import { act, renderHook, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MockInstance } from "vitest";
import * as sensorLabApi from "./sensorLabApi";
import * as qualityApi from "../quality/api";
import type { QualityReport } from "../quality/api";
import {
  LAB_ERROR_NO_LAST_READING,
  LAB_HISTORY_DAYS,
  useSensorLabScenarios,
} from "./useSensorLabScenarios";

function quality(overrides: Partial<QualityReport> = {}): QualityReport {
  return {
    sensor_id: "lab-x",
    total_rows: LAB_HISTORY_DAYS,
    period_start: "2026-01-01",
    period_end: "2026-04-30",
    missing_pct: {},
    duplicate_timestamps: [],
    out_of_range: {},
    anomalies_detected: 0,
    anomaly_method: "isolation_forest",
    anomaly_contamination: 0.05,
    anomaly_columns: [],
    is_diagnostic_only: true,
    note: "",
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const ok = { timestamp: "t", filas_totales: 1 };

describe("useSensorLabScenarios: ciclo de vida, reintentos y recuperación", () => {
  const runForecast = vi.fn();
  const onIngested = vi.fn();
  let ingest: MockInstance<typeof sensorLabApi.ingestLabReading>;
  let getQuality: MockInstance<typeof qualityApi.getQualityReport>;

  beforeEach(() => {
    vi.restoreAllMocks();
    runForecast.mockReset().mockResolvedValue(undefined);
    onIngested.mockReset();
    ingest = vi.spyOn(sensorLabApi, "ingestLabReading").mockResolvedValue(ok);
    getQuality = vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(quality());
  });

  function mount(sensorId = "lab-a", wrapper?: (props: { children: ReactNode }) => ReactNode) {
    return renderHook(({ id }) => useSensorLabScenarios(id, { onIngested, runForecast }), {
      initialProps: { id: sensorId },
      wrapper,
    });
  }

  async function reachPhase(hook: ReturnType<typeof mount>, target: "normal" | "anomaly" | "interrupted") {
    await act(async () => {
      await hook.result.current.runScenarioA();
    });
    if (target === "normal") return;
    await act(async () => {
      await hook.result.current.runScenarioB();
    });
    if (target === "anomaly") return;
    await act(async () => {
      await hook.result.current.runScenarioC();
    });
  }

  it("does not start more requests nor a forecast after unmount with a pending ingest", async () => {
    const first = deferred<typeof ok>();
    ingest.mockReturnValueOnce(first.promise);
    const hook = mount();
    let run!: Promise<void>;
    act(() => {
      run = hook.result.current.runScenarioA();
    });
    expect(ingest).toHaveBeenCalledTimes(1);
    hook.unmount();

    await act(async () => {
      first.resolve(ok);
      await run;
    });
    expect(ingest).toHaveBeenCalledTimes(1);
    expect(getQuality).not.toHaveBeenCalled();
    expect(runForecast).not.toHaveBeenCalled();
  });

  it("isolates the previous session from the new one when the sensor changes mid-ingest", async () => {
    const first = deferred<typeof ok>();
    ingest.mockReturnValueOnce(first.promise);
    const hook = mount("lab-old");
    let run!: Promise<void>;
    act(() => {
      run = hook.result.current.runScenarioA();
    });
    hook.rerender({ id: "lab-new" });
    expect(hook.result.current.phase).toBe("idle");
    expect(hook.result.current.busy).toBe(false);

    await act(async () => {
      first.resolve(ok);
      await run;
    });
    // La sesión vieja no envió nada más ni tocó el estado de la nueva.
    expect(ingest).toHaveBeenCalledTimes(1);
    expect(runForecast).not.toHaveBeenCalled();
    expect(hook.result.current.phase).toBe("idle");
    expect(hook.result.current.log).toEqual([]);

    // La sesión nueva puede correr A completa sobre su propio sensor.
    await act(async () => {
      await hook.result.current.runScenarioA();
    });
    expect(hook.result.current.phase).toBe("normal");
    const sensors = new Set(ingest.mock.calls.slice(1).map((call) => call[0]));
    expect(sensors).toEqual(new Set(["lab-new"]));
    expect(ingest).toHaveBeenCalledTimes(1 + LAB_HISTORY_DAYS);
  });

  it("a double immediate invocation of A runs a single ingest sequence", async () => {
    const hook = mount();
    await act(async () => {
      const a = hook.result.current.runScenarioA();
      const b = hook.result.current.runScenarioA();
      await Promise.all([a, b]);
    });
    expect(ingest).toHaveBeenCalledTimes(LAB_HISTORY_DAYS);
    expect(runForecast).toHaveBeenCalledTimes(1);
  });

  it("enforces the A, B, C, D order inside the hook", async () => {
    const hook = mount();
    await act(async () => {
      await hook.result.current.runScenarioB();
      await hook.result.current.runScenarioC();
      await hook.result.current.runScenarioD();
    });
    expect(ingest).not.toHaveBeenCalled();
    expect(hook.result.current.phase).toBe("idle");
    await reachPhase(hook, "normal");
    await act(async () => {
      await hook.result.current.runScenarioA(); // A no se repite
    });
    expect(ingest).toHaveBeenCalledTimes(LAB_HISTORY_DAYS);
  });

  it("works under StrictMode for the current session", async () => {
    const wrapper = ({ children }: { children: ReactNode }) => <StrictMode>{children}</StrictMode>;
    const hook = mount("lab-a", wrapper);
    await act(async () => {
      await hook.result.current.runScenarioA();
    });
    expect(hook.result.current.phase).toBe("normal");
    expect(ingest).toHaveBeenCalledTimes(LAB_HISTORY_DAYS);
    expect(runForecast).toHaveBeenCalledTimes(1);
  });

  it("after two accepted readings and a failure, A is not repeated on the old sensor; a new session can start A", async () => {
    ingest.mockResolvedValueOnce(ok).mockResolvedValueOnce(ok).mockRejectedValueOnce(new Error("fallo de red"));
    const hook = mount("lab-old");
    await act(async () => {
      await hook.result.current.runScenarioA();
    });
    expect(hook.result.current.phase).toBe("error");
    expect(hook.result.current.busy).toBe(false);
    expect(hook.result.current.error).toBe("fallo de red");
    expect(ingest).toHaveBeenCalledTimes(3);

    await act(async () => {
      await hook.result.current.runScenarioA();
      await hook.result.current.runScenarioB();
      await hook.result.current.runScenarioC();
      await hook.result.current.runScenarioD();
    });
    expect(ingest).toHaveBeenCalledTimes(3); // ninguna lectura nueva al sensor anterior
    expect(runForecast).not.toHaveBeenCalled();

    hook.rerender({ id: "lab-new" });
    expect(hook.result.current.phase).toBe("idle");
    expect(hook.result.current.error).toBeNull();
    await act(async () => {
      await hook.result.current.runScenarioA();
    });
    expect(hook.result.current.phase).toBe("normal");
    expect(ingest).toHaveBeenCalledTimes(3 + LAB_HISTORY_DAYS);
    expect(ingest.mock.calls.slice(3).every((call) => call[0] === "lab-new")).toBe(true);
  });

  it("D with period_end=null stops with a controlled error, no ingest, no forecast, no recovered state", async () => {
    const hook = mount();
    await reachPhase(hook, "interrupted");
    const ingestBefore = ingest.mock.calls.length;
    const forecastBefore = runForecast.mock.calls.length;
    getQuality.mockResolvedValue(quality({ period_end: null }));

    await act(async () => {
      await hook.result.current.runScenarioD();
    });
    expect(hook.result.current.phase).toBe("error");
    expect(hook.result.current.busy).toBe(false);
    expect(hook.result.current.error).toBe(LAB_ERROR_NO_LAST_READING);
    expect(ingest.mock.calls.length).toBe(ingestBefore);
    expect(runForecast.mock.calls.length).toBe(forecastBefore);
    expect(hook.result.current.log.some((entry) => entry.scenario === "D")).toBe(false);
  });

  it("D with a quality query error ends in error, not stuck in recovering", async () => {
    const hook = mount();
    await reachPhase(hook, "interrupted");
    const ingestBefore = ingest.mock.calls.length;
    getQuality.mockRejectedValue(new Error("consulta fallida"));

    await act(async () => {
      await hook.result.current.runScenarioD();
    });
    await waitFor(() => expect(hook.result.current.phase).toBe("error"));
    expect(hook.result.current.busy).toBe(false);
    expect(hook.result.current.error).toBe("consulta fallida");
    expect(ingest.mock.calls.length).toBe(ingestBefore);
  });
});
