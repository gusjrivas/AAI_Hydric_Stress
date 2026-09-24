// Utilidades mínimas de fecha ISO (YYYY-MM-DD), sin zona horaria — el
// backend ya trabaja en "día UTC ingenuo" (day_convention), y estas
// funciones solo hacen aritmética de calendario sobre ese mismo supuesto,
// nunca timestamps de recepción inventados.

export function addDaysIso(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function compareIso(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function clampIso(value: string, min: string, max: string): string {
  if (compareIso(value, min) < 0) return min;
  if (compareIso(value, max) > 0) return max;
  return value;
}

/** Diferencia real en días de calendario entre dos fechas ISO (`b - a`),
 * usada para ubicar puntos en una escala temporal real (no por índice de
 * fila) — dos fechas consecutivas en la lista de filas pueden estar a más
 * de un día de distancia si el backend no reporta un día ausente por
 * completo (Paso "gráfico integrado" §C). */
export function daysBetweenIso(a: string, b: string): number {
  const [ay, am, ad] = a.split("-").map(Number);
  const [by, bm, bd] = b.split("-").map(Number);
  const start = Date.UTC(ay, am - 1, ad);
  const end = Date.UTC(by, bm - 1, bd);
  return Math.round((end - start) / 86_400_000);
}

/** Lista de fechas ISO desde `startIso` hasta `endIso` (ambos incluidos),
 * un día de calendario por entrada, incluidos los días para los que el
 * backend no reportó ninguna fila (ausentes, no solo nulos). */
export function isoDayRange(startIso: string, endIso: string): string[] {
  const total = daysBetweenIso(startIso, endIso);
  if (total < 0) return [];
  const out: string[] = [];
  for (let i = 0; i <= total; i += 1) {
    out.push(addDaysIso(startIso, i));
  }
  return out;
}
