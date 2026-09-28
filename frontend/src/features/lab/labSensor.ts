/** Identidad y calendario del sensor de laboratorio (aislamiento por
 * `sensor_id`, ADR-0008): cada sesión usa un `sensor_id` propio con
 * prefijo `lab-`, exclusivo del laboratorio y nunca reutilizado por
 * Pergamino (`pergamino-ensemble-demo`), Melchor Romero
 * (`melchor-romero-demo`), la demo acelerada (`demo-*`) ni el dataset
 * histórico de evidencia (`melchor_romero_2024_consolidado`, sin prefijo
 * `sensor__`). Reiniciar el laboratorio genera un `sensor_id` nuevo: la
 * sesión anterior queda huérfana (nunca se reutiliza ni se mezcla), sin
 * necesidad de una operación de borrado.
 */

const SENSOR_ID_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;

export function makeLabSensorId(): string {
  const random =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 10)
      : `${Date.now().toString(16)}${Math.floor(Math.random() * 1e6).toString(16)}`;
  const id = `lab-${random}`;
  if (!SENSOR_ID_PATTERN.test(id)) {
    throw new Error(`Identificador de sensor de laboratorio inválido: ${id}`);
  }
  return id;
}

export function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDaysUtc(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return toIsoDate(date);
}

/** El día real de ayer (UTC). */
export function yesterdayUtc(): string {
  return addDaysUtc(toIsoDate(new Date()), -1);
}

/** Desplazamiento (días reales, UTC) del último día del backfill inicial
 * respecto de hoy: `LAB_HORIZON_DAYS` (3, igual que `HORIZON_DAYS` del
 * backend) más un margen de 3 días. Con este desplazamiento, el primer
 * pronóstico del laboratorio (Escenario A) tiene fecha objetivo
 * `backfillEndDate + 3` ya vencida (`< hoy`), así que la revisión humana
 * queda habilitada de verdad por el backend real desde el primer paso --
 * nunca fabricada del lado del cliente. Confirmado con una verificación
 * HTTP real contra el backend antes de fijar este valor (ver
 * `docs/design/`).
 */
export const LAB_BACKFILL_END_OFFSET_DAYS = 6;

/** Último día del backfill inicial (UTC): lo bastante en el pasado para
 * que el pronóstico emitido sobre él ya tenga una fecha objetivo vencida
 * (revisable de verdad), pero cerca de "hoy" para que el recorrido de
 * escenarios B→C→D siga siendo una demostración de un sensor en vivo, no
 * un recorrido histórico (eso ya lo cubren Pergamino/Melchor Romero). */
export function labBackfillEndDateUtc(): string {
  return addDaysUtc(toIsoDate(new Date()), -LAB_BACKFILL_END_OFFSET_DAYS);
}
