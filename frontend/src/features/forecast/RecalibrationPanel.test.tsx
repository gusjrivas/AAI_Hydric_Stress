import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { RecalibrationPanel } from "./RecalibrationPanel";
import { useForecastWorkspace } from "./useForecastWorkspace";
import * as api from "./api";
import { HttpError } from "./api";
import * as lineageApi from "../lineage/api";

function Harness({ sensorId, refreshToken = 0 }: { sensorId: string; refreshToken?: number }) {
  const workspace = useForecastWorkspace(sensorId);
  return (
    <RecalibrationPanel
      sensorId={sensorId}
      workspace={workspace}
      refreshToken={refreshToken}
      onRecalibrated={() => {}}
    />
  );
}

const REJECTED_ROW: api.FeedbackRow = {
  fecha: "2024-10-31",
  alerta_generada: 1,
  estado_validacion: "rechazada",
  etiqueta_corregida: 0,
  observacion: "test",
  y_proba: 0.72,
  fecha_objetivo: null,
};

describe("RecalibrationPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("applies registered corrections and explains the effect without technical identifiers", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({ rows: [REJECTED_ROW] });
    vi.spyOn(api, "getActivePredictor").mockRejectedValue(new Error("no predictor"));
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

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByRole("button", { name: /aplicar observaciones/i }));

    await userEvent.click(screen.getByRole("button", { name: /aplicar observaciones/i }));

    await waitFor(() => {
      expect(screen.getByText(/se aplicaron 1 corrección/i)).toHaveTextContent(/al generar el próximo pronóstico/i);
    });
    expect(screen.queryByText(/recalibration_id abc123/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/predictor origen/i)).not.toBeInTheDocument();
  });

  it("does not show the recalibrate button when there are no registered corrections", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [{ ...REJECTED_ROW, estado_validacion: "pendiente", etiqueta_corregida: null }],
    });
    vi.spyOn(api, "getActivePredictor").mockRejectedValue(new Error("no predictor"));

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByText(/correcciones registradas/i));

    expect(
      screen.queryByRole("button", { name: /aplicar observaciones/i }),
    ).not.toBeInTheDocument();
  });

  it("shows incorporation as unknown when the predictor metadata cannot be loaded", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({ rows: [REJECTED_ROW] });
    vi.spyOn(api, "getActivePredictor").mockRejectedValue(new HttpError(500, "fallo"));

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByText(/no se pudo comprobar qué observaciones se usaron/i)).toBeInTheDocument();
    });
    // no debe inferir ni mostrar la fecha como incorporada sin metadata
    expect(screen.queryByText(/observaciones de esta fecha usadas anteriormente/i)).not.toBeInTheDocument();
  });

  it("shows a date already applied to the active predictor, without claiming a later edit was applied", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({ rows: [REJECTED_ROW] });
    vi.spyOn(api, "getActivePredictor").mockResolvedValue({
      sensor_id: "sensor-a",
      origin: "recalibrado",
      model_id: "modelo-x",
      version: "2",
      trained_through: "2024-10-31",
      calibration_end: "2024-10-31",
      horizon_days: 3,
      contract_version: 1,
      pipeline_version: "controlled_daily_v3",
      feature_columns: [],
      lags: [],
      rolling_windows: [],
      applied_feedback_count: 1,
      applied_feedback_dates: ["2024-10-31"],
    });

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByText(/observaciones de esta fecha usadas anteriormente/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/correcciones registradas/i).closest("p")).toHaveTextContent("1");
  });

  it("does not compute a total of eligible corrections when recalibration fails without eligible ones", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({ rows: [REJECTED_ROW] });
    vi.spyOn(api, "getActivePredictor").mockResolvedValue({
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
    });
    vi.spyOn(api, "recalibrate").mockRejectedValue(
      new HttpError(422, "No hay correcciones pendientes de aplicar."),
    );

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByRole("button", { name: /aplicar observaciones/i }));

    await userEvent.click(screen.getByRole("button", { name: /aplicar observaciones/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/no hay correcciones pendientes/i);
    });
    // no se registra ninguna versión nueva ni se declara mejora de desempeño
    expect(screen.queryByText(/modelo recalibrado/i)).not.toBeInTheDocument();
  });
});
