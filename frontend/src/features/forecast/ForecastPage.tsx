import { useState } from "react";
import "./ForecastPage.css";
import {
  confirmAlert,
  listFeedback,
  rejectAlert,
  runForecast,
} from "./api";
import type { FeedbackRow, Verdict } from "./api";

export function ForecastPage() {
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [feedback, setFeedback] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function handleRunForecast() {
    setLoading(true);
    setError(null);
    setActionMessage(null);
    try {
      const result = await runForecast();
      setVerdicts(result.verdicts);
      const feedbackResult = await listFeedback();
      setFeedback(feedbackResult.rows);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(fecha: string) {
    const updated = await confirmAlert(fecha);
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
    setActionMessage(`Guardada la validación del ${fecha} — el modelo no se actualizó.`);
  }

  async function handleReject(fecha: string) {
    const updated = await rejectAlert(fecha, 0, "Rechazada desde la interfaz");
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
    setActionMessage(`Guardada la validación del ${fecha} — el modelo no se actualizó.`);
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
        <button className="fp-run-btn" onClick={handleRunForecast} disabled={loading}>
          {loading ? "Corriendo..." : "Correr pronóstico"}
        </button>
      </header>

      <div className="fp-banner" role="note">
        <strong>Qué prueba esta pantalla:</strong> confirmar o rechazar guarda tu validación en
        el registro de retroalimentación. En esta primera iteración{" "}
        <strong>no se reentrena el modelo automáticamente</strong> — la evidencia se acumula
        para una futura recalibración.
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
                <div className="fp-row-date">{verdict.fecha}</div>
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
                <button onClick={() => handleConfirm(verdict.fecha)}>Confirmar</button>
                <button onClick={() => handleReject(verdict.fecha)}>Rechazar</button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
