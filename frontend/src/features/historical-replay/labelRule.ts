import type { ReplayLabelRule } from "./api";

/**
 * Texto de la clase proxy a partir de la regla verificada (Paso 4.1 §3):
 * nunca "Estrés / Sin estrés" (lenguaje de diagnóstico), y nunca invertido
 * ni inventado — se deriva del operador exacto documentado en el
 * manifiesto (`less_than`, la única regla admitida hasta hoy).
 */
export function classLabel(value: 0 | 1, rule: ReplayLabelRule): string {
  const below = `Por debajo del umbral de humedad (${value})`;
  const notBelow = `No inferior al umbral de humedad (${value})`;
  if (rule.operador === "less_than") {
    return value === 1 ? below : notBelow;
  }
  return `Clase ${value}`;
}

export function ruleDescription(rule: ReplayLabelRule): string {
  return (
    `Proxy: ${rule.variable} observada en el horizonte por debajo de ` +
    `${rule.umbral.toFixed(3)} ${rule.unidad}` +
    (rule.percentil != null ? ` (percentil ${rule.percentil} del período de entrenamiento)` : "") +
    "."
  );
}
