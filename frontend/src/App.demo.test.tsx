import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as forecastApi from "./features/forecast/api";
import * as qualityApi from "./features/quality/api";
import * as lineageApi from "./features/lineage/api";
import * as demoApi from "./features/demo/api";
import type { DemoSessionView } from "./features/demo/api";

const EMPTY_PREDICTOR: forecastApi.ActivePredictor = {
  sensor_id: "sensor-a",
  origin: null,
  model_id: null,
  version: null,
  trained_through: null,
  calibration_end: null,
  horizon_days: 3,
  contract_version: 1,
  pipeline_version: "controlled_daily_v3",
  feature_columns: [],
  lags: [],
  rolling_windows: [],
  applied_feedback_count: 0,
  applied_feedback_dates: [],
};

function demoSession(overrides: Partial<DemoSessionView> = {}): DemoSessionView {
  return {
    session_id: "demo-1",
    sensor_id: "demo-sensor-1",
    status: "running",
    phase: "pending",
    cursor: 1,
    days: 5,
    simulated_date: "2024-01-02",
    last_ingested_date: "2024-01-02",
    last_forecast_date: "2024-01-02",
    interval_seconds: 5,
    revision: 2,
    error: null,
    ...overrides,
  };
}

describe("App — demostración acelerada (entrega 3)", () => {
  beforeEach(() => {
    window.location.hash = "";
    vi.restoreAllMocks();
    vi.spyOn(forecastApi, "getActivePredictor").mockResolvedValue(EMPTY_PREDICTOR);
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(null);
    vi.spyOn(lineageApi, "getLineage").mockResolvedValue({ sensor_id: "sensor-a", chain: [] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("hides the demo entry point and never queries the controller when it is not configured", async () => {
    vi.spyOn(demoApi, "isDemoControlConfigured").mockReturnValue(false);
    const getSpy = vi.spyOn(demoApi, "getDemoSession");

    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    expect(screen.queryByRole("link", { name: /demostración/i })).not.toBeInTheDocument();
    expect(getSpy).not.toHaveBeenCalled();
  });

  it("opens the demo view from its own link and only performs GETs, never a POST, while browsing", async () => {
    vi.spyOn(demoApi, "isDemoControlConfigured").mockReturnValue(true);
    vi.spyOn(demoApi, "getDemoSession").mockResolvedValue(demoSession({ status: "prepared" }));
    const startSpy = vi.spyOn(demoApi, "startDemo");

    render(<App />);
    await userEvent.click(screen.getByRole("link", { name: /demostración/i }));

    await screen.findByText("Demostración con datos simulados");
    expect(screen.getByText("demo-sensor-1")).toBeInTheDocument();
    expect(startSpy).not.toHaveBeenCalled();
  });

  it("blocks manual forecast generation for the demo sensor while its session has not completed, with an explanation", async () => {
    vi.spyOn(demoApi, "isDemoControlConfigured").mockReturnValue(true);
    vi.spyOn(demoApi, "getDemoSession").mockResolvedValue(demoSession({ status: "running" }));

    render(<App />);
    const input = screen.getByLabelText(/sensor/i);
    await userEvent.clear(input);
    await userEvent.type(input, "demo-sensor-1");
    await userEvent.click(screen.getByRole("button", { name: /^aplicar$/i }));

    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("demo-sensor-1"));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /generar pronóstico/i })).toBeDisabled();
    });
    expect(screen.getByText(/sesión de demostración está en curso/i)).toBeInTheDocument();
  });

  it("does not lock manual mutations for a sensor other than the one the demo controls", async () => {
    vi.spyOn(demoApi, "isDemoControlConfigured").mockReturnValue(true);
    vi.spyOn(demoApi, "getDemoSession").mockResolvedValue(demoSession({ status: "running" }));

    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /generar pronóstico/i })).not.toBeDisabled();
    });
  });

  it("refreshes history and quality via GET for the demo sensor when confirmed progress advances, without an extra request for other sensors", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.spyOn(demoApi, "isDemoControlConfigured").mockReturnValue(true);
    const getSpy = vi
      .spyOn(demoApi, "getDemoSession")
      .mockResolvedValueOnce(demoSession({ last_ingested_date: "2024-01-02", last_forecast_date: "2024-01-02" }))
      .mockResolvedValueOnce(demoSession({ last_ingested_date: "2024-01-03", last_forecast_date: "2024-01-03" }));

    render(<App />);
    const input = screen.getByLabelText(/sensor/i);
    await userEvent.clear(input);
    await userEvent.type(input, "demo-sensor-1");
    await userEvent.click(screen.getByRole("button", { name: /^aplicar$/i }));

    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("demo-sensor-1"));
    const callsAfterInitialLoad = (forecastApi.listFeedback as ReturnType<typeof vi.fn>).mock.calls.length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    await waitFor(() => expect(getSpy).toHaveBeenCalledTimes(2));

    await waitFor(() => {
      expect((forecastApi.listFeedback as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(
        callsAfterInitialLoad,
      );
    });
    expect(forecastApi.listFeedback).toHaveBeenLastCalledWith("demo-sensor-1");
  });
});
