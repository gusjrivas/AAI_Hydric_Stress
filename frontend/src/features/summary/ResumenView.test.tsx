import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ResumenView } from "./ResumenView";
import { useForecastWorkspace } from "../forecast/useForecastWorkspace";
import * as forecastApi from "../forecast/api";
import { HttpError } from "../forecast/api";
import * as qualityApi from "../quality/api";

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

    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));

    await waitFor(() => screen.getByText("2024-11-05"));
  });

  it("keeps a successful forecast result even if the follow-up history refresh fails, and offers a manual retry", async () => {
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

    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));

    await waitFor(() => {
      expect(screen.getByText("2024-10-31")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/no se pudo confirmar la actualización del historial/i),
    ).toBeInTheDocument();
  });
});
