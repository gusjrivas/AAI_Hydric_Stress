import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SensorLabPage } from "./SensorLabPage";
import * as sensorLabApi from "./sensorLabApi";
import * as qualityApi from "../quality/api";
import * as forecastApi from "../forecast/api";
import { LAB_HISTORY_DAYS } from "./useSensorLabScenarios";
import { addDaysUtc, labBackfillEndDateUtc } from "./labSensor";
import type { QualityReport } from "../quality/api";

function baseQuality(overrides: Partial<QualityReport> = {}): QualityReport {
  return {
    sensor_id: "lab-test",
    total_rows: LAB_HISTORY_DAYS,
    period_start: "2026-01-01",
    period_end: "2026-04-30",
    missing_pct: { soil_moisture: 0 },
    duplicate_timestamps: [],
    out_of_range: {},
    anomalies_detected: 0,
    anomaly_method: "isolation_forest",
    anomaly_contamination: 0.05,
    anomaly_columns: ["soil_moisture"],
    is_diagnostic_only: true,
    note: "Diagnóstico exploratorio.",
    ...overrides,
  };
}

describe("SensorLabPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(forecastApi, "runForecast").mockResolvedValue({
      verdicts: [{ fecha: "2026-04-01", alerta: false, probabilidad: 0.1, fecha_objetivo: "2026-04-04" }],
      train_rows: 90,
      test_rows: 20,
    });
    vi.spyOn(sensorLabApi, "ingestLabReading").mockResolvedValue({
      timestamp: "2026-04-30T00:00:00Z",
      filas_totales: LAB_HISTORY_DAYS,
    });
  });

  it("always shows the permanent synthetic-data banner and a lab-prefixed sensor id", () => {
    render(<SensorLabPage />);
    expect(screen.getByText(/datos sintéticos.*sensor de prueba.*demostración técnica/i)).toBeInTheDocument();
    expect(screen.getByText(/^lab-/)).toBeInTheDocument();
  });

  it("runs scenario A: backfills the fixed history, confirms via GET /quality, and runs the real forecast pipeline", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(baseQuality());
    const user = userEvent.setup();
    render(<SensorLabPage />);

    await user.click(screen.getByRole("button", { name: /iniciar laboratorio/i }));

    await waitFor(() => {
      expect(sensorLabApi.ingestLabReading).toHaveBeenCalledTimes(LAB_HISTORY_DAYS);
    });
    expect(forecastApi.runForecast).toHaveBeenCalled();
    await waitFor(() => screen.getByRole("button", { name: /inyectar anomalía/i }));
    expect(screen.getByRole("button", { name: /inyectar anomalía/i })).toBeEnabled();
    expect(screen.getByText(/historial sintético cargado/i)).toBeInTheDocument();
  });

  it("scenario B: shows the real backend out_of_range reason when the injected reading is flagged", async () => {
    const spy = vi.spyOn(qualityApi, "getQualityReport");
    spy.mockResolvedValue(baseQuality());
    const user = userEvent.setup();
    render(<SensorLabPage />);
    await user.click(screen.getByRole("button", { name: /iniciar laboratorio/i }));
    await waitFor(() => screen.getByRole("button", { name: /inyectar anomalía/i }));

    const anomalyDate = addDaysUtc(labBackfillEndDateUtc(), 1);
    spy.mockResolvedValueOnce(
      baseQuality({ out_of_range: { temperature: [anomalyDate] }, total_rows: LAB_HISTORY_DAYS + 1 }),
    );
    await user.click(screen.getByRole("button", { name: /inyectar anomalía/i }));

    await waitFor(() => screen.getByText(/marcada por el backend/i));
  });

  it("scenario C: never shows a stale forecast as current and points to checking the sensor", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(baseQuality());
    const user = userEvent.setup();
    render(<SensorLabPage />);
    await user.click(screen.getByRole("button", { name: /iniciar laboratorio/i }));
    await waitFor(() => screen.getByRole("button", { name: /inyectar anomalía/i }));
    await user.click(screen.getByRole("button", { name: /inyectar anomalía/i }));
    await waitFor(() => screen.getByRole("button", { name: /interrumpir lecturas/i, hidden: false }));

    const ingestCallsBefore = (sensorLabApi.ingestLabReading as ReturnType<typeof vi.fn>).mock.calls.length;
    await user.click(screen.getByRole("button", { name: /interrumpir lecturas/i }));

    await waitFor(() => screen.getByRole("alert"));
    expect(screen.getByRole("alert")).toHaveTextContent(/verificar sensor y cultivo/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/no un estado vigente/i);
    // Interrumpir no ingiere lecturas nuevas.
    expect((sensorLabApi.ingestLabReading as ReturnType<typeof vi.fn>).mock.calls.length).toBe(ingestCallsBefore);
  });

  it("resets into a brand-new isolated sensor id and discards previous session state", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(baseQuality());
    const user = userEvent.setup();
    render(<SensorLabPage />);
    const firstSensorId = screen.getByText(/^lab-/).textContent;

    await user.click(screen.getByRole("button", { name: /iniciar laboratorio/i }));
    await waitFor(() => screen.getByRole("button", { name: /inyectar anomalía/i }));
    expect(screen.getByRole("button", { name: /inyectar anomalía/i })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: /reiniciar en una sesión nueva/i }));

    const secondSensorId = screen.getByText(/^lab-/).textContent;
    expect(secondSensorId).not.toBe(firstSensorId);
    expect(screen.getByRole("button", { name: /inyectar anomalía/i })).toBeDisabled();
  });
});
