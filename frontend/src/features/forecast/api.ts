import { API_BASE_URL } from "../../api/baseUrl";

export class HttpError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}

async function readDetail(response: Response, fallback: string): Promise<never> {
  const body = await response.json().catch(() => null);
  throw new HttpError(response.status, body?.detail ?? fallback);
}

export interface Verdict {
  fecha: string;
  alerta: boolean;
  probabilidad: number;
  fecha_objetivo?: string;
}

export interface ForecastRunResponse {
  verdicts: Verdict[];
  train_rows: number;
  test_rows: number;
  selection_warning?: string | null;
}

export interface FeedbackRow {
  fecha: string;
  alerta_generada: number;
  estado_validacion: string;
  etiqueta_corregida: number | null;
  observacion: string | null;
  y_proba?: number | null;
  fecha_objetivo?: string | null;
}

export interface FeedbackListResponse {
  rows: FeedbackRow[];
}

export async function runForecast(sensorId: string): Promise<ForecastRunResponse> {
  const response = await fetch(`${API_BASE_URL}/forecast/${encodeURIComponent(sensorId)}/run`, { method: "POST" });
  if (!response.ok) {
    return readDetail(response, `Error al correr el pronóstico: ${response.status}`);
  }
  return response.json();
}

export async function listFeedback(sensorId: string): Promise<FeedbackListResponse> {
  const response = await fetch(`${API_BASE_URL}/feedback/${encodeURIComponent(sensorId)}`);
  if (!response.ok) {
    return readDetail(response, `Error al obtener el feedback: ${response.status}`);
  }
  return response.json();
}

export async function confirmAlert(sensorId: string, fecha: string): Promise<FeedbackRow> {
  const response = await fetch(`${API_BASE_URL}/feedback/${encodeURIComponent(sensorId)}/${fecha}/confirm`, { method: "POST" });
  if (!response.ok) {
    return readDetail(response, `Error al confirmar la alerta: ${response.status}`);
  }
  return response.json();
}

export async function rejectAlert(
  sensorId: string,
  fecha: string,
  etiquetaCorregida: number,
  observacion: string,
): Promise<FeedbackRow> {
  const response = await fetch(`${API_BASE_URL}/feedback/${encodeURIComponent(sensorId)}/${fecha}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ etiqueta_corregida: etiquetaCorregida, observacion }),
  });
  if (!response.ok) {
    return readDetail(response, `Error al rechazar la alerta: ${response.status}`);
  }
  return response.json();
}

export interface RecalibrationResponse {
  version: string;
  n_correcciones: number;
  fechas_corregidas: string[];
  recalibration_id?: string | null;
}

export async function recalibrate(sensorId: string): Promise<RecalibrationResponse> {
  const response = await fetch(`${API_BASE_URL}/recalibrate/${encodeURIComponent(sensorId)}`, { method: "POST" });
  if (!response.ok) {
    return readDetail(response, `Error al recalibrar el modelo: ${response.status}`);
  }
  return response.json();
}

export interface ActivePredictor {
  sensor_id: string;
  origin: "recalibrado" | "base_configurado" | null;
  model_id: string | null;
  version: string | null;
  trained_through: string | null;
  calibration_end: string | null;
  horizon_days: number;
  contract_version: number;
  pipeline_version: string;
  feature_columns: string[];
  lags: number[];
  rolling_windows: number[];
  applied_feedback_count: number;
  applied_feedback_dates: string[];
}

export async function getActivePredictor(sensorId: string): Promise<ActivePredictor> {
  const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(sensorId)}/active`);
  if (!response.ok) {
    return readDetail(response, `Error al obtener el predictor activo: ${response.status}`);
  }
  return response.json();
}
