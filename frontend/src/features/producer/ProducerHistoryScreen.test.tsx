import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProducerHistoryScreen } from "./ProducerHistoryScreen";
import * as forecastsApi from "./forecastsApi";
import * as historicalApi from "./historicalApi";
import type { Forecast, ForecastBatch } from "./forecastsApi";

afterEach(() => vi.restoreAllMocks());

const SHARED_FORECAST_ID = "fc-shared";

function baseForecast(overrides: Partial<Forecast> = {}): Forecast {
  return {
    forecast_id: SHARED_FORECAST_ID,
    sensor_id: "sensor-a",
    batch_id: "batch-1",
    as_of_date: "2023-06-13",
    horizon_days: 1,
    target_date: "2023-06-14",
    contract_version: "producer_daily_h123_v1",
    issued_at: "2023-06-13T00:05:00Z",
    snapshot_id: "snap-1",
    alert: false,
    score: 0.1,
    score_kind: "ensemble_mean_of_calibrated_components",
    display_probability: null,
    probability_status: "not_qualified",
    probability_reason_code: null,
    decision_threshold: 0.5,
    event_threshold: { variable: "soil_moisture", value: 0.18, unit: "m3/m3", comparison: "lt" },
    model_reference: {
      model_version: "v1", horizon_days: 1, contract_version: "producer_daily_h123_v1",
      trained_through: "2022-12-31", calibration_version: "cal-1", assessment_reference: "assessment-1",
    },
    review: {
      status: "pending", revision: 0, review_open_at: "2023-06-14T00:00:00Z",
      reviewable: true, blocked_reason: null, latest_review: null,
      training_eligibility: "no_review", applied_review_references: [],
    },
    ensemble: null,
    ...overrides,
  };
}

describe("ProducerHistoryScreen", () => {
  it("never shares review context between the operational list and the historical walkthrough, even for the same forecast_id", async () => {
    vi.spyOn(forecastsApi, "listForecasts").mockResolvedValue({
      items: [baseForecast()],
      next_cursor: null,
      pending_total: 1,
      reviewable_pending_total: 1,
    });
    vi.spyOn(forecastsApi, "submitReview").mockResolvedValue({
      status: "confirmed", revision: 1, review_open_at: "2023-06-14T00:00:00Z", reviewable: true,
      blocked_reason: null, latest_review: null, training_eligibility: "no_review", applied_review_references: [],
    });

    const historicalBatch: ForecastBatch = {
      batch_id: "batch-1", revision: 1, as_of_date: "2023-06-13", data_age_days: 0,
      server_today: "2023-06-13", provenance: "real", calendar_timezone: "UTC",
      slots: [
        { ...baseForecast(), status: "available" },
        { horizon_days: 2, target_date: "2023-06-15", status: "unavailable", reason_code: "model_not_available" },
        { horizon_days: 3, target_date: "2023-06-16", status: "unavailable", reason_code: "model_not_available" },
      ],
    };
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(historicalBatch);
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));

    render(<ProducerHistoryScreen sensorId="sensor-a" />);

    // Confirm through the *operational* (live) card, in the pendientes list.
    const liveConfirmButtons = await screen.findAllByRole("button", { name: /confirmar resultado/i });
    await userEvent.click(liveConfirmButtons[0]);
    await userEvent.click(screen.getAllByRole("button", { name: /guardar opinión/i })[0]);
    await waitFor(() => expect(screen.getAllByText(/confirmado por vos/i).length).toBeGreaterThan(0));

    // Reach the historical card for the *same* forecast_id.
    await userEvent.type(screen.getByLabelText(/emisión seleccionada/i), "2023-06-13");
    const historicalCards = await screen.findAllByText(/pendiente de revisar/i);
    // At least one card (the historical one) must still be pending: the
    // live confirmation must never have leaked into it through a shared
    // review context.
    expect(historicalCards.length).toBeGreaterThan(0);
  });
});
