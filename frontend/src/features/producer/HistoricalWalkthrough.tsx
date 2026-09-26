import { useEffect, useRef, useState } from "react";
import { ForecastCard } from "./ForecastCard";
import { getHistoricalForecastBatch, getHistoricalReadings, submitHistoricalReview } from "./historicalApi";
import { displayForecastDate, type Forecast, type ForecastBatch, type ReviewRequest } from "./forecastsApi";
import { displayDate, formatReadingValue, originLabel } from "./readingsApi";
import type { ReadingsResult } from "./readingsApi";
import "./HistoricalWalkthrough.css";

type BatchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; batch: ForecastBatch };

type ReadingsState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: ReadingsResult };

/**
 * Reproducción de solo lectura de emisiones ya persistidas. Nunca llama a
 * `emitForecasts` (POST de preparación): solo `GET .../historical/...`.
 *
 * Dos fechas, deliberadamente separadas y nunca fusionadas en una sola
 * etiqueta: `emissionDate` selecciona qué emisión mirar (por su propia
 * fecha de emisión, nunca por `target_date`); `revealedThrough` es el
 * reloj del recorrido -- hasta dónde se revelaron observaciones y hasta
 * dónde llegó la elegibilidad de revisión-- y puede avanzar más allá de
 * `emissionDate` sin cambiar la emisión seleccionada.
 */
export function HistoricalWalkthrough({ sensorId }: { sensorId: string }) {
  const [emissionDate, setEmissionDate] = useState("");
  const [revealedThrough, setRevealedThrough] = useState("");
  const effectiveReveal = revealedThrough || emissionDate;

  // Cambiar de sensor invalida cualquier selección anterior: una fecha
  // "preparada" para un sensor no significa nada para otro.
  useEffect(() => {
    setEmissionDate("");
    setRevealedThrough("");
  }, [sensorId]);

  const [batchState, setBatchState] = useState<BatchState>({ status: "idle" });
  const batchSeq = useRef(0);
  useEffect(() => {
    // Se incrementa siempre, incluso al vaciar la selección: una
    // respuesta tardía de la selección anterior nunca debe poder
    // reemplazar el estado "idle" que corresponde a no tener nada
    // seleccionado.
    const seq = ++batchSeq.current;
    if (!emissionDate) {
      setBatchState({ status: "idle" });
      return;
    }
    setBatchState({ status: "loading" });
    getHistoricalForecastBatch(sensorId, emissionDate, revealedThrough || undefined).then(
      (batch) => {
        if (batchSeq.current !== seq) return;
        setBatchState({ status: "ready", batch });
      },
      (error: Error) => {
        if (batchSeq.current !== seq) return;
        setBatchState({ status: "error", message: error.message });
      },
    );
  }, [sensorId, emissionDate, revealedThrough]);

  const [readingsState, setReadingsState] = useState<ReadingsState>({ status: "idle" });
  const readingsSeq = useRef(0);
  useEffect(() => {
    const seq = ++readingsSeq.current;
    if (!effectiveReveal) {
      setReadingsState({ status: "idle" });
      return;
    }
    setReadingsState({ status: "loading" });
    getHistoricalReadings(sensorId, effectiveReveal, 10).then(
      (data) => {
        if (readingsSeq.current !== seq) return;
        setReadingsState({ status: "ready", data });
      },
      (error: Error) => {
        if (readingsSeq.current !== seq) return;
        setReadingsState({ status: "error", message: error.message });
      },
    );
  }, [sensorId, effectiveReveal]);

  function reviewed(updated: Forecast) {
    setBatchState((current) => {
      // El usuario ya navegó a otra selección desde que se emitió esta
      // revisión: si el `forecast_id` ya no pertenece al lote vigente
      // (por ejemplo, cambió la emisión seleccionada mientras el envío
      // estaba en curso), no corresponde parchear nada, aunque la
      // respuesta en sí sea válida para su propio pedido original.
      if (current.status !== "ready") return current;
      const stillDisplayed = current.batch.slots.some(
        (slot) => slot.status === "available" && slot.forecast_id === updated.forecast_id,
      );
      if (!stillDisplayed) return current;
      return {
        status: "ready",
        batch: {
          ...current.batch,
          slots: current.batch.slots.map((slot) =>
            slot.status === "available" && slot.forecast_id === updated.forecast_id
              ? { ...updated, status: "available" }
              : slot,
          ),
        },
      };
    });
  }

  const submitReviewFn = (sid: string, forecastId: string, request: ReviewRequest) =>
    submitHistoricalReview(sid, effectiveReveal, forecastId, request);

  // No hay una ruta histórica de "un solo pronóstico": ante un conflicto de
  // revisión se vuelve a pedir el lote completo y se toma el mismo
  // forecast_id, en vez de inventar una llamada que no existe.
  const refetchFn = async (sid: string, forecastId: string): Promise<Forecast> => {
    const fresh = await getHistoricalForecastBatch(sid, emissionDate, revealedThrough || undefined);
    const match = fresh.slots.find((slot) => slot.status === "available" && slot.forecast_id === forecastId);
    if (!match || match.status !== "available") throw new Error("No se pudo recuperar esta emisión histórica.");
    return match;
  };

  return (
    <section className="historical-walkthrough" aria-labelledby="historical-walkthrough-title">
      <h3 id="historical-walkthrough-title">Recorrido histórico</h3>
      <p>
        Reproduce emisiones ya preparadas. Nunca genera un pronóstico nuevo ni modifica los resultados guardados. Las
        opiniones que registrés acá quedan aisladas del historial operativo real.
      </p>

      <div className="historical-walkthrough-controls">
        <label>
          Emisión seleccionada
          <input
            type="date"
            value={emissionDate}
            onChange={(event) => {
              setEmissionDate(event.target.value);
              if (revealedThrough && revealedThrough < event.target.value) setRevealedThrough("");
            }}
          />
        </label>
        <label>
          Recorrido hasta (observaciones y revisión)
          <input
            type="date"
            value={revealedThrough}
            min={emissionDate || undefined}
            disabled={!emissionDate}
            onChange={(event) => setRevealedThrough(event.target.value)}
          />
        </label>
      </div>
      {emissionDate && (
        <p className="historical-walkthrough-clock">
          Viendo la emisión del <strong>{displayForecastDate(emissionDate)}</strong>
          {" · "}Recorrido avanzado hasta el <strong>{displayForecastDate(effectiveReveal)}</strong>
        </p>
      )}

      {batchState.status === "loading" && <p role="status">Cargando emisión histórica…</p>}
      {batchState.status === "error" && <p role="alert">{batchState.message}</p>}
      {batchState.status === "ready" && (
        <ul className="forecast-list forecast-outlook-grid">
          {batchState.batch.slots.map((slot) => (
            <li key={slot.horizon_days}>
              {slot.status === "available" ? (
                <ForecastCard
                  sensorId={sensorId}
                  forecast={slot}
                  onChanged={reviewed}
                  submitReviewFn={submitReviewFn}
                  refetchFn={refetchFn}
                  historicalNotice="Revisión de prueba técnica en modo histórico: queda aislada del historial operativo real, no se incorpora a reentrenamiento ni recalibración."
                />
              ) : (
                <article className="forecast-card">
                  <h4>{slot.target_date ? displayForecastDate(slot.target_date) : `Día ${slot.horizon_days}`}</h4>
                  <p><strong>Sin pronóstico disponible</strong></p>
                </article>
              )}
            </li>
          ))}
        </ul>
      )}

      {effectiveReveal && (
        <div className="historical-walkthrough-observations">
          <h4>Observaciones reveladas hasta el {displayForecastDate(effectiveReveal)}</h4>
          {readingsState.status === "loading" && <p role="status">Cargando observaciones…</p>}
          {readingsState.status === "error" && <p role="alert">{readingsState.message}</p>}
          {readingsState.status === "ready" && (
            readingsState.data.status === "no_readings" ? (
              <p role="status">No hay observaciones reveladas hasta esta fecha.</p>
            ) : (
              <table>
                <thead><tr><th scope="col">Fecha</th><th scope="col">Humedad del suelo</th><th scope="col">Origen</th></tr></thead>
                <tbody>
                  {readingsState.data.rows.map((row) => (
                    <tr key={row.date}>
                      <th scope="row">{displayDate(row.date)}</th>
                      <td>{formatReadingValue("soil_moisture", row.soil_moisture, readingsState.data.units.soil_moisture)}</td>
                      <td>{originLabel(row.origin)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
          <p className="historical-walkthrough-note">
            Nunca se revelan observaciones posteriores a esta fecha, incluso si ya existen guardadas.
          </p>
        </div>
      )}
    </section>
  );
}
