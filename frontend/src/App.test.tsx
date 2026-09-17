import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as forecastApi from "./features/forecast/api";
import * as qualityApi from "./features/quality/api";
import * as lineageApi from "./features/lineage/api";

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

describe("App — cabecera de sensor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(forecastApi, "getActivePredictor").mockResolvedValue(EMPTY_PREDICTOR);
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(null);
    vi.spyOn(lineageApi, "getLineage").mockResolvedValue({ sensor_id: "sensor-a", chain: [] });
  });

  it("keeps the active sensor and its queries unchanged while editing the draft without applying", async () => {
    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    const input = screen.getByLabelText(/sensor/i);
    await userEvent.clear(input);
    await userEvent.type(input, "sensor-b");

    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-a");
    expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it("applies a valid sensor id and queries the new sensor's resources", async () => {
    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    const input = screen.getByLabelText(/sensor/i);
    await userEvent.clear(input);
    await userEvent.type(input, "sensor-b");
    await userEvent.click(screen.getByRole("button", { name: /aplicar/i }));

    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-b"));
    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-b");
  });

  it("shows a validation error and does not trigger any query for an invalid sensor id", async () => {
    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1));

    const input = screen.getByLabelText(/sensor/i);
    await userEvent.clear(input);
    await userEvent.type(input, "sensor con espacios!");
    await userEvent.click(screen.getByRole("button", { name: /aplicar/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/identificador válido/i);
    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-a");
    expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it("blocks applying another sensor while a mutation is pending, and re-enables it afterward", async () => {
    let resolveRun!: (value: forecastApi.ForecastRunResponse) => void;
    vi.spyOn(forecastApi, "runForecast").mockReturnValueOnce(
      new Promise((resolve) => (resolveRun = resolve)),
    );

    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));

    const applyButton = screen.getByRole("button", { name: /aplicar/i });
    await waitFor(() => expect(applyButton).toBeDisabled());

    resolveRun({ train_rows: 1, test_rows: 1, verdicts: [] });
    await waitFor(() => expect(applyButton).not.toBeDisabled());
  });
});
