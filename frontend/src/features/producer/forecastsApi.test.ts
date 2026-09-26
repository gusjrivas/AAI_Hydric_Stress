import { afterEach, describe, expect, it, vi } from "vitest";
import { ProducerV2UnavailableError } from "./catalogApi";
import {
  DemoWriteLockedError,
  ForecastNotFoundError,
  ForecastCursorExpiredError,
  ReviewIdempotencyConflictError,
  ReviewNotOpenError,
  RevisionConflictError,
  displayProbability,
  getForecast,
  listForecasts,
  submitReview,
} from "./forecastsApi";
import type { Forecast } from "./forecastsApi";

afterEach(() => vi.unstubAllGlobals());

const forecast: Forecast = {
  forecast_id: "fc-1",
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
  ensemble: null,
};

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

describe("listForecasts", () => {
  it("builds the query string from filters and returns the list result", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, { items: [forecast], next_cursor: "c1", pending_total: 3, reviewable_pending_total: 2 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await listForecasts("sensor-a", { reviewStatus: "pending", horizonDays: 1, limit: 10, cursor: "c0" });
    expect(result.pending_total).toBe(3);
    const url = new URL(fetchMock.mock.calls[0][0]);
    expect(url.pathname).toBe("/api/v2/sensors/sensor-a/forecasts");
    expect(url.searchParams.get("review_status")).toBe("pending");
    expect(url.searchParams.get("horizon_days")).toBe("1");
    expect(url.searchParams.get("limit")).toBe("10");
    expect(url.searchParams.get("cursor")).toBe("c0");
  });

  it("treats a bodyless 404 as the v2 facade being unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => { throw new Error("no body"); } }));
    await expect(listForecasts("sensor-a")).rejects.toBeInstanceOf(ProducerV2UnavailableError);
  });
});

describe("getForecast", () => {
  it("returns the forecast when found", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, forecast)));
    await expect(getForecast("sensor-a", "fc-1")).resolves.toEqual(forecast);
  });

  it("maps forecast_not_found to ForecastNotFoundError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(404, { error: { code: "forecast_not_found", message: "no", details: {}, request_id: "r" } }),
      ),
    );
    await expect(getForecast("sensor-a", "fc-x")).rejects.toBeInstanceOf(ForecastNotFoundError);
  });
});

describe("submitReview", () => {
  const request = { requestId: "req-1", expectedRevision: 0, action: "confirm" as const, comment: null };

  it("sends the exact request body the contract expects", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, forecast.review));
    vi.stubGlobal("fetch", fetchMock);
    await submitReview("sensor-a", "fc-1", request);
    const [url, init] = fetchMock.mock.calls[0];
    expect(new URL(url).pathname).toBe("/api/v2/sensors/sensor-a/forecasts/fc-1/reviews");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      request_id: "req-1",
      expected_revision: 0,
      action: "confirm",
      comment: null,
    });
  });

  it("maps review_not_open with its review_open_at detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(409, {
          error: { code: "review_not_open", message: "no", details: { review_open_at: "2026-01-02T00:00:00Z" }, request_id: "r" },
        }),
      ),
    );
    const error = await submitReview("sensor-a", "fc-1", request).catch((e) => e);
    expect(error).toBeInstanceOf(ReviewNotOpenError);
    expect((error as ReviewNotOpenError).reviewOpenAt).toBe("2026-01-02T00:00:00Z");
  });

  it("maps revision_conflict with the actual revision", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(409, {
          error: { code: "revision_conflict", message: "no", details: { expected_revision: 0, actual_revision: 1 }, request_id: "r" },
        }),
      ),
    );
    const error = await submitReview("sensor-a", "fc-1", request).catch((e) => e);
    expect(error).toBeInstanceOf(RevisionConflictError);
    expect((error as RevisionConflictError).actualRevision).toBe(1);
  });

  it("maps idempotency_conflict", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(409, { error: { code: "idempotency_conflict", message: "no", details: {}, request_id: "r" } })),
    );
    await expect(submitReview("sensor-a", "fc-1", request)).rejects.toBeInstanceOf(ReviewIdempotencyConflictError);
  });

  it("maps demo_write_locked", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(409, { error: { code: "demo_write_locked", message: "no", details: {}, request_id: "r" } })),
    );
    await expect(submitReview("sensor-a", "fc-1", request)).rejects.toBeInstanceOf(DemoWriteLockedError);
  });

  it("maps forecast_not_found on review submission", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(404, { error: { code: "forecast_not_found", message: "no", details: {}, request_id: "r" } })),
    );
    await expect(submitReview("sensor-a", "fc-x", request)).rejects.toBeInstanceOf(ForecastNotFoundError);
  });

  it("treats a generic 5xx as a plain recoverable error, not a terminal one", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(503, { error: { code: "storage_unavailable", message: "no disponible", details: {}, request_id: "r" } })),
    );
    const error = await submitReview("sensor-a", "fc-1", request).catch((e) => e);
    expect(error).not.toBeInstanceOf(RevisionConflictError);
    expect(error).not.toBeInstanceOf(DemoWriteLockedError);
    expect((error as Error).message).toBe("no disponible");
  });
});

describe("displayProbability", () => {
  it("never renders 0% for a missing probability", () => {
    expect(displayProbability({ ...forecast, display_probability: null })).toBe("Probabilidad no disponible");
  });

  it("renders the published probability as a rounded percentage", () => {
    expect(displayProbability({ ...forecast, display_probability: 0.723 })).toBe("72 %");
  });
});

it("maps the backend invalid_cursor response to a recoverable list restart", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "invalid_cursor", message: "internal details" } }), { status: 422 })));
  await expect(listForecasts("sensor-a", { cursor: "old" })).rejects.toBeInstanceOf(ForecastCursorExpiredError);
});

it("explains an invalid date range without exposing backend terminology", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "invalid_date_range", message: "target_from invalid" } }), { status: 422 })));
  await expect(listForecasts("sensor-a", { targetFrom: "2026-09-10", targetTo: "2026-09-01" })).rejects.toThrow("La fecha inicial debe ser anterior o igual a la fecha final.");
});