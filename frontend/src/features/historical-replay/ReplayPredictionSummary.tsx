import type { ReplayLabelRule } from "./api";

interface Props {
  targetDate: string;
  horizonDays: number;
  yPred: 0 | 1;
  rule: ReplayLabelRule;
}

/**
 * Predicción explicada en palabras (Paso "recorrido guiado" §D). Nunca dice
 * "Ejecutar arquitectura" ni "Entrenar": este recorrido consulta una
 * predicción ya archivada, no dispara una inferencia nueva.
 */
export function ReplayPredictionSummary({ targetDate, horizonDays, yPred, rule }: Props) {
  const anticipated =
    yPred === 1
      ? `Para el ${targetDate}, se anticipó humedad por debajo del umbral.`
      : `Para el ${targetDate}, no se anticipó humedad por debajo del umbral.`;

  return (
    <div className="hr-prediction-summary">
      <p className="hr-archived-badge" role="note">
        Predicción archivada · horizonte +{horizonDays} días
      </p>
      <p className="hr-prediction-sentence">{anticipated}</p>
      <p className="hr-prediction-rule-note">
        Umbral verificado: {rule.umbral.toFixed(3)} {rule.unidad} de {rule.variable}.
      </p>
    </div>
  );
}
