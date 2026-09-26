import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HistoricalWalkthrough } from "./HistoricalWalkthrough";
import * as historicalApi from "./historicalApi";
import type { ForecastBatch } from "./forecastsApi";

afterEach(() => vi.restoreAllMocks());

function batchFor(asOfDate: string, targetSuffix: string): ForecastBatch {
  return {
    batch_id: `batch-${asOfDate}`,
    revision: 1,
    as_of_date: asOfDate,
    data_age_days: 0,
    server_today: asOfDate,
    provenance: "real",
    calendar_timezone: "UTC",
    slots: [1, 2, 3].map((h) => ({
      horizon_days: h as 1 | 2 | 3,
      target_date: `2023-06-${targetSuffix}`,
      status: "unavailable",
      reason_code: "model_not_available",
    })),
  };
}

describe("HistoricalWalkthrough", () => {
  it("keeps the emission date and the walked-forward reveal date visually separate, never merged", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batchFor("2023-06-13", "14"));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue({
      sensor_id: "sensor-a",
      calendar_timezone: "UTC",
      server_today: "2023-06-13",
      snapshot_id: null,
      window: { start_date: "2023-06-04", end_date: "2023-06-13", expected_days: 10 },
      status: "no_readings",
      rows: [],
      missing_dates: [],
      variable_coverage: [],
      units: {},
      last_reading_date: null,
      data_age_days: null,
      provenance: "real",
    });
    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    await userEvent.type(screen.getByLabelText(/emisión seleccionada/i), "2023-06-13");
    expect(await screen.findByText(/viendo la emisión del/i)).toBeInTheDocument();
    expect(screen.getByText(/recorrido avanzado hasta el/i)).toBeInTheDocument();
    // Sin haber tocado "Recorrido hasta", el reloj del recorrido arranca
    // igual a la emisión -- nunca antes.
    expect(historicalApi.getHistoricalForecastBatch).toHaveBeenCalledWith("sensor-a", "2023-06-13", undefined);
  });

  it("discards a stale response when navigating A -> B -> A, keeping only the last request's result", async () => {
    const resolvers: Array<(batch: ForecastBatch) => void> = [];
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(
      () => new Promise((resolve) => resolvers.push(resolve)),
    );
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));

    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    const emissionInput = screen.getByLabelText(/emisión seleccionada/i);

    await userEvent.type(emissionInput, "2023-06-13"); // A
    await userEvent.clear(emissionInput);
    await userEvent.type(emissionInput, "2023-06-14"); // B
    await userEvent.clear(emissionInput);
    await userEvent.type(emissionInput, "2023-06-13"); // A again
    await waitFor(() => expect(resolvers).toHaveLength(3));

    // Resolve out of order: the middle (B) and the first A resolve after
    // the second A request was already issued -- their distinguishable
    // target dates must never be the one left on screen.
    await act(async () => {
      resolvers[1](batchFor("2023-06-14", "17")); // stale B
      resolvers[0](batchFor("2023-06-13", "14")); // stale first A
    });
    expect(screen.queryByText(/17 de jun/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/14 de jun/i)).not.toBeInTheDocument();

    await act(async () => {
      resolvers[2](batchFor("2023-06-13", "18")); // the current, last-issued A request
    });
    expect(await screen.findAllByText(/18 de jun/i)).not.toHaveLength(0);
    expect(screen.queryByText(/17 de jun/i)).not.toBeInTheDocument();
  });

  it("passes the walked-forward reveal date, not the emission date, to the historical review route", async () => {
    const batch: ForecastBatch = {
      batch_id: "batch-2023-06-13",
      revision: 1,
      as_of_date: "2023-06-13",
      data_age_days: 0,
      server_today: "2023-06-13",
      provenance: "real",
      calendar_timezone: "UTC",
      slots: [
        {
          status: "available",
          forecast_id: "fc-1",
          sensor_id: "sensor-a",
          batch_id: "batch-2023-06-13",
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
        },
        { horizon_days: 2, target_date: "2023-06-15", status: "unavailable", reason_code: "model_not_available" },
        { horizon_days: 3, target_date: "2023-06-16", status: "unavailable", reason_code: "model_not_available" },
      ],
    };
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batch);
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));
    const submit = vi.spyOn(historicalApi, "submitHistoricalReview").mockResolvedValue({
      status: "confirmed", revision: 1, review_open_at: "2023-06-14T00:00:00Z", reviewable: true,
      blocked_reason: null, latest_review: null, training_eligibility: "no_review", applied_review_references: [],
    });

    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    await userEvent.type(screen.getByLabelText(/emisión seleccionada/i), "2023-06-13");
    await userEvent.type(screen.getByLabelText(/recorrido hasta/i), "2023-06-20");
    await userEvent.click(await screen.findByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    await waitFor(() => expect(submit).toHaveBeenCalled());
    expect(submit).toHaveBeenCalledWith("sensor-a", "2023-06-20", "fc-1", expect.objectContaining({ action: "confirm" }));
  });

  it("clears the emission date and discards a late response for the date that was just cleared", async () => {
    const resolvers: Array<(batch: ForecastBatch) => void> = [];
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(
      () => new Promise((resolve) => resolvers.push(resolve)),
    );
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));

    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    const emissionInput = screen.getByLabelText(/emisión seleccionada/i);
    await userEvent.type(emissionInput, "2023-06-13");
    await waitFor(() => expect(resolvers).toHaveLength(1));

    await userEvent.clear(emissionInput);
    expect(screen.queryByText(/viendo la emisión del/i)).not.toBeInTheDocument();

    // The in-flight request for the date that was just cleared resolves
    // late: it must never repopulate the screen now that nothing is
    // selected.
    await act(async () => { resolvers[0](batchFor("2023-06-13", "14")); });
    expect(screen.queryByText(/viendo la emisión del/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/14 de jun/i)).not.toBeInTheDocument();
  });

  it("resets the selection and discards any in-flight request when the sensor changes", async () => {
    const resolvers: Array<(batch: ForecastBatch) => void> = [];
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(
      () => new Promise((resolve) => resolvers.push(resolve)),
    );
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));

    const view = render(<HistoricalWalkthrough sensorId="sensor-a" />);
    await userEvent.type(screen.getByLabelText(/emisión seleccionada/i), "2023-06-13");
    await waitFor(() => expect(resolvers).toHaveLength(1));

    view.rerender(<HistoricalWalkthrough sensorId="sensor-b" />);
    expect(screen.getByLabelText(/emisión seleccionada/i)).toHaveValue("");
    expect(screen.queryByText(/viendo la emisión del/i)).not.toBeInTheDocument();

    // sensor-a's stale in-flight response must never populate sensor-b's screen.
    await act(async () => { resolvers[0](batchFor("2023-06-13", "14")); });
    expect(screen.queryByText(/viendo la emisión del/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/14 de jun/i)).not.toBeInTheDocument();
  });

  it("ignores a review update that resolves after the user already navigated away from that emission", async () => {
    const batch = (() => {
      const b = batchFor("2023-06-13", "14");
      b.slots[0] = {
        status: "available", forecast_id: "fc-1", sensor_id: "sensor-a", batch_id: "batch-2023-06-13",
        as_of_date: "2023-06-13", horizon_days: 1, target_date: "2023-06-14",
        contract_version: "producer_daily_h123_v1", issued_at: "2023-06-13T00:05:00Z", snapshot_id: "snap-1",
        alert: false, score: 0.1, score_kind: "ensemble_mean_of_calibrated_components",
        display_probability: null, probability_status: "not_qualified", probability_reason_code: null,
        decision_threshold: 0.5, event_threshold: { variable: "soil_moisture", value: 0.18, unit: "m3/m3", comparison: "lt" },
        model_reference: { model_version: "v1", horizon_days: 1, contract_version: "producer_daily_h123_v1", trained_through: "2022-12-31", calibration_version: "cal-1", assessment_reference: "assessment-1" },
        review: { status: "pending", revision: 0, review_open_at: "2023-06-14T00:00:00Z", reviewable: true, blocked_reason: null, latest_review: null, training_eligibility: "no_review", applied_review_references: [] },
        ensemble: null,
      };
      return b;
    })();
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(async (_sid, asOfDate) =>
      asOfDate === "2023-06-13" ? batch : batchFor(asOfDate as string, "20"),
    );
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));
    let resolveSubmit!: (review: Awaited<ReturnType<typeof historicalApi.submitHistoricalReview>>) => void;
    vi.spyOn(historicalApi, "submitHistoricalReview").mockReturnValue(
      new Promise((resolve) => { resolveSubmit = resolve; }),
    );

    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    const emissionInput = screen.getByLabelText(/emisión seleccionada/i);
    await userEvent.type(emissionInput, "2023-06-13");
    await userEvent.click(await screen.findByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));

    // Navigate away before the review submission resolves.
    await userEvent.clear(emissionInput);
    await userEvent.type(emissionInput, "2023-06-14");
    await waitFor(() => expect(screen.getByLabelText(/emisión seleccionada/i)).toHaveValue("2023-06-14"));

    await act(async () => {
      resolveSubmit({
        status: "confirmed", revision: 1, review_open_at: "2023-06-14T00:00:00Z", reviewable: true,
        blocked_reason: null, latest_review: null, training_eligibility: "no_review", applied_review_references: [],
      });
    });
    // The stale confirmation must never resurrect the emission the user
    // already left, nor leak into the now-displayed one.
    expect(screen.queryByText(/confirmado por vos/i)).not.toBeInTheDocument();
    expect(await screen.findByText(/viendo la emisión del/i)).toBeInTheDocument();
  });
});
