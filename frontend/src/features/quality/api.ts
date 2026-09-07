import { API_BASE_URL } from "../../api/baseUrl";

export interface QualityReport {
  sensor_id: string;
  total_rows: number;
  period_start: string | null;
  period_end: string | null;
  missing_pct: Record<string, number>;
  duplicate_timestamps: string[];
  out_of_range: Record<string, string[]>;
  anomalies_detected: number;
  anomaly_method: string;
  anomaly_contamination: number;
  anomaly_columns: string[];
  is_diagnostic_only: boolean;
  note: string;
}

/** `null` cuando el sensor todavía no tiene dataset ingerido (404) — un
 * estado vacío legítimo, no un error. Cualquier otra respuesta no-ok
 * lanza una excepción con el detalle del backend.
 */
export async function getQualityReport(sensorId: string): Promise<QualityReport | null> {
  const response = await fetch(`${API_BASE_URL}/quality/${encodeURIComponent(sensorId)}`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Error al obtener la calidad de datos: ${response.status}`);
  }
  return response.json();
}
