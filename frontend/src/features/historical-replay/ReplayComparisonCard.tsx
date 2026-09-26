import type { MedicionOriginal, ReplayLabelRule } from "./api";
import { classLabel } from "./labelRule";
import {
  OUTCOME_CATEGORY_LABEL,
  distanceToThreshold,
  formatDistanceToThreshold,
  outcomeCategory,
} from "./outcomeCategory";

interface Props {
  yPred: 0 | 1;
  yTrue: 0 | 1;
  rule: ReplayLabelRule;
  medicionOriginal: MedicionOriginal | null;
}

/**
 * Comparación explicativa (Paso "recorrido guiado" §E), mostrada solo tras
 * revelar la observación. `y_true` se conserva tal cual llega archivado — no
 * se recalcula a partir del valor crudo redondeado. La distancia al umbral
 * es una magnitud física (humedad observada − umbral), nunca "error del
 * modelo": no existe una predicción numérica de humedad con la que
 * compararla.
 */
export function ReplayComparisonCard({ yPred, yTrue, rule, medicionOriginal }: Props) {
  const category = outcomeCategory(yPred, yTrue);
  const hasValidMeasurement =
    medicionOriginal !== null &&
    medicionOriginal.estado === "medida" &&
    medicionOriginal.valor !== null;
  const distance = hasValidMeasurement
    ? distanceToThreshold(medicionOriginal!.valor as number, rule)
    : null;

  return (
    <div className="hr-comparison" data-category={category}>
      <dl>
        <div>
          <dt>Qué anticipó el modelo</dt>
          <dd>{classLabel(yPred, rule)}</dd>
        </div>
        <div>
          <dt>Clase observada (archivada)</dt>
          <dd>{classLabel(yTrue, rule)}</dd>
        </div>
        <div>
          <dt>Umbral utilizado</dt>
          <dd>
            {rule.umbral.toFixed(3)} {rule.unidad} de {rule.variable}
          </dd>
        </div>
        <div>
          <dt>Humedad observada</dt>
          <dd>
            {hasValidMeasurement
              ? `${(medicionOriginal!.valor as number).toFixed(3)} ${rule.unidad}`
              : `No disponible (estado: ${medicionOriginal?.estado ?? "no_determinado"})`}
          </dd>
        </div>
        <div>
          <dt>Relación con el umbral</dt>
          <dd>{distance ? formatDistanceToThreshold(distance) : "No calculable sin medición válida"}</dd>
        </div>
        <div>
          <dt>Categoría del resultado</dt>
          <dd className="hr-outcome-category" data-outcome={category}>
            {OUTCOME_CATEGORY_LABEL[category]}
          </dd>
        </div>
      </dl>
      <p className="hr-distance-disclaimer">
        La relación con el umbral es una distancia física (humedad observada − umbral), no un error
        numérico del modelo: no existe una predicción numérica de humedad, solo una clase binaria.
      </p>
    </div>
  );
}
