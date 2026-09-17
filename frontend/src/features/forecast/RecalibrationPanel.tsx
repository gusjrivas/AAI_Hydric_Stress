import { useEffect, useState } from "react";
import "./ForecastPage.css";
import "./RecalibrationPanel.css";
import { getActivePredictor } from "./api";
import type { ForecastWorkspace } from "./useForecastWorkspace";

type AppliedStatus = "loading" | "unknown" | "ready";

interface RecalibrationPanelProps {
  sensorId: string;
  workspace: ForecastWorkspace;
  refreshToken: number;
  onRecalibrated: () => void;
}

/**
 * Correcciones registradas, fechas incorporadas al predictor activo y
 * recalibración manual (tasks 3.3 y 3.4 de
 * improve-alerting-ui-decision-workflow), ubicadas en Ajustar próximos pronósticos.
 * No calcula un total de correcciones "elegibles": la API actual no expone
 * un preflight de elegibilidad temporal, esa autoridad sigue en el backend.
 */
export function RecalibrationPanel({
  sensorId,
  workspace,
  refreshToken,
  onRecalibrated,
}: RecalibrationPanelProps) {
  const requestKey = `${sensorId}:${refreshToken}`;
  const [loadedFor, setLoadedFor] = useState(requestKey);
  const [appliedStatus, setAppliedStatus] = useState<AppliedStatus>("loading");
  const [appliedDates, setAppliedDates] = useState<string[]>([]);

  if (requestKey !== loadedFor) {
    setLoadedFor(requestKey);
    setAppliedStatus("loading");
    setAppliedDates([]);
  }

  useEffect(() => {
    let cancelled = false;
    getActivePredictor(sensorId)
      .then((predictor) => {
        if (cancelled) return;
        setAppliedDates(predictor.applied_feedback_dates ?? []);
        setAppliedStatus("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setAppliedStatus("unknown");
      });
    return () => {
      cancelled = true;
    };
  }, [sensorId, refreshToken]);

  const correctionRows = workspace.rows.filter(
    (row) => row.estado_validacion === "rechazada" && row.etiqueta_corregida !== null,
  );
  const busy = workspace.activeMutation !== null;

  async function handleRecalibrate() {
    const result = await workspace.recalibrate();
    if (!result) return;
    workspace.notify(
      `Se aplicaron ${result.n_correcciones} corrección(es). Se usarán al generar el próximo pronóstico. Los resultados anteriores se conservan.`,
    );
    onRecalibrated();
  }

  return (
    <section aria-label="Usar las observaciones guardadas" className="rp-panel">
      <h3 className="app-subsection-heading">Usar las observaciones guardadas</h3>
      <p>Este paso prepara los próximos pronósticos usando las correcciones que guardaste. No genera un pronóstico nuevo ni modifica los resultados anteriores.</p>
      <p className="rp-count">
        Correcciones registradas: <strong>{correctionRows.length}</strong>
      </p>

      {appliedStatus === "loading" && (
        <p role="status">Consultando las observaciones utilizadas…</p>
      )}
      {appliedStatus === "unknown" && (
        <p role="status" className="rp-unknown">
          No se pudo comprobar qué observaciones se usaron. Intentá consultar de nuevo más tarde.
        </p>
      )}
      {appliedStatus === "ready" && correctionRows.length > 0 && (
        <ul className="rp-correction-list">
          {correctionRows.map((row) => (
            <li key={row.fecha}>
              {row.fecha} —{" "}
              {appliedDates.includes(row.fecha)
                ? "Observaciones de esta fecha usadas anteriormente"
                : "Sin registro de uso"}
            </li>
          ))}
        </ul>
      )}

      {workspace.recalibrateError && (
        <p role="alert" className="fp-error">
          {workspace.recalibrateError}
        </p>
      )}

      {correctionRows.length > 0 && (
        <button className="fp-recalibrate-btn" onClick={handleRecalibrate} disabled={busy}>
          {workspace.activeMutation === "recalibrate"
            ? "Aplicando observaciones..."
            : `Aplicar observaciones (${correctionRows.length})`}
        </button>
      )}

      {workspace.actionMessage && (
        <p role="status" className="fp-action-message">
          {workspace.actionMessage}
        </p>
      )}

      <p className="rp-disclaimer">
        Solo se pueden usar observaciones que cumplan las condiciones de fecha y registro.
        La herramienta lo comprueba al aplicar los cambios. Si editaste una observación después
        de haberla usado, la fecha por sí sola no confirma que esa edición esté aplicada.
        Incorporar observaciones no garantiza pronósticos más acertados.
      </p>
    </section>
  );
}
