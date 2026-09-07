import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ForecastPage } from "./ForecastPage";
import * as api from "./api";
import * as lineageApi from "../lineage/api";

const EMPTY_PREDICTOR: api.ActivePredictor = {
  sensor_id: "sensor-a",
  origin: null,
  model_id: null,
  version: null,
  trained_through: null,
  calibration_end: null,
  horizon_days: 3,
  contract_version: 1,
  pipeline_version: "controlled_daily_v3",
  feature_columns: ["soil_moisture", "solar_radiation", "relative_humidity"],
  lags: [1, 2, 3],
  rolling_windows: [3, 7],
  applied_feedback_count: 0,
  applied_feedback_dates: [],
};

describe("ForecastPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "getActivePredictor").mockResolvedValue(EMPTY_PREDICTOR);
  });

  it("runs the forecast and shows the resulting alerts", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
        },
      ],
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));

    await waitFor(() => {
      expect(screen.getByText("2024-10-31")).toBeInTheDocument();
    });
    expect(screen.getByText(/pendiente/i)).toBeInTheDocument();
  });

  it("confirms an alert and updates its displayed state", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
        },
      ],
    });
    vi.spyOn(api, "confirmAlert").mockResolvedValue({
      fecha: "2024-10-31",
      alerta_generada: 1,
      estado_validacion: "confirmada",
      etiqueta_corregida: null,
      observacion: null,
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));
    await waitFor(() => screen.getByText("2024-10-31"));

    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }));

    await waitFor(() => {
      expect(screen.getByText(/confirmada/i)).toBeInTheDocument();
    });
  });

  it("shows a recalibrate button only when there is a pending correction, and using it shows the registered version and its lineage", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "rechazada",
          etiqueta_corregida: 0,
          observacion: "test",
        },
      ],
    });
    vi.spyOn(api, "recalibrate").mockResolvedValue({
      version: "1",
      n_correcciones: 1,
      fechas_corregidas: ["2024-10-31"],
      recalibration_id: "abc123",
    });
    vi.spyOn(lineageApi, "getLineage").mockResolvedValue({
      sensor_id: "sensor-a",
      chain: [
        {
          recalibration_id: "abc123",
          source_model_id: "modelo-origen-000000",
          successor_model_id: "modelo-sucesor-000000",
          feedback_references: [
            {
              sensor_id: "sensor-a",
              fecha: "2024-10-31",
              model_version: "modelo-origen-000000",
              target_timestamp: "2024-11-03",
            },
          ],
          recalibrated_at: "2026-09-06T10:00:00",
          source_trained_through: "2024-10-30",
          successor_trained_through: "2024-10-31",
          lineage_version: 2,
          dataset_sha256: "a".repeat(64),
          mlflow_model_version: "1",
        },
      ],
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));
    await waitFor(() => screen.getByRole("button", { name: /recalibrar modelo/i }));

    await userEvent.click(screen.getByRole("button", { name: /recalibrar modelo/i }));

    await waitFor(() => {
      expect(screen.getByText(/versión 1/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/recalibration_id abc123/i)).toBeInTheDocument();
    expect(screen.getByText(/predictor origen/i)).toBeInTheDocument();
  });

  it("does not show the recalibrate button when there are no pending corrections", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
        },
      ],
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));
    await waitFor(() => screen.getByText("2024-10-31"));

    expect(
      screen.queryByRole("button", { name: /recalibrar modelo/i }),
    ).not.toBeInTheDocument();
  });

  it("shows the relative-signal disclaimer next to the probability gauge", async () => {
    render(<ForecastPage />);
    expect(
      screen.getByText(/señal predictiva relativa del modelo/i),
    ).toBeInTheDocument();
  });

  it("shows the active predictor's identity once it resolves", async () => {
    vi.spyOn(api, "getActivePredictor").mockResolvedValue({
      ...EMPTY_PREDICTOR,
      origin: "recalibrado",
      model_id: "modelo-activo",
      version: "2",
      trained_through: "2024-10-31",
    });

    render(<ForecastPage />);

    await waitFor(() => {
      expect(screen.getByText(/recalibrado \(hitl\)/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/modelo-activo/i)).toBeInTheDocument();
  });
});
