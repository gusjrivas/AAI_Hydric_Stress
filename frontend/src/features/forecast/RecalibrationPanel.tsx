import { useEffect, useState } from "react";
import "./ForecastPage.css";
import "./RecalibrationPanel.css";
import { getActivePredictor } from "./api";
import { getLineage } from "../lineage/api";
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
 * improve-alerting-ui-decision-workflow), ubicadas en Modelo y trazabilidad.
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
    let lineageInfo = "";
    if (result.recalibration_id) {
      try {
        const lineage = await getLineage(sensorId);
        const event = lineage.chain.find(
          (entry) => entry.recalibration_id === result.recalibration_id,
        );
        if (event) {
          lineageInfo = ` Predictor origen ${event.source_model_id.slice(0, 8)}… → sucesor ${event.successor_model_id.slice(0, 8)}….`;
        }
      } catch {
        // El linaje tiene su propio estado de error; esta consulta
        // adicional es solo para enriquecer este mensaje.
      }
    }
    workspace.notify(
      `Modelo recalibrado (versión ${result.version}` +
        `${result.recalibration_id ? `, recalibration_id ${result.recalibration_id}` : ""}` +
        `) usando ${result.n_correcciones} corrección(es) — el próximo pronóstico usará este modelo.${lineageInfo}`,
    );
    onRecalibrated();
  }

  return (
    <section aria-label="Correcciones y recalibración" className="rp-panel">
      <h3 className="app-subsection-heading">Correcciones y recalibración</h3>
      <p className="rp-count">
        Correcciones registradas: <strong>{correctionRows.length}</strong>
      </p>

      {appliedStatus === "loading" && (
        <p role="status">Consultando incorporación al predictor activo…</p>
      )}
      {appliedStatus === "unknown" && (
        <p role="status" className="rp-unknown">
          Incorporación al predictor activo: desconocida — no se pudo consultar el predictor.
        </p>
      )}
      {appliedStatus === "ready" && correctionRows.length > 0 && (
        <ul className="rp-correction-list">
          {correctionRows.map((row) => (
            <li key={row.fecha}>
              {row.fecha} —{" "}
              {appliedDates.includes(row.fecha)
                ? "Fecha incorporada al predictor activo"
                : "Todavía no incorporada"}
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
            ? "Recalibrando..."
            : `Recalibrar modelo (${correctionRows.length})`}
        </button>
      )}

      {workspace.actionMessage && (
        <p role="status" className="fp-action-message">
          {workspace.actionMessage}
        </p>
      )}

      <p className="rp-disclaimer">
        Recalibrar reentrena el modelo con las correcciones acumuladas y registra una nueva
        versión — el próximo pronóstico usará esa versión; los pronósticos anteriores se
        conservan. El backend decide si hay correcciones nuevas y temporalmente elegibles; esto
        no afirma una mejora de desempeño.
      </p>
    </section>
  );
}
