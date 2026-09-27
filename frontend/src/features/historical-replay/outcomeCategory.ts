import type { ReplayLabelRule } from "./api";

/**
 * Categoría explicativa del resultado (sección "Comparación explicativa" de
 * la entrega "recorrido guiado"). Se deriva únicamente de `y_pred` e
 * `y_true`, ambos ya archivados — nunca recalcula ni redondea la
 * observación (`y_true` se conserva como referencia archivada, no se
 * reclasifica a partir del valor crudo).
 *
 * Las cuatro categorías, en el vocabulario del encargo:
 * - Alerta correcta: predicción positiva y clase observada positiva.
 * - Falsa alerta: predicción positiva y clase observada negativa.
 * - Omisión de alerta: predicción negativa y clase observada positiva.
 * - Ausencia de alerta correcta: ambas clases negativas.
 */
export type OutcomeCategory =
  | "alerta_correcta"
  | "falsa_alerta"
  | "omision_alerta"
  | "ausencia_correcta";

export const OUTCOME_CATEGORY_LABEL: Record<OutcomeCategory, string> = {
  alerta_correcta: "Alerta correcta",
  falsa_alerta: "Falsa alerta",
  omision_alerta: "Omisión de alerta",
  ausencia_correcta: "Ausencia de alerta correcta",
};

export function outcomeCategory(yPred: 0 | 1, yTrue: 0 | 1): OutcomeCategory {
  if (yPred === 1 && yTrue === 1) return "alerta_correcta";
  if (yPred === 1 && yTrue === 0) return "falsa_alerta";
  if (yPred === 0 && yTrue === 1) return "omision_alerta";
  return "ausencia_correcta";
}

/**
 * Distancia con signo de la observación al umbral físico de humedad, en la
 * misma unidad del umbral (m³/m³ en el candidato verificado). Nunca se
 * llama "error del modelo": no existe una predicción numérica de humedad
 * con la que compararla, solo una clase binaria (Paso "predicción
 * explicada" §E). Se calcula solo cuando hay una medición válida revelada
 * (`valor` no nulo) — nunca sobre un estado `imputada`/`no_determinado`/
 * `sin_dato_en_fuente` sin valor.
 */
export function distanceToThreshold(
  observedValue: number,
  rule: Pick<ReplayLabelRule, "umbral" | "unidad">,
): { value: number; unit: string; relation: "por_debajo" | "por_encima" | "igual" } {
  const value = observedValue - rule.umbral;
  const relation = value < 0 ? "por_debajo" : value > 0 ? "por_encima" : "igual";
  return { value, unit: rule.unidad, relation };
}

export function formatDistanceToThreshold(distance: {
  value: number;
  unit: string;
  relation: "por_debajo" | "por_encima" | "igual";
}): string {
  const magnitude = Math.abs(distance.value).toFixed(3);
  const relationText =
    distance.relation === "por_debajo"
      ? "por debajo del umbral"
      : distance.relation === "por_encima"
        ? "por encima del umbral"
        : "exactamente en el umbral";
  return `${distance.value >= 0 ? "+" : "-"}${magnitude} ${distance.unit} (${relationText})`;
}
