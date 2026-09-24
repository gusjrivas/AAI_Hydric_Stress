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
