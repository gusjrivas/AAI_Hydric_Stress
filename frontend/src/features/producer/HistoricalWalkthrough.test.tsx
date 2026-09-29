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
  it("shows a recoverable reading error instead of leaving posterior observations loading", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batchFor("2023-06-13", "13"));
    const readings = vi.spyOn(historicalApi, "getHistoricalReadings")
      .mockRejectedValueOnce(new Error("Sin conexión"))
      .mockResolvedValueOnce({
        sensor_id: "pergamino-ensemble-demo", calendar_timezone: "UTC", server_today: "2023-06-13",
        snapshot_id: null, window: { start_date: "2023-06-04", end_date: "2023-06-13", expected_days: 10 },
        status: "ready", rows: [], missing_dates: ["2023-06-13"], variable_coverage: [], units: {},
        last_reading_date: null, data_age_days: null, provenance: "external_reanalysis",
      });
    render(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    expect(await screen.findAllByText(/no se pudo consultar la observación/i)).not.toHaveLength(0);
    expect(screen.queryByText(/cargando dato posterior/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: /reintentar lecturas/i })[0]);
    await waitFor(() => expect(readings).toHaveBeenCalledTimes(2));
    expect(await screen.findAllByText(/sin observación en la fuente/i)).not.toHaveLength(0);
  });

  it("limits defense navigation to the five persisted emission dates and does not show a later target as observed", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batchFor("2023-06-13", "14"));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue({
      sensor_id: "pergamino-ensemble-demo", calendar_timezone: "UTC", server_today: "2023-06-13",
      snapshot_id: null, window: { start_date: "2023-06-04", end_date: "2023-06-13", expected_days: 10 },
      status: "ready", rows: [], missing_dates: ["2023-06-12"], variable_coverage: [], units: {},
      last_reading_date: null, data_age_days: null, provenance: "external_reanalysis",
    });
    render(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    const select = screen.getByLabelText(/emisión seleccionada/i);
    expect(select).toHaveValue("2023-06-13");
    expect(screen.getAllByRole("option")).toHaveLength(5);
    expect(await screen.findAllByText(/todavía no disponible según el reloj/i)).toHaveLength(3);
    expect(screen.getByText(/1 fecha sin datos/i)).toBeInTheDocument();
    expect(historicalApi.getHistoricalForecastBatch).toHaveBeenCalledWith("pergamino-ensemble-demo", "2023-06-13", undefined);
  });
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

  function slotWithReviewable(reviewable: boolean) {
    return {
      status: "available" as const,
      forecast_id: "fc-1",
      sensor_id: "sensor-a",
      batch_id: "batch-2023-06-13",
      as_of_date: "2023-06-13",
      horizon_days: 1 as const,
      target_date: "2023-06-14",
      contract_version: "producer_daily_h123_v1",
      issued_at: "2023-06-13T00:05:00Z",
      snapshot_id: "snap-1",
      alert: false,
      score: 0.1,
      score_kind: "ensemble_mean_of_calibrated_components" as const,
      display_probability: null,
      probability_status: "not_qualified" as const,
      probability_reason_code: null,
      decision_threshold: 0.5,
      event_threshold: { variable: "soil_moisture", value: 0.18, unit: "m3/m3", comparison: "lt" as const },
      model_reference: {
        model_version: "v1", horizon_days: 1 as const, contract_version: "producer_daily_h123_v1",
        trained_through: "2022-12-31", calibration_version: "cal-1", assessment_reference: "assessment-1",
      },
      review: {
        status: "pending" as const, revision: 0, review_open_at: "2023-06-14T00:00:00Z",
        reviewable, blocked_reason: reviewable ? null : ("review_not_open" as const), latest_review: null,
        training_eligibility: "no_review" as const, applied_review_references: [],
      },
      ensemble: null,
    };
  }

  it("distinguishes an alert from missing horizons in the defense summary", async () => {
    const batch = batchFor("2023-06-13", "14");
    batch.slots[0] = { ...slotWithReviewable(false), alert: true };
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batch);
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue({
      sensor_id: "pergamino-ensemble-demo", calendar_timezone: "UTC", server_today: "2023-06-13",
      snapshot_id: null, window: { start_date: "2023-06-04", end_date: "2023-06-13", expected_days: 10 },
      status: "ready", rows: [{
        date: "2023-06-13", soil_moisture: 0.375, relative_humidity: null, solar_radiation: null,
        temperature: null, precipitation: null, wind_speed: null, et0: null,
        origin: "external_reanalysis", quality_flags: [], imputed_variables: [],
      }], missing_dates: ["2023-06-12"], variable_coverage: [], units: {},
      last_reading_date: null, data_age_days: null, provenance: "external_reanalysis",
    });

    render(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    expect(await screen.findByText("1 de 1 horizonte disponible con alerta prevista")).toBeInTheDocument();
    expect(screen.getByText(/1 fecha sin datos/i)).toBeInTheDocument();
    expect(screen.getByText(/era5-land\/nasa power \(datos externos\)/i)).toBeInTheDocument();
    expect(screen.getAllByText(/sin pronóstico disponible/i)).toHaveLength(2);
    expect(screen.getAllByText(/37\.5 %/i)).toHaveLength(2);
    expect(screen.getByText(/18\.0 %/i)).toBeInTheDocument();
  });

  it("a submit response from an earlier reveal clock never overrides the card after the clock moved back on the same emission", async () => {
    // Misma emisión (13/06) en todo momento: solo cambia `revealedThrough`
    // (20/06 -> 13/06), que es exactamente el caso que la comparación por
    // `forecast_id` sola no puede distinguir.
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(async (_sid, _asOfDate, revealedThrough) => {
      const reviewable = revealedThrough === "2023-06-20";
      const batch = batchFor("2023-06-13", "14");
      batch.slots[0] = slotWithReviewable(reviewable);
      return batch;
    });
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));
    let resolveSubmit!: (review: Awaited<ReturnType<typeof historicalApi.submitHistoricalReview>>) => void;
    vi.spyOn(historicalApi, "submitHistoricalReview").mockReturnValue(
      new Promise((resolve) => { resolveSubmit = resolve; }),
    );

    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    const emissionInput = screen.getByLabelText(/emisión seleccionada/i);
    const revealInput = screen.getByLabelText(/recorrido hasta/i);
    await userEvent.type(emissionInput, "2023-06-13");
    await userEvent.type(revealInput, "2023-06-20");
    await userEvent.click(await screen.findByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));

    // Retroceder el reloj del recorrido a la propia fecha de emisión,
    // antes de que la respuesta del envío llegue.
    await userEvent.clear(revealInput);
    await userEvent.type(revealInput, "2023-06-13");
    await waitFor(() => expect(screen.getByText(/vas a poder revisar este resultado a partir del/i)).toBeInTheDocument());

    await act(async () => {
      resolveSubmit({
        status: "confirmed", revision: 1, review_open_at: "2023-06-14T00:00:00Z", reviewable: true,
        blocked_reason: null, latest_review: null, training_eligibility: "no_review", applied_review_references: [],
      });
    });
    // La tarjeta debe seguir reflejando el reloj vigente (13/06,
    // reviewable=false), nunca el reviewable=true de la respuesta tardía
    // originada bajo el reloj anterior (20/06).
    expect(screen.queryByText(/confirmado por vos/i)).not.toBeInTheDocument();
    expect(screen.getByText(/vas a poder revisar este resultado a partir del/i)).toBeInTheDocument();
  });

  it("discards a stale response when only the reveal clock changes A -> B -> A on the same emission", async () => {
    const resolvers: Array<(batch: ForecastBatch) => void> = [];
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(
      () => new Promise((resolve) => resolvers.push(resolve)),
    );
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));

    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    const emissionInput = screen.getByLabelText(/emisión seleccionada/i);
    const revealInput = screen.getByLabelText(/recorrido hasta/i);
    await userEvent.type(emissionInput, "2023-06-13");
    await waitFor(() => expect(resolvers).toHaveLength(1)); // request for revealedThrough = emissionDate

    await userEvent.type(revealInput, "2023-06-20"); // A -> B
    await userEvent.clear(revealInput); // B -> back to A (clearing falls back to emissionDate)
    await userEvent.type(revealInput, "2023-06-13"); // re-typed explicitly: A again
    await waitFor(() => expect(resolvers.length).toBeGreaterThanOrEqual(3));
    const lastIndex = resolvers.length - 1;

    // Resolve every earlier request out of order, all with distinguishable
    // content: none of them may be the one left on screen.
    await act(async () => {
      for (let i = 0; i < lastIndex; i += 1) {
        resolvers[i](batchFor("2023-06-13", "17"));
      }
    });
    expect(screen.queryByText(/17 de jun/i)).not.toBeInTheDocument();

    await act(async () => {
      resolvers[lastIndex](batchFor("2023-06-13", "18")); // the current, last-issued request
    });
    expect(await screen.findAllByText(/18 de jun/i)).not.toHaveLength(0);
  });

  it("ignores a late error and a late conflict-recovery from an earlier context", async () => {
    let callCount = 0;
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(async () => {
      callCount += 1;
      const batch = batchFor("2023-06-13", "14");
      batch.slots[0] = slotWithReviewable(true);
      return batch;
    });
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));
    let rejectSubmit!: (error: Error) => void;
    vi.spyOn(historicalApi, "submitHistoricalReview").mockReturnValue(
      new Promise((_resolve, reject) => { rejectSubmit = reject; }),
    );

    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    const emissionInput = screen.getByLabelText(/emisión seleccionada/i);
    await userEvent.type(emissionInput, "2023-06-13");
    await userEvent.click(await screen.findByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));

    // Navigate away (new emission) before the rejected submit resolves.
    await userEvent.clear(emissionInput);
    await userEvent.type(emissionInput, "2023-06-14");
    await waitFor(() => expect(callCount).toBeGreaterThanOrEqual(2));

    await act(async () => { rejectSubmit(new Error("Fallo de red")); });

    // The old (now-unmounted) card's own error notice never appears on
    // the current context, and the current context's own cards remain
    // reviewable as freshly fetched, untouched by the stale rejection.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(await screen.findAllByRole("button", { name: /confirmar resultado/i })).not.toHaveLength(0);
  });

  it("generalizes to a second real site (Melchor Romero) without leaking Pergamino's dates, reveal limit, or provenance text, and resets cleanly A -> B -> A", async () => {
    const resolvers: Array<(batch: ForecastBatch) => void> = [];
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(
      () => new Promise((resolve) => resolvers.push(resolve)),
    );
    vi.spyOn(historicalApi, "getHistoricalReadings").mockReturnValue(new Promise(() => {}));

    const view = render(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    expect(screen.getByLabelText(/emisión seleccionada/i)).toHaveValue("2023-06-13");
    expect(screen.getByText(/Origen: Pergamino/i)).toBeInTheDocument();
    await waitFor(() => expect(resolvers).toHaveLength(1));

    // A (Pergamino) -> B (Melchor Romero): a different site, own dates,
    // own reveal limit, own provenance text -- never Pergamino's.
    view.rerender(
      <HistoricalWalkthrough
        sensorId="melchor-romero-demo"
        defense
        availableDates={["2024-10-20", "2024-10-21", "2024-10-22", "2024-10-23", "2024-10-24"]}
        revealMax="2024-10-27"
        provenanceNotice={<p className="historical-provenance">Origen: Melchor Romero · ESA CCI/NASA POWER.</p>}
      />,
    );
    expect(screen.getByLabelText(/emisión seleccionada/i)).toHaveValue("2024-10-20");
    expect(screen.getByText(/Origen: Melchor Romero/i)).toBeInTheDocument();
    expect(screen.queryByText(/Origen: Pergamino/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/13 al 17 de junio/i)).not.toBeInTheDocument();

    // Pergamino's stale in-flight response must never populate Melchor
    // Romero's screen after the switch: the clock still reflects Melchor
    // Romero's own selected emission (2024-10-20), never Pergamino's.
    await act(async () => { resolvers[0](batchFor("2023-06-13", "14")); });
    expect(screen.getByText(/viendo la emisión del/i)).toHaveTextContent(/20 de oct de 2024/i);
    expect(screen.queryByText(/13 de jun/i)).not.toBeInTheDocument();

    // B -> A again: back to Pergamino, with no Melchor Romero residue.
    view.rerender(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    expect(screen.getByLabelText(/emisión seleccionada/i)).toHaveValue("2023-06-13");
    expect(screen.getByText(/Origen: Pergamino/i)).toBeInTheDocument();
    expect(screen.queryByText(/Origen: Melchor Romero/i)).not.toBeInTheDocument();
  });

  it("F01: labels an imputed soil-moisture value explicitly (never as a plain real observation), labels a genuinely absent value as such, and excludes imputed days from the observed-coverage count", async () => {
    const batch = batchFor("2024-10-23", "26");
    batch.as_of_date = "2024-10-23";
    batch.slots = [
      { horizon_days: 1, target_date: "2024-10-24", status: "unavailable", reason_code: "model_not_available" },
      { horizon_days: 2, target_date: "2024-10-25", status: "unavailable", reason_code: "model_not_available" },
      { horizon_days: 3, target_date: "2024-10-26", status: "unavailable", reason_code: "model_not_available" },
    ];
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batch);
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue({
      sensor_id: "melchor-romero-demo", calendar_timezone: "UTC", server_today: "2024-10-27",
      snapshot_id: null, window: { start_date: "2024-10-18", end_date: "2024-10-27", expected_days: 10 },
      status: "ready",
      rows: [
        {
          date: "2024-10-25", soil_moisture: 0.3632737398, relative_humidity: 70, solar_radiation: 18,
          temperature: null, precipitation: null, wind_speed: null, et0: null,
          origin: "real", quality_flags: [], imputed_variables: [],
        },
        {
          // 26/10: la fuente no tenía dato; el frame preparado lo rellena
          // por forward-fill desde el 25/10 -- debe identificarse como
          // imputado, nunca como observación real independiente (F01).
          date: "2024-10-26", soil_moisture: 0.3632737398, relative_humidity: 71, solar_radiation: 17,
          temperature: null, precipitation: null, wind_speed: null, et0: null,
          origin: "real", quality_flags: ["imputed:soil_moisture"], imputed_variables: ["soil_moisture"],
        },
        {
          date: "2024-10-27", soil_moisture: null, relative_humidity: 72, solar_radiation: null,
          temperature: null, precipitation: null, wind_speed: null, et0: null,
          origin: "real", quality_flags: [], imputed_variables: [],
        },
      ],
      missing_dates: [],
      variable_coverage: [{ variable: "soil_moisture", observed_days: 8, missing_days: 1, imputed_days: 1 }],
      units: { soil_moisture: "m3/m3" },
      last_reading_date: "2024-10-26", data_age_days: 1, provenance: "real",
    });

    render(
      <HistoricalWalkthrough
        sensorId="melchor-romero-demo"
        defense
        availableDates={["2024-10-20", "2024-10-21", "2024-10-22", "2024-10-23", "2024-10-24"]}
        revealMax="2024-10-27"
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText(/emisión seleccionada/i), "2024-10-23");
    await userEvent.type(screen.getByLabelText(/recorrido hasta/i), "2024-10-27");

    // Emisiones 23/10 +3 y 24/10 +2 apuntan al 26/10: el valor se muestra
    // pero identificado explícitamente como imputado, nunca implicando que
    // es una observación real con la que contrastar el pronóstico.
    expect(await screen.findByText(/valor imputado/i)).toBeInTheDocument();
    expect(screen.getByText(/no es una observación independiente/i)).toBeInTheDocument();

    // 27/10: sin dato en la fuente -- rótulo explícito, nunca "no disponible" genérico.
    expect(screen.getAllByText(/sin observación en la fuente/i).length).toBeGreaterThan(0);

    // 25/10: observación real conservada, contrastable, y distinguida del 26/10 imputado.
    expect(screen.getAllByText(/fuente real/i).length).toBeGreaterThan(0);

    // Cobertura: el día imputado no cuenta como observación.
    await userEvent.click(screen.getByText(/ver disponibilidad por variable/i));
    expect(
      screen.getByText(/8 días con dato, 1 sin dato, 1 imputado \(no cuenta como observación\)/i),
    ).toBeInTheDocument();
  });
});
