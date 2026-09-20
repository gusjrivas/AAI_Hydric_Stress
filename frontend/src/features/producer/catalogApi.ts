import { API_BASE_URL } from "../../api/baseUrl";

export interface Sector {
  sector_id: string;
  display_name: string;
  crop: string | null;
  primary_sensor_id: string | null;
  revision: number;
  created_at: string;
}

export interface SensorSummary {
  sensor_id: string;
  display_name: string;
  sector_id: string | null;
  source_kind: "real" | "synthetic" | "unknown";
  revision: number;
  created_at: string | null;
  registered: boolean;
}

/** La fachada v2 no está disponible en este backend (`PRODUCER_V2_ENABLED`
 * desactivado o ruta inexistente): FastAPI responde 404 plano, sin el cuerpo
 * `{error:{code,...}}` del contrato v2. Se distingue de un 404 de recurso
 * desconocido, que sí trae ese cuerpo. */
export class ProducerV2UnavailableError extends Error {
  constructor() {
    super("El catálogo de sectores y sensores todavía no está disponible en este servidor.");
    this.name = "ProducerV2UnavailableError";
  }
}

async function getV2<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api/v2${path}`);
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
  if (response.status === 404 && !errorCode) {
    throw new ProducerV2UnavailableError();
  }
  throw new Error(errorCode?.message ?? "No se pudo consultar el catálogo. Intentá nuevamente.");
}

export interface SectorListResult {
  items: Sector[];
  next_cursor: string | null;
}

export interface SensorListResult {
  items: SensorSummary[];
  next_cursor: string | null;
}

export async function listSectors(): Promise<SectorListResult> {
  return getV2<SectorListResult>("/sectors");
}

export async function listSensors(sectorId?: string): Promise<SensorListResult> {
  const query = sectorId ? `?sector_id=${encodeURIComponent(sectorId)}` : "";
  return getV2<SensorListResult>(`/sensors${query}`);
}
