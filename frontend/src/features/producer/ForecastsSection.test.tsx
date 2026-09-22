import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ForecastsSection } from "./ForecastsSection";
import * as forecastsApi from "./forecastsApi";
import type { Forecast, ForecastListResult } from "./forecastsApi";

function makeForecast(overrides: Partial<Forecast> = {}): Forecast {
  return {
    forecast_id: overrides.forecast_id ?? "fc-1",
    sensor_id: "sensor-a",
    batch_id: "batch-1",
    as_of_date: "2026-01-01",
    horizon_days: 1,
    target_date: "2026-01-02",
    contract_version: "producer_daily_h123_v1",
    issued_at: "2026-01-01T00:05:00Z",
    snapshot_id: "snap-1",
    alert: true,
    score: 0.72,
    score_kind: "calibrated_probability",
    display_probability: 0.72,
    probability_status: "development_assessed",
    probability_reason_code: null,
    decision_threshold: 0.5,
    event_threshold: { variable: "soil_moisture", value: 0.18, unit: "m3/m3", comparison: "lt" },
    model_reference: {
      model_version: "v1",
      horizon_days: 1,
      contract_version: "producer_daily_h123_v1",
      trained_through: "2025-12-31",
      calibration_version: "cal-1",
      assessment_reference: "assessment-1",
    },
    review: {
      status: "pending",
      revision: 0,
      review_open_at: "2026-01-02T00:00:00Z",
      reviewable: true,
      blocked_reason: null,
      latest_review: null,
      training_eligibility: "no_review",
      applied_review_references: [],
    },
    ...overrides,
  };
}

function listResult(items: Forecast[], overrides: Partial<ForecastListResult> = {}): ForecastListResult {
  return { items, next_cursor: null, pending_total: items.length, reviewable_pending_total: items.length, ...overrides };
}

describe("ForecastsSection", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows the honest empty state, never fabricated data, for both lists", async () => {
    vi.spyOn(forecastsApi, "listForecasts").mockResolvedValue(listResult([], { pending_total: 0, reviewable_pending_total: 0 }));
    render(<ForecastsSection sensorId="sensor-a" />);
    await screen.findByText(/todavía no hay pronósticos disponibles/i);
    expect(screen.getByText(/no tenés pronósticos pendientes de revisar/i)).toBeInTheDocument();
  });

  it("distinguishes an error from an empty history and can retry", async () => {
    const spy = vi
      .spyOn(forecastsApi, "listForecasts")
      .mockRejectedValueOnce(new Error("Fallo de red"))
      .mockRejectedValueOnce(new Error("Fallo de red"))
      .mockResolvedValue(listResult([]));
    render(<ForecastsSection sensorId="sensor-a" />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts).toHaveLength(2);
    await userEvent.click(within(alerts[0]).getByRole("button", { name: /reintentar/i }));
    await waitFor(() => expect(spy.mock.calls.length).toBeGreaterThanOrEqual(3));
  });

  it("shows pending/reviewable-now counts independent of the visible page", async () => {
    vi.spyOn(forecastsApi, "listForecasts").mockImplementation(async (_sensorId, filters) => {
      if (filters?.reviewStatus === "pending") {
        return listResult([makeForecast()], { pending_total: 5, reviewable_pending_total: 2 });
      }
      return listResult([]);
    });
    render(<ForecastsSection sensorId="sensor-a" />);
    await screen.findByText(/5 pendientes en total/i);
    expect(screen.getByText(/2 habilitados para revisar ahora/i)).toBeInTheDocument();
  });

  it("does not group different emissions that share a target date, and shows more with pagination", async () => {
    const first = makeForecast({ forecast_id: "fc-1", as_of_date: "2026-01-01", horizon_days: 2 });
    const second = makeForecast({ forecast_id: "fc-2", as_of_date: "2026-01-02", horizon_days: 1 });
    const spy = vi.spyOn(forecastsApi, "listForecasts").mockImplementation(async (_sensorId, filters) => {
      if (filters?.reviewStatus === "pending") return listResult([]);
      if (!filters?.cursor) return listResult([first], { next_cursor: "page-2" });
      return listResult([second], { next_cursor: null });
    });
    render(<ForecastsSection sensorId="sensor-a" />);
    await screen.findByRole("button", { name: "Ver más" });
    expect(screen.getAllByRole("article")).toHaveLength(1);
    await userEvent.click(screen.getByText("Ver historial de pronósticos"));
    await userEvent.click(screen.getByRole("button", { name: "Ver más" }));
    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(2));
    expect(spy).toHaveBeenLastCalledWith("sensor-a", expect.objectContaining({ cursor: "page-2" }));
  });

  it("discards a stale response from a previously selected sensor", async () => {
    let resolveFirst!: (value: ForecastListResult) => void;
    const spy = vi.spyOn(forecastsApi, "listForecasts").mockImplementation(async (sensorId) => {
      if (sensorId === "sensor-a") return new Promise((resolve) => { resolveFirst = resolve; });
      return listResult([]);
    });
    const { rerender } = render(<ForecastsSection sensorId="sensor-a" />);
    rerender(<ForecastsSection sensorId="sensor-b" />);
    await screen.findByText(/todavía no hay pronósticos disponibles/i);
    resolveFirst(listResult([makeForecast({ forecast_id: "fc-late" })]));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(screen.queryAllByRole("article")).toHaveLength(0);
    expect(screen.getByText(/todavía no hay pronósticos disponibles/i)).toBeInTheDocument();
  });

  it("moves a forecast out of the pending list once it stops being pending", async () => {
    const pendingForecast = makeForecast({ forecast_id: "fc-pending" });
    vi.spyOn(forecastsApi, "listForecasts").mockImplementation(async (_sensorId, filters) => {
      if (filters?.reviewStatus === "pending") return listResult([pendingForecast]);
      return listResult([pendingForecast]);
    });
    vi.spyOn(forecastsApi, "submitReview").mockResolvedValue({
      ...pendingForecast.review,
      status: "confirmed",
      revision: 1,
    });
    render(<ForecastsSection sensorId="sensor-a" />);
    await screen.findAllByText(/pendiente de revisar/i);
    const pendingSection = screen.getByRole("group", { name: "Pendientes de revisar" });
    const confirmButtons = within(pendingSection).getAllByRole("button", { name: /confirmar resultado/i });
    await userEvent.click(confirmButtons[0]);
    const saveButtons = within(pendingSection).getAllByRole("button", { name: /guardar opinión/i });
    await userEvent.click(saveButtons[0]);
    await waitFor(() => expect(within(pendingSection).getByText(/no tenés pronósticos pendientes de revisar/i)).toBeInTheDocument());
  });
});

it("offers an explicit restart when backend rejects an old cursor", async () => {
  const spy = vi.spyOn(forecastsApi, "listForecasts").mockImplementation(async (_sensorId, filters) => {
    if (filters?.reviewStatus === "pending") return listResult([]);
    if (filters?.cursor) throw new forecastsApi.ForecastCursorExpiredError();
    return listResult([makeForecast()], { next_cursor: "old-cursor" });
  });
  render(<ForecastsSection sensorId="sensor-a" />);
  await screen.findByText("Ver historial de pronósticos");
  await userEvent.click(screen.getByText("Ver historial de pronósticos"));
  await userEvent.click(await screen.findByRole("button", { name: "Ver más" }));
  await userEvent.click(await screen.findByRole("button", { name: "Volver a cargar la lista" }));
  await waitFor(() => expect(spy.mock.calls.filter(([, filters]) => !filters?.cursor && !filters?.reviewStatus)).toHaveLength(2));
});

it("shows a recoverable pagination failure without discarding the page", async () => {
  vi.spyOn(forecastsApi, "listForecasts").mockImplementation(async (_sensorId, filters) => {
    if (filters?.reviewStatus === "pending") return listResult([]);
    if (filters?.cursor) throw new Error("network");
    return listResult([makeForecast()], { next_cursor: "page-2" });
  });
  render(<ForecastsSection sensorId="sensor-a" />);
  await userEvent.click(screen.getByText("Ver historial de pronósticos"));
  await userEvent.click(await screen.findByRole("button", { name: "Ver más" }));
  expect(await screen.findByRole("button", { name: "Reintentar carga" })).toBeInTheDocument();
  expect(screen.getAllByRole("article")).toHaveLength(1);
});
afterEach(() => vi.restoreAllMocks());
