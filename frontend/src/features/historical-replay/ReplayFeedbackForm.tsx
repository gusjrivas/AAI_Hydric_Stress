import { useState } from "react";
import type { EstadoValidacion, ReplayFeedbackEntry, ReplayLabelRule } from "./api";

interface Props {
  existing: ReplayFeedbackEntry[];
  submitting: boolean;
  error: string | null;
  labelRule: ReplayLabelRule;
  onSubmit: (input: {
    estado_validacion: EstadoValidacion;
    etiqueta_corregida?: 0 | 1 | null;
    observacion?: string | null;
  }) => void;
}

/** Formulario de feedback de demostración (RH-07). Solo se muestra una vez
 * revelada la observación (decisión del componente padre); nunca atribuye
 * el registro a un experto ni a una fecha histórica. */
export function ReplayFeedbackForm({ existing, submitting, error, labelRule, onSubmit }: Props) {
  const [estado, setEstado] = useState<EstadoValidacion>("confirmada");
  const [etiqueta, setEtiqueta] = useState<"" | "0" | "1">("");
  const [observacion, setObservacion] = useState("");

  if (existing.length > 0) {
    return (
      <div className="hr-feedback hr-feedback--registered">
        <p role="status">Feedback de demostración ya registrado para esta predicción:</p>
        <ul>
          {existing.map((entry, index) => (
            <li key={index}>
              <strong>{entry.estado_validacion}</strong>
              {entry.observacion && <> — “{entry.observacion}”</>}
              <br />
              <small>
                Registrado el {entry.registered_at} (reloj simulado en {entry.simulated_at})
              </small>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <form
      className="hr-feedback"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit({
          estado_validacion: estado,
          etiqueta_corregida: etiqueta === "" ? undefined : (Number(etiqueta) as 0 | 1),
          observacion: observacion.trim() === "" ? undefined : observacion.trim(),
        });
      }}
    >
      <p className="hr-feedback-disclaimer">
        Este feedback es de demostración: no se atribuye a ningún experto real ni a la fecha
        histórica simulada, y no dispara ninguna recalibración.
      </p>
      <p className="hr-feedback-rule">
        Umbral verificado: {labelRule.umbral.toFixed(3)} {labelRule.unidad} de {labelRule.variable}.
      </p>
      <fieldset>
        <legend>¿La predicción archivada coincide con la observación revelada?</legend>
        <label>
          <input
            type="radio"
            name="estado_validacion"
            value="confirmada"
            checked={estado === "confirmada"}
            onChange={() => setEstado("confirmada")}
          />
          Coincide
        </label>
        <label>
          <input
            type="radio"
            name="estado_validacion"
            value="rechazada"
            checked={estado === "rechazada"}
            onChange={() => setEstado("rechazada")}
          />
          No coincide
        </label>
      </fieldset>
      {estado === "rechazada" && (
        <label>
          Etiqueta que hubiera correspondido (opcional)
          <select value={etiqueta} onChange={(event) => setEtiqueta(event.target.value as "" | "0" | "1")}>
            <option value="">Sin indicar</option>
            <option value="0">0 (no inferior al umbral)</option>
            <option value="1">1 (por debajo del umbral)</option>
          </select>
        </label>
      )}
      <label>
        Observación (opcional)
        <textarea value={observacion} onChange={(event) => setObservacion(event.target.value)} rows={2} />
      </label>
      {error && (
        <p role="alert" className="hr-feedback-error">
          {error}
        </p>
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? "Registrando…" : "Registrar feedback de demostración"}
      </button>
    </form>
  );
}
