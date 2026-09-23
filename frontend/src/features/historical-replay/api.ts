import { API_BASE_URL } from "../../api/baseUrl";

export interface ReplayDisclaimers {
  reproduccion_retrospectiva: boolean;
  proxy_estadistico_relativo: boolean;
  utilidad_agronomica_demostrada: boolean;
}

export interface ReplayEvidenceCard {
  package_id: string;
  dataset_name: string;
  commit_sha: string;
  split_date: string;
  // Corte de partición train/test; NO necesariamente la última fecha
  // realmente usada para entrenar — ver `training_max_date` (Paso 4.1 §3).
  training_max_date: string;
  day_convention: string;
  issuance_assumption: string;
}

export interface ReplayLabelRule {
  variable: string;
  unidad: string;
  operador: "less_than";
  umbral: number;
  percentil: number | null;
}

export interface ReplayCandidateInfo {
  experiment_id: string;
  run_id: string;
  config_name: string;
  seed: number;
  horizon_days: number;
  periodo_inicio: string;
  periodo_fin: string;
  disclaimers: ReplayDisclaimers;
  limitaciones: string[];
  evidencia: ReplayEvidenceCard;
  regla_etiqueta: ReplayLabelRule;
}

export interface ReplayOriginsResponse {
  origins: { timestamp_origen: string }[];
}

export interface MedicionOriginal {
  estado: "medida" | "imputada" | "no_determinado" | "sin_dato_en_fuente";
  valor: number | null;
}

export interface ReplayPredictionResponse {
  timestamp_origen: string;
  target_timestamp: string;
  experiment_id: string;
  run_id: string;
  config_name: string;
  seed: number;
  horizon_days: number;
  disclaimers: ReplayDisclaimers;
  y_pred: number;
  target_observed?: boolean;
  y_true?: number;
  coincide?: boolean;
  medicion_original?: MedicionOriginal;
}

export interface ReplayHistoryRow {
  fecha: string;
  soil_moisture: number | null;
}

export interface ReplayHistoryResponse {
  simulated_date: string;
  rows: ReplayHistoryRow[];
}

export type EstadoValidacion = "confirmada" | "rechazada";

export interface ReplayFeedbackEntry {
  timestamp_origen: string;
  estado_validacion: EstadoValidacion;
  etiqueta_corregida: 0 | 1 | null;
  observacion: string | null;
  registered_at: string;
  simulated_at: string;
}

export interface ReplayFeedbackListResponse {
  timestamp_origen: string;
  feedback: ReplayFeedbackEntry[];
}

export class ReplayNotFoundError extends Error {}
export class ReplayNotYetRevealedError extends Error {}
export class ReplayApiError extends Error {}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? `Error de la API de reproducción histórica: ${response.status}`;
    if (response.status === 404) throw new ReplayNotFoundError(message);
    if (response.status === 409) throw new ReplayNotYetRevealedError(message);
    throw new ReplayApiError(message);
  }
  return response.json();
}

export function getCandidate(): Promise<ReplayCandidateInfo> {
  return requestJson("/replay/candidate");
}

export function listOrigins(): Promise<ReplayOriginsResponse> {
  return requestJson("/replay/predictions");
}

export function getPrediction(
  timestampOrigen: string,
  simulatedDate: string,
): Promise<ReplayPredictionResponse> {
  const params = new URLSearchParams({ simulated_date: simulatedDate });
  return requestJson(`/replay/predictions/${encodeURIComponent(timestampOrigen)}?${params}`);
}

export function getHistory(simulatedDate: string): Promise<ReplayHistoryResponse> {
  const params = new URLSearchParams({ simulated_date: simulatedDate });
  return requestJson(`/replay/history?${params}`);
}

export function getFeedback(
  timestampOrigen: string,
  simulatedDate: string,
): Promise<ReplayFeedbackListResponse> {
  const params = new URLSearchParams({ simulated_date: simulatedDate });
  return requestJson(`/replay/predictions/${encodeURIComponent(timestampOrigen)}/feedback?${params}`);
}

export function createFeedback(
  timestampOrigen: string,
  body: {
    simulated_date: string;
    estado_validacion: EstadoValidacion;
    etiqueta_corregida?: 0 | 1 | null;
    observacion?: string | null;
  },
): Promise<ReplayFeedbackEntry> {
  return requestJson(`/replay/predictions/${encodeURIComponent(timestampOrigen)}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
