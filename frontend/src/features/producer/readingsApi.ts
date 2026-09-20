import { API_BASE_URL } from "../../api/baseUrl";
import { ProducerV2UnavailableError } from "./catalogApi";

export type ReadingVariable =
  | "soil_moisture"
  | "relative_humidity"
  | "solar_radiation"
  | "temperature"
  | "precipitation"
  | "wind_speed"
  | "et0";

export const READING_VARIABLES: ReadingVariable[] = [
  "soil_moisture",
  "temperature",
  "precipitation",
  "relative_humidity",
  "solar_radiation",
  "wind_speed",
  "et0",
];

export interface ReadingRow {
  date: string;
  soil_moisture: number | null;
  relative_humidity: number | null;
  solar_radiation: number | null;
  temperature: number | null;
  precipitation: number | null;
  wind_speed: number | null;
  et0: number | null;
  origin: "real" | "synthetic" | "unknown";
  quality_flags: string[];
}

export interface VariableCoverage {
  variable: string;
  observed_days: number;
  missing_days: number;
}

export interface ReadingsResult {
  sensor_id: string;
  calendar_timezone: "UTC";
  server_today: string;
  snapshot_id: string | null;
  window: { start_date: string; end_date: string; expected_days: number };
  status: "ready" | "no_readings";
  rows: ReadingRow[];
  missing_dates: string[];
  variable_coverage: VariableCoverage[];
  units: Record<string, string>;
  last_reading_date: string | null;
  data_age_days: number | null;
  provenance: "real" | "synthetic" | "mixed" | "unknown";
}

/** Un sensor desconocido (404 con cuerpo de error v2). */
export class SensorNotFoundError extends Error {
  constructor(sensorId: string) {
    super(`No se encontró el punto de medición «${sensorId}».`);
    this.name = "SensorNotFoundError";
  }
}

export async function getSensorReadings(sensorId: string, days: number): Promise<ReadingsResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/v2/sensors/${encodeURIComponent(sensorId)}/readings?days=${days}`,
  );
  if (response.ok) return response.json();

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  const errorCode =
    body && typeof body === "object" && "error" in body
      ? (body as { error?: { code?: string; message?: string } }).error
      : null;

  if (response.status === 404) {
    if (errorCode) throw new SensorNotFoundError(sensorId);
    throw new ProducerV2UnavailableError();
  }
  throw new Error(errorCode?.message ?? "No se pudieron cargar las mediciones. Intentá nuevamente.");
}

export function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(`${value}T00:00:00Z`));
}

const PROVENANCE_LABELS: Record<ReadingsResult["provenance"], string> = {
  real: "Datos registrados de la fuente",
  synthetic: "Datos simulados · Solo para demostración",
  mixed: "Fuentes reales y simuladas combinadas",
  unknown: "Procedencia no identificada",
};

export function provenanceLabel(provenance: ReadingsResult["provenance"]): string {
  return PROVENANCE_LABELS[provenance];
}

const ORIGIN_LABELS: Record<ReadingRow["origin"], string> = {
  real: "Fuente real",
  synthetic: "Simulado",
  unknown: "No identificado",
};

export function originLabel(origin: ReadingRow["origin"]): string {
  return ORIGIN_LABELS[origin];
}

// El backend expone unidades como códigos estables en inglés (contrato v2,
// api-contract.md), no pensados para mostrarse tal cual a un productor sin
// conocimientos técnicos (bug detectado al verificar contra el backend v2
// real: se veían literalmente "degC"/"mm/day"). Traducción de presentación
// only; si aparece una unidad nueva no mapeada, se muestra el código crudo
// del backend antes que ocultar la unidad.
const UNIT_DISPLAY_LABELS: Record<string, string> = {
  "degC": "°C",
  "mm/day": "mm",
  "MJ/m2/day": "MJ/m²/día",
  "m/s": "m/s",
  "%": "%",
};

function displayUnit(unit: string | undefined): string {
  if (!unit) return "";
  return UNIT_DISPLAY_LABELS[unit] ?? unit;
}

export function formatReadingValue(variable: ReadingVariable, value: number | null, unit: string | undefined): string {
  if (value === null) return "Sin medición";
  if (variable === "soil_moisture") return `${(value * 100).toFixed(1)} %`;
  const suffix = displayUnit(unit);
  return suffix ? `${value.toFixed(1)} ${suffix}` : value.toFixed(1);
}
