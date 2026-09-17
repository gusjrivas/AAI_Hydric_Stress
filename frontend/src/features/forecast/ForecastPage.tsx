import { useEffect, useState } from "react";
import "./ForecastPage.css";
import { getLineage } from "../lineage/api";
import { ActivePredictorSummary } from "./ActivePredictorSummary";
import { useForecastWorkspace } from "./useForecastWorkspace";

interface ForecastPageProps {
  sensorId: string;
  onRecalibrated?: () => void;
  onBusyChange?: (busy: boolean) => void;
}

export function ForecastPage({ sensorId, onRecalibrated, onBusyChange }: ForecastPageProps) {
  const workspace = useForecastWorkspace(sensorId);
  const [predictorRefreshToken, setPredictorRefreshToken] = useState(0);

  useEffect(() => {
    onBusyChange?.(workspace.activeMutation !== null);
  }, [workspace.activeMutation, onBusyChange]);

  const pendingCorrections = workspace.rows.filter(
    (row) => row.estado_validacion === "rechazada" && row.etiqueta_corregida !== null,
  ).length;
  const feedbackPendienteRevision = workspace.rows.filter(
    (row) => row.estado_validacion === "pendiente",
  ).length;

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
          lineageInfo = ` Predictor origen ${event.source_model_id.slice(0, 8)}… → sucesor ${event.successor_model_id.slice(0, 8)}… (ver sección Linaje).`;
        }
      } catch {
        // La sección de Linaje tiene su propio estado de error; esta
        // consulta adicional es solo para enriquecer este mensaje.
      }
    }
    workspace.notify(
      `Modelo recalibrado (versión ${result.version}` +
        `${result.recalibration_id ? `, recalibration_id ${result.recalibration_id}` : ""}` +
        `) usando ${result.n_correcciones} corrección(es) — el próximo pronóstico usará este modelo.${lineageInfo}`,
    );
    setPredictorRefreshToken((token) => token + 1);
    onRecalibrated?.();
  }

  async function handleRunForecast() {
    await workspace.runForecast();
    setPredictorRefreshToken((token) => token + 1);
  }

  return (
    <div className="fp-page">
      <header className="fp-header">
        <div>
          <h3 className="fp-title">Pronóstico de estrés hídrico</h3>
          <p className="fp-subtitle">Validación humana de alertas sobre el dataset consolidado</p>
        </div>
        <div className="fp-header-actions">
          {pendingCorrections > 0 && (
            <button className="fp-recalibrate-btn" onClick={handleRecalibrate} disabled={busy}>
              {workspace.activeMutation === "recalibrate"
                ? "Recalibrando..."
                : `Recalibrar modelo (${pendingCorrections})`}
            </button>
          )}
          <button className="fp-run-btn" onClick={handleRunForecast} disabled={busy}>
            {workspace.activeMutation === "forecast" ? "Corriendo..." : "Correr pronóstico"}
          </button>
        </div>
      </header>

      <div className="fp-banner" role="note">
        <strong>Qué prueba esta pantalla:</strong> consultar el historial no genera un
        pronóstico nuevo. Confirmar o rechazar guarda tu validación en el registro de
        retroalimentación. Recalibrar reentrena el modelo con las correcciones acumuladas y
        registra una nueva versión — el próximo pronóstico usará esa versión.
      </div>

      <p className="fp-disclaimer">
        La probabilidad es una señal predictiva relativa del modelo y no un diagnóstico
        fisiológico ni una probabilidad agronómicamente calibrada.
      </p>

      <section className="fp-predictor-section" aria-label="Predictor activo">
        <h3 className="fp-section-heading">Predictor activo</h3>
        <ActivePredictorSummary sensorId={sensorId} refreshToken={predictorRefreshToken} />
      </section>

      {workspace.runError && (
        <p role="alert" className="fp-error">
          {workspace.runError}
        </p>
      )}
      {workspace.actionMessage && (
        <p role="status" className="fp-action-message">
          {workspace.actionMessage}
        </p>
      )}
      {workspace.refreshPending && (
        <p role="alert" className="fp-error">
          No se pudo confirmar la actualización del historial.{" "}
          <button type="button" onClick={() => void workspace.reloadHistory()}>
            Actualizar
          </button>
        </p>
      )}

      {workspace.historyStatus === "loading" && (
        <p role="status">Consultando historial…</p>
      )}

      {workspace.historyStatus === "empty" && (
        <p role="status">Todavía no hay pronósticos registrados.</p>
      )}

      {workspace.historyStatus === "error" && (
        <p role="alert" className="fp-error">
          {workspace.historyError ?? "No se pudo consultar el historial."}{" "}
          <button type="button" onClick={() => void workspace.reloadHistory()}>
            Reintentar
          </button>
        </p>
      )}

      {(workspace.historyStatus === "ready" || workspace.rows.length > 0) && (
        <>
          <p className="fp-feedback-stats">
            Feedback sin revisar: <strong>{feedbackPendienteRevision}</strong> · Correcciones sin
            incorporar a la recalibración: <strong>{pendingCorrections}</strong>
          </p>

          <ul className="fp-list">
            {workspace.rows.map((row) => {
              const severity = row.alerta_generada ? "alert" : "safe";
              const rowBusy =
                workspace.activeMutation === `confirm:${row.fecha}` ||
                workspace.activeMutation === `reject:${row.fecha}`;
              return (
                <li key={row.fecha} className={`fp-row fp-row--${severity}`}>
                  <span className="fp-signal" aria-hidden="true" />
                  <div className="fp-row-main">
                    <div className="fp-row-date">{row.fecha}</div>
                    {row.fecha_objetivo && <div>Objetivo: {row.fecha_objetivo}</div>}
                    <div className="fp-row-verdict">
                      {row.alerta_generada ? "Alerta" : "Sin alerta"}
                    </div>
                  </div>
                  <div className="fp-gauge">
                    {row.y_proba != null ? (
                      <>
                        <span className="fp-gauge-value">{row.y_proba.toFixed(2)}</span>
                        <span className="fp-gauge-bar">
                          <span
                            className="fp-gauge-fill"
                            style={{ width: `${Math.round(row.y_proba * 100)}%` }}
                          />
                        </span>
                      </>
                    ) : (
                      <span className="fp-gauge-value">No disponible</span>
                    )}
                  </div>
                  <span className={`fp-badge fp-badge--${row.estado_validacion}`}>
                    {row.estado_validacion}
                  </span>
                  <div className="fp-actions">
                    <button onClick={() => workspace.confirm(row.fecha)} disabled={busy}>
                      {rowBusy && workspace.activeMutation === `confirm:${row.fecha}`
                        ? "Guardando..."
                        : "Confirmar"}
                    </button>
                    <button
                      onClick={() =>
                        workspace.reject(row.fecha, row.alerta_generada ? 0 : 1, "Rechazada desde la interfaz")
                      }
                      disabled={busy}
                    >
                      {rowBusy && workspace.activeMutation === `reject:${row.fecha}`
                        ? "Guardando..."
                        : "Rechazar"}
                    </button>
                  </div>
                  {workspace.rowErrors[row.fecha] && (
                    <p role="alert" className="fp-error">
                      {workspace.rowErrors[row.fecha]}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
