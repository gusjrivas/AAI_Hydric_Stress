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
    expect(screen.getByText("SIMULACIÓN · Datos sintéticos · Sin sensor físico conectado")).toBeInTheDocument();
    expect(screen.getByText(/^lab-/)).toBeInTheDocument();
  });

  it("runs scenario A: backfills the fixed history, confirms via GET /quality, and runs the real forecast pipeline", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(baseQuality());
    const user = userEvent.setup();
    render(<SensorLabPage />);

    await user.click(screen.getByRole("button", { name: /generar historial de prueba/i }));

    await waitFor(() => {
      expect(sensorLabApi.ingestLabReading).toHaveBeenCalledTimes(LAB_HISTORY_DAYS);
    });
    expect(forecastApi.runForecast).toHaveBeenCalled();
    await waitFor(() => screen.getByRole("button", { name: /introducir una lectura anómala/i }));
    expect(screen.getByRole("button", { name: /introducir una lectura anómala/i })).toBeEnabled();
    expect(screen.getByText(/historial sintético cargado/i)).toBeInTheDocument();
  });

  it("scenario B: shows the real backend out_of_range reason when the injected reading is flagged", async () => {
    const spy = vi.spyOn(qualityApi, "getQualityReport");
    spy.mockResolvedValue(baseQuality());
    const user = userEvent.setup();
    render(<SensorLabPage />);
    await user.click(screen.getByRole("button", { name: /generar historial de prueba/i }));
    await waitFor(() => screen.getByRole("button", { name: /introducir una lectura anómala/i }));

    const anomalyDate = addDaysUtc(labBackfillEndDateUtc(), 1);
    spy.mockResolvedValueOnce(
      baseQuality({ out_of_range: { temperature: [anomalyDate] }, total_rows: LAB_HISTORY_DAYS + 1 }),
    );
    await user.click(screen.getByRole("button", { name: /introducir una lectura anómala/i }));

    await waitFor(() => screen.getByText(/marcada por el control de calidad/i));
  });

  it("scenario C: never shows a stale forecast as current and points to checking the sensor", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(baseQuality());
    const user = userEvent.setup();
    render(<SensorLabPage />);
    await user.click(screen.getByRole("button", { name: /generar historial de prueba/i }));
    await waitFor(() => screen.getByRole("button", { name: /introducir una lectura anómala/i }));
    await user.click(screen.getByRole("button", { name: /introducir una lectura anómala/i }));
    await waitFor(() => screen.getByRole("button", { name: /simular una interrupción/i, hidden: false }));

    const ingestCallsBefore = (sensorLabApi.ingestLabReading as ReturnType<typeof vi.fn>).mock.calls.length;
    await user.click(screen.getByRole("button", { name: /simular una interrupción/i }));

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

    await user.click(screen.getByRole("button", { name: /generar historial de prueba/i }));
    await waitFor(() => screen.getByRole("button", { name: /introducir una lectura anómala/i }));
    expect(screen.getByRole("button", { name: /introducir una lectura anómala/i })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: /iniciar una sesión nueva/i }));

    const secondSensorId = screen.getByText(/^lab-/).textContent;
    expect(secondSensorId).not.toBe(firstSensorId);
    expect(screen.getByRole("button", { name: /introducir una lectura anómala/i })).toBeDisabled();
  });

  it("explains precisely what is simulated, what really runs, and never says the predictor is not trained", () => {
    render(<SensorLabPage />);
    expect(screen.getByRole("heading", { name: "Laboratorio de sensor simulado" })).toBeInTheDocument();
    expect(screen.getByText("Qué simulamos")).toBeInTheDocument();
    expect(screen.getByText("Qué funciona realmente")).toBeInTheDocument();
    expect(screen.getByText(/puede entrenarse o actualizarse con las lecturas sintéticas/i)).toBeInTheDocument();
    expect(screen.queryByText(/no entrena otro modelo/i)).toBeNull();
    expect(screen.getByText(/no cambia la fecha real del servidor/i)).toBeInTheDocument();
    expect(screen.getByText(/no representa una observación independiente de un cultivo real/i)).toBeInTheDocument();
    expect(screen.getByText(/se suspende el envío del generador/i)).toBeInTheDocument();
  });

  it("presents the physical connection as collapsible future work with the four steps", () => {
    render(<SensorLabPage />);
    const summary = screen.getByText("¿Cómo se conectaría un sensor real?");
    expect(summary.closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText(/quedan como trabajo futuro/i)).toBeInTheDocument();
    expect(summary.closest("details")!.querySelectorAll("ol > li")).toHaveLength(4);
  });

  it("after an ingest error keeps A-D disabled, shows the guidance and lets a new session start A", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(baseQuality());
    vi.spyOn(sensorLabApi, "ingestLabReading").mockRejectedValueOnce(new Error("Error del backend"));
    const user = userEvent.setup();
    render(<SensorLabPage />);
    const firstSensorId = screen.getByText(/^lab-/).textContent;

    await user.click(screen.getByRole("button", { name: /generar historial de prueba/i }));
    await waitFor(() => screen.getByText(/este paso no pudo completarse/i));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Este paso no pudo completarse. Para evitar modificar lecturas ya guardadas, iniciá una sesión nueva. Los datos de la sesión anterior se conservan.",
    );
    for (const name of [/generar historial de prueba/i, /introducir una lectura anómala/i, /simular una interrupción/i, /simular la recuperación/i]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }

    await user.click(screen.getByRole("button", { name: /iniciar una sesión nueva/i }));
    expect(screen.getByText(/^lab-/).textContent).not.toBe(firstSensorId);
    expect(screen.getByRole("button", { name: /generar historial de prueba/i })).toBeEnabled();
    expect(screen.queryByText(/este paso no pudo completarse/i)).toBeNull();
  });

  it("tells the app which sensor has data once scenario A finishes, and opens it in the tools without copying the id", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(baseQuality());
    const onSensorWithData = vi.fn();
    const onOpenInTools = vi.fn();
    const user = userEvent.setup();
    render(<SensorLabPage onSensorWithData={onSensorWithData} onOpenInTools={onOpenInTools} />);
    // Antes del paso A no hay datos: ni aviso ni enlace.
    expect(onSensorWithData).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /en resumen e historial/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generar historial de prueba/i }));
    const open = await screen.findByRole("button", { name: /^ver «lab-[a-z0-9]+» en resumen e historial$/i });
    const sensorId = /«(lab-[a-z0-9]+)»/i.exec(open.textContent ?? "")![1];
    expect(onSensorWithData).toHaveBeenCalledWith(sensorId);
    await user.click(open);
    expect(onOpenInTools).toHaveBeenCalledWith(sensorId);
  });
});
