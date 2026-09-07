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
import { ActivePredictorSummary } from "./ActivePredictorSummary";
import { getLineage } from "../lineage/api";

interface ForecastPageProps {
  sensorId?: string;
  onSensorIdChange?: (sensorId: string) => void;
  onRecalibrated?: () => void;
}

export function ForecastPage({
  sensorId: sensorIdProp,
  onSensorIdChange,
  onRecalibrated,
}: ForecastPageProps = {}) {
  const [internalSensorId, setInternalSensorId] = useState("sensor-a");
  const sensorId = sensorIdProp ?? internalSensorId;
  const setSensorId = onSensorIdChange ?? setInternalSensorId;

  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [feedback, setFeedback] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [recalibrating, setRecalibrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [predictorRefreshToken, setPredictorRefreshToken] = useState(0);

  const pendingCorrections = feedback.filter(
    (row) => row.estado_validacion === "rechazada" && row.etiqueta_corregida !== null,
  ).length;
  const feedbackPendienteRevision = feedback.filter(
    (row) => row.estado_validacion === "pendiente",
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
      setPredictorRefreshToken((token) => token + 1);
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
      setActionMessage(
        `Modelo recalibrado (versión ${result.version}` +
          `${result.recalibration_id ? `, recalibration_id ${result.recalibration_id}` : ""}` +
          `) usando ${result.n_correcciones} corrección(es) — el próximo pronóstico usará este modelo.${lineageInfo}`,
      );
      setPredictorRefreshToken((token) => token + 1);
      onRecalibrated?.();
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
          <h3 className="fp-title">Pronóstico de estrés hídrico</h3>
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

      <p className="fp-disclaimer">
        La probabilidad es una señal predictiva relativa del modelo y no un diagnóstico
        fisiológico ni una probabilidad agronómicamente calibrada.
      </p>

      <section className="fp-predictor-section" aria-label="Predictor activo">
        <h3 className="fp-section-heading">Predictor activo</h3>
        <ActivePredictorSummary sensorId={sensorId} refreshToken={predictorRefreshToken} />
      </section>

      {error && <p role="alert" className="fp-error">{error}</p>}
      {actionMessage && (
        <p role="status" className="fp-action-message">
          {actionMessage}
        </p>
      )}

      <p className="fp-feedback-stats">
        Feedback sin revisar: <strong>{feedbackPendienteRevision}</strong> · Correcciones sin
        incorporar a la recalibración: <strong>{pendingCorrections}</strong>
      </p>

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
