import type { FeedbackRow } from "../forecast/api";
import type { DemoSessionView } from "./api";

/**
 * Restricción de la UI sobre mutaciones manuales del sensor de demo
 * (tasks 3.3-3.4; requerimiento "Revisión humana posterior a la
 * reproducción"). Nunca sustituye la autoridad del backend: solo decide
 * qué botones ofrecer, los rechazos reales (409, procedencia, maduración)
 * siguen viniendo de la API.
 */
export interface DemoWriteGate {
  /** true mientras la sesión no está `completed`: bloquea pronóstico
   * manual, confirmar/corregir y aplicar observaciones por completo. */
  locked: boolean;
  lockedReason: string;
  /** Con la sesión ya completada, solo habilita confirmar/corregir para
   * filas cuya fecha objetivo ya está en el período ingerido y terminó
   * en UTC real. Con la sesión en curso, siempre devuelve false. */
  isRowReviewable: (row: FeedbackRow) => boolean;
  rowUnavailableReason: (row: FeedbackRow) => string;
}

const LOCKED_REASON =
  "Esta sesión de demostración está en curso. Los ajustes manuales de este sensor se habilitan al completarse.";

const NO_TARGET_REASON =
  "Todavía no hay una observación disponible para esta fecha objetivo.";

function todayUtcDateString(): string {
  return new Date().toISOString().slice(0, 10);
}

export function computeDemoWriteGate(session: DemoSessionView): DemoWriteGate {
  const locked = session.status !== "completed";

  function isRowReviewable(row: FeedbackRow): boolean {
    if (locked) return false;
    if (!row.fecha_objetivo) return false;
    if (row.fecha_objetivo >= todayUtcDateString()) return false;
    if (!session.last_ingested_date) return false;
    return row.fecha_objetivo <= session.last_ingested_date;
  }

  return {
    locked,
    lockedReason: LOCKED_REASON,
    isRowReviewable,
    rowUnavailableReason: (_row) => (locked ? LOCKED_REASON : NO_TARGET_REASON),
  };
}

/** `activeSensorId` es el sensor que la persona está mirando; `session`
 * es el estado vigente del controlador (o `null` si no hay uno
 * configurado/preparado). Devuelve `undefined` cuando no aplica ninguna
 * restricción de demo a ese sensor. */
export function demoGateForSensor(
  session: DemoSessionView | null,
  activeSensorId: string,
): DemoWriteGate | undefined {
  if (session === null || session.sensor_id !== activeSensorId) return undefined;
  return computeDemoWriteGate(session);
}
