import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ForecastCard } from "./ForecastCard";
import type { Forecast, ForecastReview } from "./forecastsApi";

const reference = {
  model_version: "v1", horizon_days: 1 as const, contract_version: "producer_daily_h123_v1",
  trained_through: "2025-12-31", calibration_version: "cal-1", assessment_reference: "assessment-1",
};

function forecast(alert: boolean, votes: 0 | 1 | 2 | 3): Forecast {
  const families = ["logistic_regression", "random_forest", "hist_gradient_boosting_classifier"] as const;
  const categories = {
    0: "sin_alerta_por_unanimidad", 1: "sin_alerta_por_mayoria_con_discrepancia",
    2: "posible_alerta_acuerdo_parcial", 3: "alerta_por_unanimidad",
  } as const;
  return {
    forecast_id: "fc-1", sensor_id: "pergamino-ensemble-demo", batch_id: "b-1", as_of_date: "2023-06-13",
    horizon_days: 1, target_date: "2023-06-14", contract_version: "producer_daily_h123_v1",
    issued_at: "2023-06-13T00:05:00Z", snapshot_id: "s-1", alert, score: 0.61, score_kind: "calibrated_probability",
    display_probability: 0.61, probability_status: "development_assessed", probability_reason_code: null,
    decision_threshold: 0.5, event_threshold: { variable: "soil_moisture", value: 0.255, unit: "m3/m3", comparison: "lt" },
    model_reference: reference,
    review: {
      status: "pending", revision: 0, review_open_at: "2023-06-14T00:00:00Z", reviewable: true, blocked_reason: null,
      latest_review: null, training_eligibility: "no_review", applied_review_references: [],
    },
    ensemble: {
      policy_version: "ensemble_agreement_v1", ensemble_identity_sha256: "abc",
      weights: { logistic_regression: 1 / 3, random_forest: 1 / 3, hist_gradient_boosting_classifier: 1 / 3 },
      components: families.map((family, index) => ({
        family, model_reference: reference, calibrated_through: "2025-12-31", score: 0.123 + index / 10,
        decision_threshold: 0.5, alert: index < votes,
      })),
      combined_probability: 0.61, combined_alert: alert, positive_votes: votes,
      agreement_category: categories[votes], calibrated_through: "2025-12-31",
    },
  };
}

const NOTICE = "Revisión de prueba técnica en modo histórico: queda aislada del historial operativo real, no se incorpora a reentrenamiento ni recalibración.";
const savedReview = (action: "confirm" | "reject"): ForecastReview => ({
  status: action === "confirm" ? "confirmed" : "rejected", revision: 1, review_open_at: "2023-06-14T00:00:00Z",
  reviewable: true, blocked_reason: null, training_eligibility: "no_review", applied_review_references: [],
  latest_review: { action, comment: null, reviewed_at: "2023-06-14T10:00:00Z" } as ForecastReview["latest_review"],
});

describe("ForecastCard compact", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows neither a probability message nor model scores", () => {
    render(<ForecastCard sensorId="s" forecast={forecast(true, 3)} historicalNotice={NOTICE} compact />);
    expect(screen.queryByText(/probabilidad/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/posibilidad de alerta/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\d\s?%/)).not.toBeInTheDocument();
  });

  it("states the vote count and lists each model without its score", async () => {
    render(<ForecastCard sensorId="s" forecast={forecast(true, 2)} historicalNotice={NOTICE} compact />);
    expect(screen.getByText(/2 de 3 modelos indican alerta/i)).toBeInTheDocument();
    await userEvent.click(screen.getByText(/ver qué indicó cada modelo/i));
    const items = screen.getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "Regresión logística: indica alerta",
      "Random Forest: indica alerta",
      "HistGradientBoosting: no indica alerta",
    ]);
  });

  it("names the model count as agreement between models, as the memoria does, not as a vote", () => {
    render(<ForecastCard sensorId="s" forecast={forecast(false, 2)} historicalNotice={NOTICE} compact />);
    expect(screen.getByText(/acuerdo entre modelos:/i)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/votaci/i);
  });

  it("does not claim the vote count is the decision rule", () => {
    render(<ForecastCard sensorId="s" forecast={forecast(false, 2)} historicalNotice={NOTICE} compact />);
    expect(screen.getByText(/no es una explicación de causas/i)).toBeInTheDocument();
    expect(screen.queryByText(/por votación|regla de votación/i)).not.toBeInTheDocument();
  });

  it.each([
    ["alerta", true, 3, "Confirmar", "confirm"],
    ["ausencia de alerta", false, 0, "Confirmar", "confirm"],
    ["alerta", true, 3, "Rechazar", "reject"],
    ["ausencia de alerta", false, 0, "Rechazar", "reject"],
  ] as const)("lets the person %s be reviewed: %s resultado", async (_label, alert, votes, button, action) => {
    const submit = vi.fn().mockResolvedValue(savedReview(action));
    render(<ForecastCard sensorId="s" forecast={forecast(alert, votes)} historicalNotice={NOTICE} compact submitReviewFn={submit} />);
    const decision = alert ? "Alerta" : "Sin alerta";
    expect(screen.getByText(new RegExp(`¿Coincidió «${decision}» con lo que observaste\\?`, "i"))).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: new RegExp(`${button} resultado`, "i") }));
    expect(screen.getByText(new RegExp(`(Confirmo|Rechazo) la decisión mostrada «${decision}»`, "i"))).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/comentario/i), "visto en campo");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(submit).toHaveBeenCalledTimes(1);
    expect(submit.mock.calls[0][2]).toMatchObject({ action, comment: "visto en campo", expectedRevision: 0 });
    expect(await screen.findByText(/registraste/i)).toHaveTextContent(action === "confirm" ? "Confirmar" : "Rechazar");
  });

  it("keeps the technical-test notice visible and blocks review before the target is revealed", () => {
    const blocked = forecast(false, 0);
    blocked.review = { ...blocked.review, reviewable: false, blocked_reason: "review_not_open" };
    render(<ForecastCard sensorId="s" forecast={blocked} historicalNotice={NOTICE} compact />);
    expect(screen.getByText(NOTICE)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /confirmar resultado/i })).not.toBeInTheDocument();
    expect(within(document.body).getByText(/todavía no se puede revisar|vas a poder revisar/i)).toBeInTheDocument();
  });

  it("leaves the default card unchanged: probability message and scores remain outside compact mode", async () => {
    render(<ForecastCard sensorId="s" forecast={forecast(true, 2)} historicalNotice={NOTICE} />);
    expect(screen.getByText(/posibilidad de alerta/i)).toBeInTheDocument();
    await userEvent.click(screen.getByText(/ver detalle por modelo/i));
    expect(screen.getAllByText(/score 0\.\d{3}/i).length).toBe(3);
  });
});
