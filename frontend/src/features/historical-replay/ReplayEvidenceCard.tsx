import type { ReplayCandidateInfo } from "./api";
import { ruleDescription } from "./labelRule";

/** Ficha expandible de trazabilidad (Paso 4 §4, Paso 4.1 §3): campos explícitos
 * tomados de la respuesta de la API, nunca el manifiesto completo. Distingue
 * el corte de partición de la fecha máxima de entrenamiento — no son lo
 * mismo en este candidato — y muestra la regla de la clase proxy verificada. */
export function ReplayEvidenceCard({ candidate }: { candidate: ReplayCandidateInfo }) {
  return (
    <details className="hr-evidence">
      <summary>Ficha de trazabilidad</summary>
      <dl className="hr-evidence-list">
        <div>
          <dt>Origen de los datos</dt>
          <dd>{candidate.evidencia.dataset_name} (dato real, no sintético)</dd>
        </div>
        <div>
          <dt>Identidad del modelo y run</dt>
          <dd>
            experimento {candidate.experiment_id}, run <code>{candidate.run_id}</code>,
            configuración {candidate.config_name}, semilla {candidate.seed}
          </dd>
        </div>
        <div>
          <dt>Corte de partición (train/test)</dt>
          <dd>{candidate.evidencia.split_date}</dd>
        </div>
        <div>
          <dt>Última fecha realmente usada para entrenar</dt>
          <dd>
            {candidate.evidencia.training_max_date}
            {candidate.evidencia.training_max_date !== candidate.evidencia.split_date && (
              <> (anterior al corte de partición; no son la misma fecha)</>
            )}
          </dd>
        </div>
        <div>
          <dt>Horizonte</dt>
          <dd>+{candidate.horizon_days} días</dd>
        </div>
        <div>
          <dt>Regla de la clase proxy</dt>
          <dd>{ruleDescription(candidate.regla_etiqueta)}</dd>
        </div>
        <div>
          <dt>Identificación del paquete</dt>
          <dd>
            <code>{candidate.evidencia.package_id}</code>, commit <code>{candidate.evidencia.commit_sha}</code>
          </dd>
        </div>
        <div>
          <dt>Convención de fecha</dt>
          <dd>{candidate.evidencia.day_convention}</dd>
        </div>
        <div>
          <dt>Supuesto de disponibilidad diaria</dt>
          <dd>{candidate.evidencia.issuance_assumption}</dd>
        </div>
        <div>
          <dt>Limitaciones</dt>
          <dd>
            <ul>
              {candidate.limitaciones.map((limitacion) => (
                <li key={limitacion}>{limitacion}</li>
              ))}
            </ul>
          </dd>
        </div>
      </dl>
    </details>
  );
}
