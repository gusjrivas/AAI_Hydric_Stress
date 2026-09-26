import { afterEach, describe, expect, it, vi } from "vitest";
import { ProducerV2UnavailableError } from "./catalogApi";
import {
  BatchNotPreparedError,
  ForecastNotVisibleAtThisHistoricalDateError,
  InvalidRevealWindowError,
  getHistoricalForecastBatch,
  getHistoricalReadings,
  submitHistoricalReview,
} from "./historicalApi";

afterEach(() => vi.unstubAllGlobals());

describe("getHistoricalForecastBatch", () => {
  it("selects by as_of_date and forwards revealed_through as a separate query param, never merging the two dates", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await getHistoricalForecastBatch("sensor-a", "2023-06-13", "2023-06-20");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/historical/2023-06-13/forecasts?revealed_through=2023-06-20"),
    );
  });

  it("omits revealed_through when not provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await getHistoricalForecastBatch("sensor-a", "2023-06-13");
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/historical/2023-06-13/forecasts"));
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("revealed_through"));
  });

  it("distinguishes a date never emitted from a generic error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "batch_not_prepared", message: "x" } }), { status: 404 }),
      ),
    );
    await expect(getHistoricalForecastBatch("sensor-a", "2023-01-01")).rejects.toBeInstanceOf(BatchNotPreparedError);
  });

  it("surfaces an unavailable producer v2 facade as its own error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));
    await expect(getHistoricalForecastBatch("sensor-a", "2023-01-01")).rejects.toBeInstanceOf(ProducerV2UnavailableError);
  });

  it("rejects a reveal window earlier than the emission with a dedicated error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "invalid_reveal_window", message: "x" } }), { status: 422 }),
      ),
    );
    await expect(getHistoricalForecastBatch("sensor-a", "2023-06-14", "2023-06-13")).rejects.toBeInstanceOf(
      InvalidRevealWindowError,
    );
  });
});

describe("getHistoricalReadings", () => {
  it("reveals through the walked-forward clock, never a client-supplied end date", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await getHistoricalReadings("sensor-a", "2023-06-20", 10);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/historical/2023-06-20/readings?days=10"));
  });
});

describe("submitHistoricalReview", () => {
  it("posts to the historical route gated by the walked-forward clock", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "confirmed" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    await submitHistoricalReview("sensor-a", "2023-06-20", "fc-1", {
      requestId: "req-1",
      expectedRevision: 0,
      action: "confirm",
      comment: null,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/historical/2023-06-20/forecasts/fc-1/reviews"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("refuses to review a later emission's forecast from an earlier historical date with a dedicated error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: "forecast_not_visible_at_this_historical_date", message: "x" } }),
          { status: 404 },
        ),
      ),
    );
    await expect(
      submitHistoricalReview("sensor-a", "2023-06-13", "fc-later", {
        requestId: "req-1",
        expectedRevision: 0,
        action: "confirm",
        comment: null,
      }),
    ).rejects.toBeInstanceOf(ForecastNotVisibleAtThisHistoricalDateError);
  });
});
