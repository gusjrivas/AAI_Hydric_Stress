import { API_BASE_URL } from "../../api/baseUrl";
import type { LabReadingValues } from "./readingGenerator";

export interface LabIngestResult {
  timestamp: string;
  filas_totales: number;
}

/** Ingesta una lectura sintética del laboratorio contra el endpoint real
 * de ingesta (`POST /sensors/{sensor_id}/readings`, ADR-0007/0008) --
 * nunca un almacenamiento paralelo propio del laboratorio. `procedencia`
 * queda fija en "sintetico": nunca se declara "real" una lectura
 * generada por este módulo. */
export async function ingestLabReading(
  sensorId: string,
  isoDate: string,
  values: LabReadingValues,
): Promise<LabIngestResult> {
  const response = await fetch(`${API_BASE_URL}/sensors/${encodeURIComponent(sensorId)}/readings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      timestamp: `${isoDate}T00:00:00Z`,
      soil_moisture: values.soil_moisture,
      temperature: values.temperature,
      relative_humidity: values.relative_humidity,
      precipitation: values.precipitation,
      solar_radiation: values.solar_radiation,
      wind_speed: values.wind_speed,
      procedencia: "sintetico",
    }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Error al ingerir una lectura sintética: ${response.status}`);
  }
  return response.json();
}
