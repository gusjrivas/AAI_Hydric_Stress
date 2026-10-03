import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ResumenView } from "./ResumenView";
import { useForecastWorkspace } from "../forecast/useForecastWorkspace";
import * as forecastApi from "../forecast/api";
import { HttpError } from "../forecast/api";
import * as qualityApi from "../quality/api";
import { readyQuality } from "../quality/testFixtures";

function Harness({ sensorId }: { sensorId: string }) {
  const workspace = useForecastWorkspace(sensorId);
  return <ResumenView sensorId={sensorId} workspace={workspace} />;
}

describe("ResumenView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(null);
  });

  it("shows the row with the greatest fecha as the last registered forecast, with its dates distinguished", async () => {
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-20",
          alerta_generada: 0,
          estado_validacion: "confirmada",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.1,
          fecha_objetivo: "2024-10-23",
        },
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.72,
          fecha_objetivo: "2024-11-03",
        },
      ],
    });

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => screen.getByText("2024-10-31"));
    expect(screen.getByText("2024-11-03")).toBeInTheDocument();
    // no debe mostrar la fila más antigua como "el" último pronóstico
    expect(screen.queryByText("2024-10-20")).not.toBeInTheDocument();
    expect(screen.getByText("Hay una alerta para revisar")).toBeVisible();
    expect(screen.getByText("0.72")).not.toBeVisible();
    await userEvent.click(screen.getByText("Ver el valor calculado"));
    expect(screen.getByText("0.72")).toBeVisible();
    expect(screen.getByText(/no es un porcentaje de certeza/i)).toBeVisible();
  });

  it("shows an explicit empty state instead of implying 'sin alerta' when there is no forecast yet", async () => {
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByText(/todavía no hay pronósticos registrados/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/sin alerta/i)).not.toBeInTheDocument();
  });

  it("shows 'no disponible' for missing probability/target date instead of zero or a default", async () => {
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 0,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: null,
          fecha_objetivo: null,
        },
      ],
    });

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => screen.getByText("2024-10-31"));
    expect(screen.getAllByText(/no disponible/i).length).toBeGreaterThanOrEqual(2);
  });

  it("counts pendientes de revisión across the whole history", async () => {
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.72,
          fecha_objetivo: null,
        },
        {
          fecha: "2024-10-30",
          alerta_generada: 0,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.2,
          fecha_objetivo: null,
        },
      ],
    });

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => screen.getByText(/pendientes de revisión/i));
    expect(screen.getByText(/pendientes de revisión/i).closest("p")).toHaveTextContent("2");
  });

  it("shows the quality context (data available through) as secondary content", async () => {
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue({
      sensor_id: "sensor-a",
      total_rows: 10,
      period_start: "2024-10-01",
      period_end: "2024-10-31",
      missing_pct: {},
      duplicate_timestamps: [],
      out_of_range: {},
      anomalies_detected: 0,
      anomaly_method: "isolation_forest",
      anomaly_contamination: 0.05,
      anomaly_columns: [],
      is_diagnostic_only: true,
      note: "",
    });

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByText(/datos disponibles hasta/i)).toHaveTextContent("2024-10-31");
    });
  });

  it("runs a forecast from Resumen without requiring the user to leave the view", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(readyQuality("sensor-a"));
    vi.spyOn(forecastApi, "listFeedback")
      .mockResolvedValueOnce({ rows: [] })
      .mockResolvedValue({
        rows: [
          {
            fecha: "2024-11-05",
            alerta_generada: 1,
            estado_validacion: "pendiente",
            etiqueta_corregida: null,
            observacion: null,
            y_proba: 0.8,
            fecha_objetivo: null,
          },
        ],
      });
    vi.spyOn(forecastApi, "runForecast").mockResolvedValue({
      train_rows: 1,
      test_rows: 1,
      verdicts: [{ fecha: "2024-11-05", alerta: true, probabilidad: 0.8 }],
    });

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByText(/todavía no hay pronósticos registrados/i));

    await userEvent.click(screen.getByRole("button", { name: /generar pronóstico/i }));

    await waitFor(() => screen.getByText("2024-11-05"));
  });

  it("keeps a successful forecast result even if the follow-up history refresh fails, and offers a manual retry", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(readyQuality("sensor-a"));
    vi.spyOn(forecastApi, "listFeedback")
      .mockResolvedValueOnce({ rows: [] })
      .mockRejectedValueOnce(new HttpError(500, "fallo de refresco"));
    vi.spyOn(forecastApi, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByText(/todavía no hay pronósticos registrados/i));

    await userEvent.click(screen.getByRole("button", { name: /generar pronóstico/i }));

    await waitFor(() => {
      expect(screen.getByText("2024-10-31")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/no se pudo confirmar la actualización del historial/i),
    ).toBeInTheDocument();
  });

  it("blocks the forecast action for a point without readings and points to the Laboratorio instead of failing", async () => {
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    render(<Harness sensorId="sensor-a" />);
    expect(await screen.findByText(/todavía no hay mediciones cargadas para este punto/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generar pronóstico/i })).toBeDisabled();
    expect(screen.getByText(/primero hacen falta mediciones de este punto/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ir al laboratorio/i })).toHaveAttribute("href", "#laboratorio-sensores");
  });

  it("enables the forecast action once the point has readings", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(readyQuality("sensor-a"));
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => expect(screen.getByRole("button", { name: /generar pronóstico/i })).toBeEnabled());
    expect(screen.queryByText(/primero hacen falta mediciones/i)).not.toBeInTheDocument();
  });

  it("says so when generating again does not add a day because the last date already has its forecast", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(readyQuality("sensor-a"));
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({
      rows: [{ fecha: "2026-09-27", alerta_generada: 0, estado_validacion: "pendiente", etiqueta_corregida: null, observacion: null, y_proba: 0, fecha_objetivo: "2026-09-30" }],
    });
    vi.spyOn(forecastApi, "runForecast").mockResolvedValue({
      train_rows: 100, test_rows: 1, verdicts: [{ fecha: "2026-09-27", alerta: false, probabilidad: 0, fecha_objetivo: "2026-09-30" }],
    });
    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => expect(screen.getByRole("button", { name: /generar pronóstico/i })).toBeEnabled());
    await screen.findByText("2026-09-30");
    await userEvent.click(screen.getByRole("button", { name: /generar pronóstico/i }));
    expect(await screen.findByText(/ya estaba emitido: no se agregaron días nuevos/i)).toBeInTheDocument();
    expect(screen.getByText(/mediciones más recientes/i)).toBeInTheDocument();
  });

  it("confirms when a new day was added", async () => {
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(readyQuality("sensor-a"));
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(forecastApi, "runForecast").mockResolvedValue({
      train_rows: 100, test_rows: 1, verdicts: [{ fecha: "2026-09-27", alerta: false, probabilidad: 0, fecha_objetivo: "2026-09-30" }],
    });
    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => expect(screen.getByRole("button", { name: /generar pronóstico/i })).toBeEnabled());
    await userEvent.click(screen.getByRole("button", { name: /generar pronóstico/i }));
    expect(await screen.findByText(/se agregó el pronóstico con datos hasta el 2026-09-27 \(para el 2026-09-30\)/i)).toBeInTheDocument();
  });
});
