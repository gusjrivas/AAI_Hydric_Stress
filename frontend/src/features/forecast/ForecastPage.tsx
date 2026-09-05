import { useState } from "react";
import "./ForecastPage.css";
import {
  confirmAlert,
  listFeedback,
  recalibrate,
  rejectAlert,
  runForecast,
} from "./api";
import type { FeedbackRow, Verdict } from "./api";

export function ForecastPage() {
  const [sensorId, setSensorId] = useState("sensor-a");
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [feedback, setFeedback] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [recalibrating, setRecalibrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const pendingCorrections = feedback.filter(
    (row) => row.estado_validacion === "rechazada" && row.etiqueta_corregida !== null,
  ).length;

  async function handleRunForecast() {
    setLoading(true);
    setError(null);
    setActionMessage(null);
    try {
      const result = await runForecast(sensorId);
      setVerdicts(result.verdicts);
      const feedbackResult = await listFeedback(sensorId);
      setFeedback(feedbackResult.rows);
      setVerdicts([
        ...feedbackResult.rows.filter((r) => r.y_proba != null && !result.verdicts.some((v) => v.fecha === r.fecha))
          .map((r) => ({ fecha: r.fecha, alerta: Boolean(r.alerta_generada), probabilidad: r.y_proba!, fecha_objetivo: r.fecha_objetivo ?? undefined })),
        ...result.verdicts,
      ]);
      if (result.selection_warning) setActionMessage(result.selection_warning);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(fecha: string) {
    const updated = await confirmAlert(sensorId, fecha);
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
    setActionMessage(`Guardada la validación del ${fecha} — el modelo no se actualizó.`);
  }

  async function handleReject(fecha: string) {
    const updated = await rejectAlert(sensorId, fecha, verdicts.find((v) => v.fecha === fecha)?.alerta ? 0 : 1, "Rechazada desde la interfaz");
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
    setActionMessage(`Guardada la validación del ${fecha} — el modelo no se actualizó.`);
  }

  async function handleRecalibrate() {
    setRecalibrating(true);
    setError(null);
    try {
      const result = await recalibrate(sensorId);
      setActionMessage(
        `Modelo recalibrado (versión ${result.version}) usando ${result.n_correcciones} corrección(es) — el próximo pronóstico usará este modelo.`,
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRecalibrating(false);
    }
  }

  function stateFor(fecha: string): string {
    return feedback.find((row) => row.fecha === fecha)?.estado_validacion ?? "pendiente";
  }

  return (
    <div className="fp-page">
      <header className="fp-header">
        <div>
          <h1 className="fp-title">Pronóstico de estrés hídrico</h1>
          <p className="fp-subtitle">Validación humana de alertas sobre el dataset consolidado</p>
        </div>
        <div className="fp-header-actions">
          <label>Sensor <input aria-label="Sensor" value={sensorId} disabled={loading || recalibrating}
            onChange={(event) => { setSensorId(event.target.value); setVerdicts([]); setFeedback([]); setError(null); setActionMessage(null); }} /></label>
          {pendingCorrections > 0 && (
            <button
              className="fp-recalibrate-btn"
              onClick={handleRecalibrate}
              disabled={recalibrating}
            >
              {recalibrating ? "Recalibrando..." : `Recalibrar modelo (${pendingCorrections})`}
            </button>
          )}
          <button className="fp-run-btn" onClick={handleRunForecast} disabled={loading || !/^[a-zA-Z0-9_-]{1,64}$/.test(sensorId)}>
            {loading ? "Corriendo..." : "Correr pronóstico"}
          </button>
        </div>
      </header>

      <div className="fp-banner" role="note">
        <strong>Qué prueba esta pantalla:</strong> confirmar o rechazar guarda tu validación en
        el registro de retroalimentación. Recalibrar reentrena el modelo con las correcciones
        acumuladas y registra una nueva versión — el próximo pronóstico usará esa versión.
      </div>

      {error && <p role="alert" className="fp-error">{error}</p>}
      {actionMessage && (
        <p role="status" className="fp-action-message">
          {actionMessage}
        </p>
      )}

      <ul className="fp-list">
        {verdicts.map((verdict) => {
          const estado = stateFor(verdict.fecha);
          const severity = verdict.alerta ? "alert" : "safe";
          return (
            <li key={verdict.fecha} className={`fp-row fp-row--${severity}`}>
              <span className="fp-signal" aria-hidden="true" />
              <div className="fp-row-main">
                <div className="fp-row-date">{verdict.fecha}</div>{verdict.fecha_objetivo && <div>Objetivo: {verdict.fecha_objetivo}</div>}
                <div className="fp-row-verdict">{verdict.alerta ? "Alerta" : "Sin alerta"}</div>
              </div>
              <div className="fp-gauge">
                <span className="fp-gauge-value">{verdict.probabilidad.toFixed(2)}</span>
                <span className="fp-gauge-bar">
                  <span
                    className="fp-gauge-fill"
                    style={{ width: `${Math.round(verdict.probabilidad * 100)}%` }}
                  />
                </span>
              </div>
              <span className={`fp-badge fp-badge--${estado}`}>{estado}</span>
              <div className="fp-actions">
                <button onClick={() => handleConfirm(verdict.fecha).catch((err) => setError(err.message))}>Confirmar</button>
                <button onClick={() => handleReject(verdict.fecha).catch((err) => setError(err.message))}>Rechazar</button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
