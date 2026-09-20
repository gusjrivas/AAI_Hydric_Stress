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
  score_kind: "raw_model_score" | "calibrated_probability";
  display_probability: number | null;
  probability_status: "development_assessed" | "not_qualified";
  probability_reason_code: string | null;
  decision_threshold: number;
  event_threshold: EventThreshold;
  model_reference: ModelReference;
  review: ForecastReview;
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
  throw new Error(error?.message ?? "No se pudieron consultar los pronósticos. Intentá nuevamente.");
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
