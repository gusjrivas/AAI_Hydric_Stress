import { DEMO_CONTROL_BASE_URL } from "../../api/demoControlUrl";

export function isDemoControlConfigured(): boolean {
  return DEMO_CONTROL_BASE_URL !== null;
}

export type DemoSessionStatus =
  | "prepared"
  | "running"
  | "pausing"
  | "paused"
  | "blocked"
  | "completed";

export type DemoStepPhase =
  | "pending"
  | "ingest_pending"
  | "ingested"
  | "forecast_pending"
  | "completed";

// Espejo de `scripts.demo_simulation.control.public_view` (entrega 2,
// PR #203): sin rutas locales ni detalles internos del manifiesto.
export interface DemoSessionView {
  session_id: string;
  sensor_id: string;
  status: DemoSessionStatus;
  phase: DemoStepPhase;
  cursor: number;
  days: number;
  simulated_date: string | null;
  last_ingested_date: string | null;
  last_forecast_date: string | null;
  interval_seconds: number;
  revision: number;
  error: string | null;
}

export class DemoControlError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "DemoControlError";
    this.status = status;
  }
}

function requireBaseUrl(): string {
  if (DEMO_CONTROL_BASE_URL === null) {
    throw new DemoControlError(0, "El controlador de demostración no está configurado.");
  }
  return DEMO_CONTROL_BASE_URL;
}

async function readDemoError(response: Response, fallback: string): Promise<never> {
  const body = await response.json().catch(() => null);
  throw new DemoControlError(response.status, body?.error ?? fallback);
}

/** Puramente de lectura (contrato de `GET /demo/session`): nunca crea,
 * inicia ni avanza nada. `null` significa "no hay sesión preparada",
 * distinto de un error de conexión (que se propaga como excepción). */
export async function getDemoSession(): Promise<DemoSessionView | null> {
  const base = requireBaseUrl();
  const response = await fetch(`${base}/demo/session`);
  if (response.status === 404) return null;
  if (!response.ok) {
    return readDemoError(response, `Error al consultar la demostración: ${response.status}`);
  }
  return response.json();
}

export interface DemoControlOrder {
  session_id: string;
  expected_revision: number;
  request_id: string;
}

async function postDemoCommand(path: string, order: DemoControlOrder): Promise<DemoSessionView> {
  const base = requireBaseUrl();
  const response = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(order),
  });
  if (!response.ok) {
    return readDemoError(response, `Error al enviar la orden: ${response.status}`);
  }
  return response.json();
}

export function startDemo(order: DemoControlOrder): Promise<DemoSessionView> {
  return postDemoCommand("/demo/session/start", order);
}

export function pauseDemo(order: DemoControlOrder): Promise<DemoSessionView> {
  return postDemoCommand("/demo/session/pause", order);
}

export function resumeDemo(order: DemoControlOrder): Promise<DemoSessionView> {
  return postDemoCommand("/demo/session/resume", order);
}

export function newRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
