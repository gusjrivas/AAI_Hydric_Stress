import { useState } from "react";
import { useForecastReviews } from "./useForecastReviews";
import {
  DemoWriteLockedError,
  ForecastNotFoundError,
  ReviewIdempotencyConflictError,
  ReviewNotOpenError,
  RevisionConflictError,
  displayForecastDate,
  displayIssuedAt,
  displayProbability,
  getForecast,
  newRequestId,
  reviewStatusLabel,
  submitReview,
} from "./forecastsApi";
import type { Forecast, ReviewAction } from "./forecastsApi";

const HORIZON_LABELS: Record<1 | 2 | 3, string> = {
  1: "1 día después de la medición",
  2: "2 días después de la medición",
  3: "3 días después de la medición",
};

function reviewActionCopy(forecast: Forecast): Record<ReviewAction, string> {
  return forecast.alert
    ? {
        confirm: "Sí, hubo señales de falta de agua ese día.",
        reject: "No, el suelo no mostró falta de agua ese día.",
      }
    : {
        confirm: "Sí, no hubo falta de agua, tal como indicó el pronóstico.",
        reject: "No, sí hubo falta de agua aunque el pronóstico no alertó.",
      };
}

interface Draft {
  action: ReviewAction;
  comment: string;
}

export function ForecastCard({
  sensorId,
  forecast: initialForecast,
  onChanged,
}: {
  sensorId: string;
  forecast: Forecast;
  onChanged?: (forecast: Forecast) => void;
}) {
  const [localForecast, setForecast] = useState(initialForecast);
  const { updates, publish } = useForecastReviews();
  const shared = updates[initialForecast.forecast_id];
  const candidates = [localForecast, initialForecast, ...(shared ? [shared] : [])];
  const forecast = candidates.reduce((latest, value) => value.review.revision >= latest.review.revision ? value : latest);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const review = forecast.review;
  const isCorrecting = review.status !== "pending";
  const frozen = submitting || formError !== null;

  function openForm(action: ReviewAction) {
    setNotice(null);
    setDraft({ action, comment: review.latest_review?.comment ?? "" });
    setRequestId(newRequestId());
    setFormError(null);
  }

  function cancel() {
    setDraft(null);
    setRequestId(null);
    setFormError(null);
  }

  async function submit() {
    if (!draft || !requestId || submitting) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const updatedReview = await submitReview(sensorId, forecast.forecast_id, {
        requestId,
        expectedRevision: review.revision,
        action: draft.action,
        comment: draft.comment.trim() ? draft.comment.trim() : null,
      });
      const updated = { ...forecast, review: updatedReview };
      setForecast(updated);
      setDraft(null);
      setRequestId(null);
      setSubmitting(false);
      setNotice(
        "Tu opinión quedó guardada. El pronóstico original se conserva. Los próximos resultados no cambian automáticamente.",
      );
      publish(updated);
      onChanged?.(updated);
      return;
    } catch (error) {
      setSubmitting(false);
      if (error instanceof RevisionConflictError) {
        setDraft(null);
        setRequestId(null);
        setNotice("Se registró otra opinión mientras completabas este formulario.");
        try {
          const fresh = await getForecast(sensorId, forecast.forecast_id);
          setForecast(fresh);
          setNotice("Se registró otra opinión. Ya estás viendo el resultado actualizado.");
          publish(fresh);
          onChanged?.(fresh);
        } catch {
          setNotice("No pudimos recuperar la última opinión. Recargá la página antes de volver a revisar este resultado.");
        }
        return;
      }
      if (error instanceof ReviewIdempotencyConflictError) {
        setDraft(null);
        setRequestId(null);
        setNotice("Ese envío ya se había usado con otro contenido. Iniciá la revisión de nuevo si hace falta.");
        return;
      }
      if (error instanceof DemoWriteLockedError) {
        setDraft(null);
        setRequestId(null);
        setNotice(error.message);
        return;
      }
      if (error instanceof ReviewNotOpenError) {
        setDraft(null);
        setRequestId(null);
        setNotice("Todavía no se puede revisar este resultado.");
        return;
      }
      if (error instanceof ForecastNotFoundError) {
        setDraft(null);
        setRequestId(null);
        setNotice(error.message);
        return;
      }
      // Error recuperable (red, servidor no disponible): se conserva el
      // formulario y el mismo request_id para no duplicar el envío al reintentar.
      setFormError(error instanceof Error ? error.message : "No se pudo enviar la revisión.");
    }
  }

  return (
    <article className={`forecast-card ${forecast.alert ? "forecast-card-alert" : "forecast-card-clear"}`} aria-label={`Pronóstico para el ${displayForecastDate(forecast.target_date)}`}>
      <header className="forecast-card-header">
        <div>
          <p className="forecast-card-target">{displayForecastDate(forecast.target_date)}</p>
          <details className="forecast-card-details"><summary>Ver de cuándo son los datos</summary><p className="forecast-card-meta">
            {HORIZON_LABELS[forecast.horizon_days]} · Emitido el {displayIssuedAt(forecast.issued_at)} a partir de
            datos del {displayForecastDate(forecast.as_of_date)}
          </p></details>
        </div>
        <span className={`forecast-card-badge ${forecast.alert ? "is-alert" : ""}`}>
          {forecast.alert ? "Alerta" : "Sin alerta"}
        </span>
      </header>

      <p className="forecast-card-guidance">{forecast.alert ? "Puede haber falta de agua. Revisá cómo está el cultivo." : "No se anticipa una alerta para esta fecha. Seguí observando el cultivo."}</p>
      <p className="forecast-probability">{forecast.display_probability === null ? "Probabilidad no disponible: todavía no hay un porcentaje respaldado para mostrar." : `Posibilidad de alerta: ${displayProbability(forecast)}`}</p>
      <p className="forecast-card-review-status">Revisión: {reviewStatusLabel(review.status)}</p>

      {review.latest_review && (
        <p className="forecast-card-latest-review">
          Registraste «{review.latest_review.action === "confirm" ? "Confirmar" : "Rechazar"}» el{" "}
          {displayIssuedAt(review.latest_review.reviewed_at)}
          {review.latest_review.comment ? `: "${review.latest_review.comment}"` : "."}
        </p>
      )}

      {notice && <p role="status">{notice}</p>}

      {!review.reviewable && !draft && (
        <p className="forecast-card-blocked">
          {review.blocked_reason === "review_not_open"
            ? `Vas a poder revisar este resultado a partir del ${displayIssuedAt(review.review_open_at)}.`
            : "Todavía no se puede revisar este resultado."}
        </p>
      )}

      {review.reviewable && !draft && (
        <div className="forecast-card-actions">
          <p>¿Coincidió con lo que observaste?</p>
          <div className="forecast-card-buttons">
            <button type="button" onClick={() => openForm("confirm")}>
              Confirmar resultado
            </button>
            <button type="button" onClick={() => openForm("reject")}>
              Rechazar resultado
            </button>
          </div>
          {isCorrecting && <p className="forecast-card-hint">Podés corregir tu opinión cuando quieras: no vence.</p>}
        </div>
      )}

      {draft && (
        <form
          className="forecast-card-form"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <p>{reviewActionCopy(forecast)[draft.action]}</p>
          <label>
            Comentario (opcional)
            <textarea
              value={draft.comment}
              maxLength={2000}
              disabled={frozen}
              onChange={(event) => setDraft({ ...draft, comment: event.target.value })}
            />
          </label>
          {formError && (
            <p role="alert">
              {formError} El envío no se duplicará: al reintentar se usa la misma solicitud.
            </p>
          )}
          <div className="forecast-card-buttons">
            {formError ? (
              <button type="button" onClick={() => void submit()} disabled={submitting}>
                Reintentar
              </button>
            ) : (
              <button type="submit" disabled={submitting}>
                {submitting ? "Guardando…" : "Guardar opinión"}
              </button>
            )}
            <button type="button" onClick={cancel} disabled={submitting}>
              Cancelar
            </button>
          </div>
        </form>
      )}
    </article>
  );
}
