import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ForecastCard } from "./ForecastCard";
import * as forecastsApi from "./forecastsApi";
import {
  DemoWriteLockedError,
  ReviewIdempotencyConflictError,
  ReviewNotOpenError,
  RevisionConflictError,
} from "./forecastsApi";
import type { Forecast } from "./forecastsApi";

const baseForecast: Forecast = {
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
};

describe("ForecastCard", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows the target date, probability and pending review status", () => {
    render(<ForecastCard sensorId="sensor-a" forecast={baseForecast} />);
    expect(screen.getByText(/pendiente de revisar/i)).toBeInTheDocument();
    expect(screen.getByText(/72 %/)).toBeInTheDocument();
  });

  it("never shows 0% when display_probability is missing", () => {
    render(<ForecastCard sensorId="sensor-a" forecast={{ ...baseForecast, display_probability: null }} />);
    expect(screen.getByText(/probabilidad no disponible/i)).toBeInTheDocument();
    expect(screen.queryByText(/0 %/)).not.toBeInTheDocument();
  });

  it("confirms a result with an optional comment and shows the saved outcome without a premature success message", async () => {
    const spy = vi.spyOn(forecastsApi, "submitReview").mockResolvedValue({
      ...baseForecast.review,
      status: "confirmed",
      revision: 1,
      latest_review: {
        review_id: "rev-1",
        request_id: "req-x",
        revision: 1,
        forecast_id: "fc-1",
        action: "confirm",
        observed_label: true,
        comment: "Vi el suelo seco",
        reviewed_at: "2026-01-02T10:00:00Z",
      },
    });
    render(<ForecastCard sensorId="sensor-a" forecast={baseForecast} />);
    await userEvent.click(screen.getByRole("button", { name: /confirmar resultado/i }));
    expect(screen.queryByText(/tu opinión quedó guardada/i)).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/comentario/i), "Vi el suelo seco");
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));

    await screen.findByText(/tu opinión quedó guardada/i);
    expect(screen.getByText(/no significa que ya se haya usado para entrenar/i)).toBeInTheDocument();
    expect(spy).toHaveBeenCalledWith(
      "sensor-a",
      "fc-1",
      expect.objectContaining({ action: "confirm", expectedRevision: 0, comment: "Vi el suelo seco" }),
    );
  });

  it("allows correcting a previously registered opinion", async () => {
    const reviewed: Forecast["review"] = {
      status: "confirmed",
      revision: 1,
      review_open_at: "2026-01-02T00:00:00Z",
      reviewable: true,
      blocked_reason: null,
      latest_review: {
        review_id: "rev-1",
        request_id: "req-x",
        revision: 1,
        forecast_id: "fc-1",
        action: "confirm",
        observed_label: true,
        comment: null,
        reviewed_at: "2026-01-02T10:00:00Z",
      },
      training_eligibility: "confirmation_only",
      applied_review_references: [],
    };
    vi.spyOn(forecastsApi, "submitReview").mockResolvedValue({ ...reviewed, status: "rejected", revision: 2 });
    render(<ForecastCard sensorId="sensor-a" forecast={{ ...baseForecast, review: reviewed }} />);
    expect(screen.getByText(/podés corregir tu opinión cuando quieras: no vence/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /rechazar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    await waitFor(() => expect(screen.getByText(/rechazado por vos/i)).toBeInTheDocument());
  });

  it("disables review controls before review_open_at and explains when it opens", () => {
    render(
      <ForecastCard
        sensorId="sensor-a"
        forecast={{
          ...baseForecast,
          review: { ...baseForecast.review, reviewable: false, blocked_reason: "review_not_open" },
        }}
      />,
    );
    expect(screen.queryByRole("button", { name: /confirmar resultado/i })).not.toBeInTheDocument();
    expect(screen.getByText(/vas a poder revisar este resultado a partir del/i)).toBeInTheDocument();
  });

  it("retries a recoverable error reusing the same request_id, without duplicating the submission", async () => {
    const spy = vi
      .spyOn(forecastsApi, "submitReview")
      .mockRejectedValueOnce(new Error("Fallo de red"))
      .mockResolvedValueOnce({ ...baseForecast.review, status: "confirmed", revision: 1 });
    render(<ForecastCard sensorId="sensor-a" forecast={baseForecast} />);
    await userEvent.click(screen.getByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    await screen.findByRole("alert");
    // El formulario se mantiene: no se pierde el intento ante un error recuperable.
    expect(screen.getByLabelText(/comentario/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /reintentar/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
    const [firstCallRequestId] = [spy.mock.calls[0][2].requestId, spy.mock.calls[1][2].requestId];
    expect(spy.mock.calls[1][2].requestId).toBe(firstCallRequestId);
  });

  it("does not overwrite someone else's review on a revision conflict, and refreshes from the server", async () => {
    vi.spyOn(forecastsApi, "submitReview").mockRejectedValue(new RevisionConflictError(1));
    const refreshed: Forecast = {
      ...baseForecast,
      review: {
        ...baseForecast.review,
        status: "rejected",
        revision: 1,
        latest_review: {
          review_id: "rev-2",
          request_id: "other",
          revision: 1,
          forecast_id: "fc-1",
          action: "reject",
          observed_label: false,
          comment: null,
          reviewed_at: "2026-01-02T09:00:00Z",
        },
      },
    };
    vi.spyOn(forecastsApi, "getForecast").mockResolvedValue(refreshed);
    render(<ForecastCard sensorId="sensor-a" forecast={baseForecast} />);
    await userEvent.click(screen.getByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    await screen.findByText(/se registró otra opinión mientras completabas este formulario/i);
    await waitFor(() => expect(screen.getByText(/rechazado por vos/i)).toBeInTheDocument());
  });

  it("shows a clear message when the same request_id was already used for different content", async () => {
    vi.spyOn(forecastsApi, "submitReview").mockRejectedValue(new ReviewIdempotencyConflictError());
    render(<ForecastCard sensorId="sensor-a" forecast={baseForecast} />);
    await userEvent.click(screen.getByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    await screen.findByText(/ya se había usado con otro contenido/i);
  });

  it("shows the demo lock explanation instead of a generic error", async () => {
    vi.spyOn(forecastsApi, "submitReview").mockRejectedValue(new DemoWriteLockedError());
    render(<ForecastCard sensorId="demo-x" forecast={baseForecast} />);
    await userEvent.click(screen.getByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    await screen.findByText(/no admite revisiones acá/i);
  });

  it("cancels a late review-not-open response without leaving the form open", async () => {
    vi.spyOn(forecastsApi, "submitReview").mockRejectedValue(new ReviewNotOpenError("2026-01-02T00:00:00Z"));
    render(<ForecastCard sensorId="sensor-a" forecast={baseForecast} />);
    await userEvent.click(screen.getByRole("button", { name: /confirmar resultado/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    await screen.findByText(/todavía no se puede revisar este resultado/i);
    expect(screen.queryByLabelText(/comentario/i)).not.toBeInTheDocument();
  });
});
