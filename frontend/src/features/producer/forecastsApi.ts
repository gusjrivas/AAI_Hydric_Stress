import { API_BASE_URL } from "../../api/baseUrl";
import { ProducerV2UnavailableError } from "./catalogApi";

export type ReviewStatus = "pending" | "confirmed" | "rejected";
export type ReviewAction = "confirm" | "reject";

export interface EventThreshold {
  variable: string;
  value: number;
  unit: string;
  comparison: "lt";
}

export interface ModelReference {
  model_version: string | null;
  horizon_days: 1 | 2 | 3;
  contract_version: string;
  trained_through: string | null;
  calibration_version: string | null;
  assessment_reference: string | null;
}

export interface LatestReview {
  review_id: string;
  request_id: string;
  revision: number;
  forecast_id: string;
  action: ReviewAction;
  observed_label: boolean;
  comment: string | null;
  reviewed_at: string;
}

export type TrainingEligibility =
  | "no_review"
  | "waiting_target_maturity"
  | "requires_mature_revalidation"
  | "compatible_correction"
  | "confirmation_only"
  | "incompatible_source_model"
  | "incompatible_contract"
  | "insufficient_data"
  | "applied";

export interface ForecastReview {
  status: ReviewStatus;
  revision: number;
  review_open_at: string;
  reviewable: boolean;
  blocked_reason: "review_not_open" | null;
  latest_review: LatestReview | null;
  training_eligibility: TrainingEligibility;
  applied_review_references: string[];
}

export type EnsembleFamily = "logistic_regression" | "random_forest" | "hist_gradient_boosting_classifier";

export type AgreementCategory =
  | "alerta_por_unanimidad"
  | "posible_alerta_acuerdo_parcial"
  | "sin_alerta_por_mayoria_con_discrepancia"
  | "sin_alerta_por_unanimidad";

export interface EnsembleComponentVote {
  family: EnsembleFamily;
  model_reference: ModelReference;
  calibrated_through: string;
  score: number;
  decision_threshold: number;
  alert: boolean;
}

export interface EnsembleDetail {
  policy_version: string;
  ensemble_identity_sha256: string;
  weights: Record<EnsembleFamily, number>;
  components: EnsembleComponentVote[];
  combined_probability: number;
  combined_alert: boolean;
  positive_votes: number;
  agreement_category: AgreementCategory;
  calibrated_through: string;
}

export interface Forecast {
  forecast_id: string;
  sensor_id: string;
  batch_id: string;
  as_of_date: string;
  horizon_days: 1 | 2 | 3;
  target_date: string;
  contract_version: string;
  issued_at: string;
  snapshot_id: string;
  alert: boolean;
  score: number;
  score_kind: "raw_model_score" | "calibrated_probability" | "ensemble_mean_of_calibrated_components";
  display_probability: number | null;
  probability_status: "development_assessed" | "not_qualified";
  probability_reason_code: string | null;
  decision_threshold: number;
  event_threshold: EventThreshold;
  model_reference: ModelReference;
  review: ForecastReview;
  ensemble: EnsembleDetail | null;
}

const FAMILY_LABELS: Record<EnsembleFamily, string> = {
  logistic_regression: "Regresión logística",
  random_forest: "Bosque aleatorio",
  hist_gradient_boosting_classifier: "Boosting de gradiente",
};

export function familyLabel(family: EnsembleFamily): string {
  return FAMILY_LABELS[family];
}

/** El acuerdo es una dimensión distinta de la alerta combinada: cuántos de
 * los 3 modelos individuales coinciden, nunca una confianza ni una encuesta
 * que reemplace `combined_alert`. */
const AGREEMENT_LABELS: Record<AgreementCategory, string> = {
  alerta_por_unanimidad: "Los 3 modelos coinciden en la alerta",
  posible_alerta_acuerdo_parcial: "2 de 3 modelos indican alerta",
  sin_alerta_por_mayoria_con_discrepancia: "1 de 3 modelos indica alerta",
  sin_alerta_por_unanimidad: "Los 3 modelos coinciden en que no hay alerta",
}

export function agreementLabel(ensemble: EnsembleDetail): string {
  return AGREEMENT_LABELS[ensemble.agreement_category];
}

export function agreementVotesLabel(ensemble: EnsembleDetail): string {
  return `${ensemble.positive_votes} de ${ensemble.components.length} modelos indican alerta`;
}

export interface ForecastListFilters {
  targetFrom?: string;
  targetTo?: string;
  horizonDays?: 1 | 2 | 3;
  reviewStatus?: ReviewStatus;
  limit?: number;
  cursor?: string;
}

export interface ForecastListResult {
  items: Forecast[];
  next_cursor: string | null;
  pending_total: number;
  reviewable_pending_total: number;
}

/** Emisión o revisión inexistente para este sensor (404 con cuerpo v2). */
export class ForecastNotFoundError extends Error {
  constructor() {
    super("No se encontró ese pronóstico para este punto de medición.");
    this.name = "ForecastNotFoundError";
  }
}

/** La revisión todavía no está habilitada (apertura UTC no alcanzada). */
export class ReviewNotOpenError extends Error {
  reviewOpenAt: string | null;
  constructor(reviewOpenAt: string | null) {
    super("Todavía no se puede revisar este resultado.");
    this.name = "ReviewNotOpenError";
    this.reviewOpenAt = reviewOpenAt;
  }
}

/** Otra opinión ya avanzó la revisión: no se sobrescribe. */
export class RevisionConflictError extends Error {
  actualRevision: number | null;
  constructor(actualRevision: number | null) {
    super("Se registró otra opinión mientras completabas este formulario.");
    this.name = "RevisionConflictError";
    this.actualRevision = actualRevision;
  }
}

/** El mismo request_id ya se usó con un contenido distinto: no se reintenta
 * como si fuera el mismo envío. */
export class ReviewIdempotencyConflictError extends Error {
  constructor() {
    super("Este envío no coincide con un intento anterior con el mismo identificador.");
    this.name = "ReviewIdempotencyConflictError";
  }
}

/** Reserva permanente del espacio demo- (decisiones de dependencias v2). */
export class DemoWriteLockedError extends Error {
  constructor() {
    super("Este punto de medición pertenece a la demostración y no admite revisiones acá.");
    this.name = "DemoWriteLockedError";
  }
}

interface ErrorEnvelope {
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
}

async function readErrorEnvelope(response: Response): Promise<ErrorEnvelope | null> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    return null;
  }
  if (body && typeof body === "object" && "error" in body) {
    return (body as { error?: ErrorEnvelope }).error ?? null;
  }
  return null;
}

export class ForecastCursorExpiredError extends Error {
  constructor() { super("La lista cambió. Volvé a cargarla para seguir viendo resultados."); this.name = "ForecastCursorExpiredError"; }
}

function forecastsPath(sensorId: string): string {
  return `${API_BASE_URL}/api/v2/sensors/${encodeURIComponent(sensorId)}/forecasts`;
}

export async function listForecasts(
  sensorId: string,
  filters: ForecastListFilters = {},
): Promise<ForecastListResult> {
  const query = new URLSearchParams();
  if (filters.targetFrom) query.set("target_from", filters.targetFrom);
  if (filters.targetTo) query.set("target_to", filters.targetTo);
  if (filters.horizonDays) query.set("horizon_days", String(filters.horizonDays));
  if (filters.reviewStatus) query.set("review_status", filters.reviewStatus);
  if (filters.limit) query.set("limit", String(filters.limit));
  if (filters.cursor) query.set("cursor", filters.cursor);
  const qs = query.toString();
  const response = await fetch(`${forecastsPath(sensorId)}${qs ? `?${qs}` : ""}`);
  if (response.ok) return response.json();

  const error = await readErrorEnvelope(response);
  if (response.status === 404 && !error) throw new ProducerV2UnavailableError();
  if (error?.code === "invalid_cursor") throw new ForecastCursorExpiredError();
  if (error?.code === "invalid_date_range") throw new Error("La fecha inicial debe ser anterior o igual a la fecha final.");
  throw new Error("No se pudieron consultar los pronósticos. Intentá nuevamente.");
}

export async function getForecast(sensorId: string, forecastId: string): Promise<Forecast> {
  const response = await fetch(`${forecastsPath(sensorId)}/${encodeURIComponent(forecastId)}`);
  if (response.ok) return response.json();

  const error = await readErrorEnvelope(response);
  if (response.status === 404) {
    if (error?.code === "forecast_not_found") throw new ForecastNotFoundError();
    throw new ProducerV2UnavailableError();
  }
  throw new Error(error?.message ?? "No se pudo consultar este pronóstico. Intentá nuevamente.");
}

export interface ReviewRequest {
  requestId: string;
  expectedRevision: number;
  action: ReviewAction;
  comment: string | null;
}

export async function submitReview(
  sensorId: string,
  forecastId: string,
  request: ReviewRequest,
): Promise<ForecastReview> {
  const response = await fetch(`${forecastsPath(sensorId)}/${encodeURIComponent(forecastId)}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request_id: request.requestId,
      expected_revision: request.expectedRevision,
      action: request.action,
      comment: request.comment,
    }),
  });
  if (response.ok) return response.json();

  const error = await readErrorEnvelope(response);
  if (response.status === 404) {
    if (error?.code === "forecast_not_found") throw new ForecastNotFoundError();
    throw new ProducerV2UnavailableError();
  }
  if (response.status === 409) {
    if (error?.code === "review_not_open") {
      const reviewOpenAt = typeof error.details?.review_open_at === "string" ? error.details.review_open_at : null;
      throw new ReviewNotOpenError(reviewOpenAt);
    }
    if (error?.code === "revision_conflict") {
      const actualRevision =
        typeof error.details?.actual_revision === "number" ? error.details.actual_revision : null;
      throw new RevisionConflictError(actualRevision);
    }
    if (error?.code === "idempotency_conflict") throw new ReviewIdempotencyConflictError();
    if (error?.code === "demo_write_locked") throw new DemoWriteLockedError();
  }
  throw new Error(error?.message ?? "No se pudo guardar la revisión. Intentá nuevamente.");
}

export function newRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function displayForecastDate(value: string): string {
  return new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${value}T00:00:00Z`),
  );
}

export function displayIssuedAt(value: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));
}

const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: "Pendiente de revisar",
  confirmed: "Confirmado por vos",
  rejected: "Rechazado por vos",
};

export function reviewStatusLabel(status: ReviewStatus): string {
  return REVIEW_STATUS_LABELS[status];
}

/** El contrato prohíbe mostrar `score` como porcentaje: es una puntuación
 * interna del clasificador, no una probabilidad apta para publicarse.
 * `display_probability` es lo único que puede mostrarse como porcentaje, y
 * solo cuando el backend lo publica (gate de calibración aprobado). */
export function displayProbability(forecast: Forecast): string {
  if (forecast.display_probability === null) return "Probabilidad no disponible";
  return `${Math.round(forecast.display_probability * 100)} %`;
}

export type ForecastSlot = (Forecast & { status: "available" }) | { horizon_days: 1 | 2 | 3; target_date: string | null; status: "unavailable"; reason_code: string };
export interface ForecastBatch {
  batch_id: string | null; revision: number; as_of_date: string | null;
  data_age_days: number | null; server_today: string; slots: ForecastSlot[];
  provenance: "real" | "synthetic" | "external_reanalysis" | "mixed" | "unknown";
  calendar_timezone: "UTC";
}
export async function emitForecasts(sensorId: string, requestId: string): Promise<ForecastBatch> {
  const response = await fetch(forecastsPath(sensorId), {
    method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": requestId }, body: "{}",
  });
  if (response.ok) return response.json();
  const error = await readErrorEnvelope(response);
  const messages: Record<string, string> = {
    issued_snapshot_conflict: "Las mediciones de ese día cambiaron. Conservamos el pronóstico anterior; hace falta revisar los datos.",
    demo_write_locked: "Este punto pertenece a la demostración anterior y no permite generar pronósticos aquí.",
    future_readings: "Hay mediciones con fechas futuras. Revisá sus fechas antes de continuar.",
    invalid_calendar: "Hay fechas de medición inconsistentes. Es necesario revisarlas.",
    sensor_not_found: "Este punto de medición ya no está disponible.",
  };
  if (response.status === 404 && !error) throw new ProducerV2UnavailableError();
  throw new Error(messages[error?.code ?? ""] ?? "No pudimos recuperar el resultado. Reintentá para consultar el mismo pedido.");
}

export interface AlertOutlookSummary {
  alert: boolean;
  /** Fechas con alerta, ya formateadas ("lunes 28" style), en orden. Vacío
   * cuando `alert` es false. */
  days: string[];
}

/** Resumen de la parte superior de "Mi cultivo": nunca recalcula
 * `combined_alert`, solo agrupa los `alert: true` ya decididos por el
 * backend en cada horizonte disponible. `null` cuando no hay ningún
 * horizonte disponible (para mostrar el aviso de información insuficiente
 * en su lugar, nunca "sin alerta"). */
export function alertOutlookSummary(batch: ForecastBatch): AlertOutlookSummary | null {
  const available = batch.slots.filter((slot) => slot.status === "available") as (Forecast & { status: "available" })[];
  if (available.length === 0) return null;
  const alerted = available.filter((slot) => slot.alert);
  return {
    alert: alerted.length > 0,
    days: alerted.map((slot) => displayForecastDate(slot.target_date)),
  };
}
