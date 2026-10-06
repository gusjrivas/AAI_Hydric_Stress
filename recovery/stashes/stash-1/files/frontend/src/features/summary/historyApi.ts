import { API_BASE_URL } from "../../api/baseUrl";

export interface Measurement {
  fecha: string;
  soil_moisture: number | null;
  temperature: number | null;
  precipitation: number | null;
  origen: string;
}

export interface MeasurementHistory {
  sensor_id: string;
  period_start: string | null;
  period_end: string | null;
  rows: Measurement[];
}

export async function getMeasurementHistory(sensorId: string, days: number): Promise<MeasurementHistory | null> {
  const response = await fetch(`${API_BASE_URL}/sensors/${encodeURIComponent(sensorId)}/history?days=${days}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("No se pudieron cargar las mediciones. Intentá nuevamente.");
  return response.json();
}

export function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(`${value}T00:00:00Z`));
}
