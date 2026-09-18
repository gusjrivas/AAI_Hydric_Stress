import { describe, expect, it, vi } from "vitest";
import { computeDemoWriteGate, demoGateForSensor } from "./lock";
import type { DemoSessionView } from "./api";
import type { FeedbackRow } from "../forecast/api";

function session(overrides: Partial<DemoSessionView> = {}): DemoSessionView {
  return {
    session_id: "demo-1",
    sensor_id: "demo-sensor-1",
    status: "running",
    phase: "pending",
    cursor: 2,
    days: 5,
    simulated_date: "2024-01-03",
    last_ingested_date: "2024-01-03",
    last_forecast_date: "2024-01-03",
    interval_seconds: 5,
    revision: 4,
    error: null,
    ...overrides,
  };
}

function row(overrides: Partial<FeedbackRow> = {}): FeedbackRow {
  return {
    fecha: "2024-01-03",
    alerta_generada: 1,
    estado_validacion: "pendiente",
    etiqueta_corregida: null,
    observacion: null,
    fecha_objetivo: "2024-01-01",
    ...overrides,
  };
}

describe("demoGateForSensor", () => {
  it("returns undefined when there is no session", () => {
    expect(demoGateForSensor(null, "sensor-a")).toBeUndefined();
  });

  it("returns undefined for a sensor that is not the demo sensor", () => {
    expect(demoGateForSensor(session(), "sensor-a")).toBeUndefined();
  });

  it("returns a gate for the demo sensor", () => {
    expect(demoGateForSensor(session(), "demo-sensor-1")).toBeDefined();
  });
});

describe("computeDemoWriteGate", () => {
  it("locks every manual mutation while the session has not completed", () => {
    for (const status of ["prepared", "running", "pausing", "paused", "blocked"] as const) {
      const gate = computeDemoWriteGate(session({ status }));
      expect(gate.locked).toBe(true);
      expect(gate.isRowReviewable(row())).toBe(false);
    }
  });

  it("unlocks manual mutations once completed", () => {
    const gate = computeDemoWriteGate(session({ status: "completed" }));
    expect(gate.locked).toBe(false);
  });

  it("only allows review for rows whose target date is ingested and already past in UTC", () => {
    vi.setSystemTime(new Date("2024-06-01T00:00:00Z"));
    const completed = session({ status: "completed", last_ingested_date: "2024-01-03" });
    const gate = computeDemoWriteGate(completed);

    expect(gate.isRowReviewable(row({ fecha_objetivo: "2024-01-01" }))).toBe(true);
    // fecha objetivo posterior al período ingerido: sin observación disponible.
    expect(gate.isRowReviewable(row({ fecha_objetivo: "2024-01-10" }))).toBe(false);
    // sin fecha objetivo: nunca ofrecida como revisable.
    expect(gate.isRowReviewable(row({ fecha_objetivo: null }))).toBe(false);
    vi.useRealTimers();
  });

  it("never treats a target date that has not yet happened in real UTC time as reviewable", () => {
    vi.setSystemTime(new Date("2024-01-02T00:00:00Z"));
    const completed = session({ status: "completed", last_ingested_date: "2024-01-05" });
    const gate = computeDemoWriteGate(completed);

    expect(gate.isRowReviewable(row({ fecha_objetivo: "2024-01-05" }))).toBe(false);
    vi.useRealTimers();
  });
});
