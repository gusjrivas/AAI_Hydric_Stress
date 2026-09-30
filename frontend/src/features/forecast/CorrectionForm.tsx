import { useState } from "react";
import type { FeedbackRow } from "./api";

interface CorrectionFormProps {
  row: FeedbackRow;
  saving: boolean;
  /** Motivos por los que la fila dejó de ser revisable con el formulario
   * ya abierto (fecha objetivo o bloqueo de la demo). Distinto de
   * `saving`: "bloqueado" no es "guardando". Vacío si es revisable. */
  blockedReasons?: string[];
  serverError: string | null;
  onCancel: () => void;
  onSave: (etiquetaCorregida: 0 | 1, observacion: string) => void;
}

/**
 * Formulario inline de corrección (task 3.1 de
 * improve-alerting-ui-decision-workflow): no escribe nada hasta que se
 * guarda una etiqueta explícita y opuesta a la original; la misma etiqueta
 * orienta a Confirmar en vez de habilitar el guardado.
 */
export function CorrectionForm({ row, saving, blockedReasons = [], serverError, onCancel, onSave }: CorrectionFormProps) {
  const [etiqueta, setEtiqueta] = useState<0 | 1 | null>(null);
  const [observacion, setObservacion] = useState("");

  const original = row.alerta_generada ? 1 : 0;
  const sameAsOriginal = etiqueta !== null && etiqueta === original;
  const blocked = blockedReasons.length > 0;
  const canSave = etiqueta !== null && !sameAsOriginal && !saving && !blocked;

  return (
    <div className="fp-correction-form" role="group" aria-label={`Corregir resultado del ${row.fecha}`}>
      <p>
        Resultado original: <strong>{row.alerta_generada ? "Alerta" : "Sin alerta"}</strong>
      </p>
      <p>
        Pronóstico para el día: <strong>{row.fecha_objetivo ?? "No disponible"}</strong>
      </p>
      <fieldset className="fp-correction-fieldset">
        <legend>Resultado observado</legend>
        <label>
          <input
            type="radio"
            name={`etiqueta-observada-${row.fecha}`}
            checked={etiqueta === 1}
            onChange={() => setEtiqueta(1)}
            disabled={saving}
          />
          Alerta
        </label>
        <label>
          <input
            type="radio"
            name={`etiqueta-observada-${row.fecha}`}
            checked={etiqueta === 0}
            onChange={() => setEtiqueta(0)}
            disabled={saving}
          />
          Sin alerta
        </label>
      </fieldset>
      {sameAsOriginal && (
        <p role="status" className="fp-correction-hint">
          Tu observación coincide con el resultado. Usá «Confirmar» para guardarla.
        </p>
      )}
      <label className="fp-correction-observacion">
        Observación (opcional)
        <textarea
          value={observacion}
          onChange={(event) => setObservacion(event.target.value)}
          disabled={saving}
        />
      </label>
      {blocked && (
        <div role="status" className="fp-correction-hint">
          {blockedReasons.map((reason) => (
            <p key={reason}>{reason}</p>
          ))}
        </div>
      )}
      {serverError && (
        <p role="alert" className="fp-error">
          {serverError}
        </p>
      )}
      <div className="fp-correction-actions">
        <button
          type="button"
          onClick={() => onSave(etiqueta as 0 | 1, observacion)}
          disabled={!canSave}
        >
          {saving ? "Guardando..." : "Guardar corrección"}
        </button>
        <button type="button" onClick={onCancel} disabled={saving}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
