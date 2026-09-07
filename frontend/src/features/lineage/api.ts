import { API_BASE_URL } from "../../api/baseUrl";

export interface FeedbackReference {
  sensor_id: string;
  fecha: string;
  model_version: string;
  target_timestamp: string;
}

export interface LineageEntry {
  recalibration_id: string;
  source_model_id: string;
  successor_model_id: string;
  feedback_references: FeedbackReference[];
  recalibrated_at: string;
  source_trained_through: string;
  successor_trained_through: string;
  lineage_version: number;
  dataset_sha256: string | null;
  mlflow_model_version: string | null;
}

export interface LineageResponse {
  sensor_id: string;
  chain: LineageEntry[];
}

/** Un linaje corrupto o incompleto (`LineageValidationError` en el
 * backend) responde 409 y se propaga como excepción explícita — nunca
 * se degrada a cadena vacía.
 */
export async function getLineage(sensorId: string): Promise<LineageResponse> {
  const response = await fetch(`${API_BASE_URL}/lineage/${encodeURIComponent(sensorId)}`);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Error al obtener el linaje: ${response.status}`);
  }
  return response.json();
}
