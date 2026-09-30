import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ForecastCard } from "./ForecastCard";
import { TARGET_OBSERVATION_MESSAGES, TargetObservationBlockedError } from "./forecastsApi";
import type { Forecast, ReviewBlockedReason } from "./forecastsApi";

const forecast: Forecast = {
  forecast_id: "fc-1",
  sensor_id: "melchor-romero-demo",
  batch_id: "batch-1",
  as_of_date: "2024-10-23",
  horizon_days: 3,
  target_date: "2024-10-26",
  contract_version: "producer_daily_h123_v1",
  issued_at: "2024-10-23T00:05:00Z",
  snapshot_id: "snap-1",
  alert: false,
  score: 0.2,
  score_kind: "calibrated_probability",
  display_probability: null,
  probability_status: "not_qualified",
  probability_reason_code: null,
  decision_threshold: 0.5,
  event_threshold: { variable: "soil_moisture", value: 0.32, unit: "m3/m3", comparison: "lt" },
  model_reference: {
    model_version: "v1",
    horizon_days: 3,
    contract_version: "producer_daily_h123_v1",
    trained_through: "2024-10-22",
    calibration_version: "cal-1",
    assessment_reference: "assessment-1",
  },
  review: {
    status: "pending",
    revision: 0,
    review_open_at: "2024-10-26T00:00:00Z",
    reviewable: true,
    blocked_reason: null,
    latest_review: null,
    training_eligibility: "no_review",
    applied_review_references: [],
  },
  ensemble: null,
};

function blocked(reason: ReviewBlockedReason | null): Forecast {
  return {
    ...forecast,
    review: { ...forecast.review, reviewable: reason === null, blocked_reason: reason },
  };
}

const MESSAGES = {
  imputed:
    "No se puede revisar este pronóstico con el dato disponible: el valor del día objetivo fue imputado y no es una observación independiente.",
  missing: "No se puede revisar este pronóstico: no hay una observación disponible para el día objetivo.",
  unverified:
    "No se puede revisar este pronóstico: la procedencia del valor del día objetivo no está verificada.",
};

describe("ForecastCard: motivos de bloqueo por la observación del día objetivo", () => {
  beforeEach(() => vi.restoreAllMocks());

  it.each([
    ["target_observation_imputed", MESSAGES.imputed],
    ["target_observation_missing", MESSAGES.missing],
    ["target_observation_unverified", MESSAGES.unverified],
  ] as const)("%s: shows the explicit message and offers no review actions", (reason, message) => {
    render(<ForecastCard sensorId="melchor-romero-demo" forecast={blocked(reason)} historicalNotice="x" />);
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /confirmar resultado/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /rechazar resultado/i })).toBeNull();
  });

  it("keeps the existing temporal message for a target not yet revealed", () => {
    render(<ForecastCard sensorId="melchor-romero-demo" forecast={blocked("review_not_open")} />);
    expect(screen.getByText(/vas a poder revisar este resultado/i)).toBeInTheDocument();
  });

  it("an open form whose forecast becomes blocked disables saving, keeps the text and lets cancel, sending nothing", async () => {
    const submit = vi.fn();
    const { rerender } = render(
      <ForecastCard sensorId="melchor-romero-demo" forecast={blocked(null)} submitReviewFn={submit} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /confirmar resultado/i }));
    await userEvent.type(screen.getByLabelText(/comentario/i), "texto escrito");

    rerender(
      <ForecastCard
        sensorId="melchor-romero-demo"
        forecast={blocked("target_observation_imputed")}
        submitReviewFn={submit}
      />,
    );
    expect(screen.getByText(MESSAGES.imputed)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /guardar opinión/i })).toBeDisabled();
    expect(screen.getByLabelText(/comentario/i)).toHaveValue("texto escrito");
    expect(screen.getByRole("button", { name: /cancelar/i })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    expect(submit).not.toHaveBeenCalled();

    // Vuelve a ser revisable: se conserva lo escrito y puede enviarse.
    submit.mockResolvedValue({ ...forecast.review, status: "confirmed", revision: 1 });
    rerender(<ForecastCard sensorId="melchor-romero-demo" forecast={blocked(null)} submitReviewFn={submit} />);
    expect(screen.getByLabelText(/comentario/i)).toHaveValue("texto escrito");
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));
    expect(submit).toHaveBeenCalledTimes(1);
  });

  it("shows a real 409 from the backend when the state changed between the query and the POST", async () => {
    const submit = vi.fn().mockRejectedValue(new TargetObservationBlockedError("target_observation_missing"));
    render(<ForecastCard sensorId="melchor-romero-demo" forecast={blocked(null)} submitReviewFn={submit} />);
    await userEvent.click(screen.getByRole("button", { name: /confirmar resultado/i }));
    await userEvent.type(screen.getByLabelText(/comentario/i), "mi comentario");
    await userEvent.click(screen.getByRole("button", { name: /guardar opinión/i }));

    expect(await screen.findByText(MESSAGES.missing)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /guardar opinión/i })).toBeDisabled();
    expect(screen.getByLabelText(/comentario/i)).toHaveValue("mi comentario");
    expect(screen.getByRole("button", { name: /cancelar/i })).toBeEnabled();
  });

  it("uses the exact messages required by the decision", () => {
    expect(TARGET_OBSERVATION_MESSAGES.target_observation_imputed).toBe(MESSAGES.imputed);
    expect(TARGET_OBSERVATION_MESSAGES.target_observation_missing).toBe(MESSAGES.missing);
    expect(TARGET_OBSERVATION_MESSAGES.target_observation_unverified).toBe(MESSAGES.unverified);
  });
});
