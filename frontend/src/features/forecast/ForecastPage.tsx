import { useState } from "react";
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

  async function handleRunForecast() {
    setLoading(true);
    setError(null);
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
  }

  async function handleReject(fecha: string) {
    const updated = await rejectAlert(fecha, 0, "Rechazada desde la interfaz");
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
  }

  function stateFor(fecha: string): string {
    return feedback.find((row) => row.fecha === fecha)?.estado_validacion ?? "pendiente";
  }

  return (
    <div>
      <h1>Pronóstico de estrés hídrico</h1>
      <button onClick={handleRunForecast} disabled={loading}>
        {loading ? "Corriendo..." : "Correr pronóstico"}
      </button>
      {error && <p role="alert">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Alerta</th>
            <th>Probabilidad</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {verdicts.map((verdict) => (
            <tr key={verdict.fecha}>
              <td>{verdict.fecha}</td>
              <td>{verdict.alerta ? "Sí" : "No"}</td>
              <td>{verdict.probabilidad.toFixed(2)}</td>
              <td>{stateFor(verdict.fecha)}</td>
              <td>
                <button onClick={() => handleConfirm(verdict.fecha)}>Confirmar</button>
                <button onClick={() => handleReject(verdict.fecha)}>Rechazar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
