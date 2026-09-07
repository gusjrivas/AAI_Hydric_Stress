import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ActivePredictorSummary } from "./ActivePredictorSummary";
import * as api from "./api";
import type { ActivePredictor } from "./api";

function buildPredictor(overrides: Partial<ActivePredictor> = {}): ActivePredictor {
  return {
    sensor_id: "sensor-a",
    origin: "base_configurado",
    model_id: "modelo-abc",
    version: "1",
    trained_through: "2024-10-30",
    calibration_end: null,
    horizon_days: 3,
    contract_version: 1,
    pipeline_version: "v1",
    feature_columns: ["soil_moisture"],
    lags: [1],
    rolling_windows: [3],
    applied_feedback_count: 0,
    applied_feedback_dates: [],
    ...overrides,
  };
}

describe("ActivePredictorSummary", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state before the predictor resolves", () => {
    vi.spyOn(api, "getActivePredictor").mockReturnValue(new Promise(() => {}));

    render(<ActivePredictorSummary sensorId="sensor-a" />);

    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
  });

  it("shows an empty state when no forecast has run yet", async () => {
    vi.spyOn(api, "getActivePredictor").mockResolvedValue(buildPredictor({ origin: null, model_id: null, version: null }));

    render(<ActivePredictorSummary sensorId="sensor-a" />);

    await waitFor(() => screen.getByText(/todavía no se corrió ningún pronóstico/i));
  });

  it("renders the resolved predictor identity", async () => {
    vi.spyOn(api, "getActivePredictor").mockResolvedValue(buildPredictor());

    render(<ActivePredictorSummary sensorId="sensor-a" />);

    await waitFor(() => screen.getByText(/modelo-abc/i));
    expect(screen.getByText(/base configurado/i)).toBeInTheDocument();
  });

  it("shows an alert on error", async () => {
    vi.spyOn(api, "getActivePredictor").mockRejectedValue(new Error("fallo de red"));

    render(<ActivePredictorSummary sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/fallo de red/i);
    });
  });

  it("shows loading again and never the previous sensor's predictor when sensorId changes", async () => {
    const spy = vi.spyOn(api, "getActivePredictor");
    spy.mockResolvedValueOnce(buildPredictor({ model_id: "modelo-sensor-a" }));

    const { rerender } = render(<ActivePredictorSummary sensorId="sensor-a" />);
    await waitFor(() => screen.getByText(/modelo-sensor-a/i));

    let resolveSensorB!: (value: ActivePredictor) => void;
    spy.mockReturnValueOnce(new Promise<ActivePredictor>((resolve) => (resolveSensorB = resolve)));

    rerender(<ActivePredictorSummary sensorId="sensor-b" />);

    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
    expect(screen.queryByText(/modelo-sensor-a/i)).not.toBeInTheDocument();

    resolveSensorB(buildPredictor({ sensor_id: "sensor-b", model_id: "modelo-sensor-b" }));

    await waitFor(() => screen.getByText(/modelo-sensor-b/i));
  });

  it("refetches without showing stale data when refreshToken changes", async () => {
    const spy = vi.spyOn(api, "getActivePredictor");
    spy.mockResolvedValueOnce(buildPredictor({ model_id: "modelo-v1", version: "1" }));

    const { rerender } = render(<ActivePredictorSummary sensorId="sensor-a" refreshToken={0} />);
    await waitFor(() => screen.getByText(/modelo-v1/i));

    let resolveRefetch!: (value: ActivePredictor) => void;
    spy.mockReturnValueOnce(new Promise<ActivePredictor>((resolve) => (resolveRefetch = resolve)));

    rerender(<ActivePredictorSummary sensorId="sensor-a" refreshToken={1} />);

    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);

    resolveRefetch(buildPredictor({ origin: "recalibrado", model_id: "modelo-v2", version: "2" }));

    await waitFor(() => screen.getByText(/modelo-v2/i));
  });
});
