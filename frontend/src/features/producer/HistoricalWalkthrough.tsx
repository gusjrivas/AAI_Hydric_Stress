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
const PERGAMINO_DATES = ["2023-06-13", "2023-06-14", "2023-06-15", "2023-06-16", "2023-06-17"];
export function HistoricalWalkthrough({ sensorId, defense = false }: { sensorId: string; defense?: boolean }) {
  const [emissionDate, setEmissionDate] = useState(defense ? PERGAMINO_DATES[0] : "");
  const [revealedThrough, setRevealedThrough] = useState("");
  const effectiveReveal = revealedThrough || emissionDate;

  // Cambiar de sensor invalida cualquier selección anterior: una fecha
  // "preparada" para un sensor no significa nada para otro.
  useEffect(() => {
    setEmissionDate(defense ? PERGAMINO_DATES[0] : "");
    setRevealedThrough("");
  }, [sensorId, defense]);

  const [batchState, setBatchState] = useState<BatchState & { context?: string }>({ status: "idle" });
  const [batchRetry, setBatchRetry] = useState(0);
  const batchSeq = useRef(0);
  const context = `${sensorId}|${emissionDate}|${effectiveReveal}`;
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
    setBatchState({ status: "loading", context });
    getHistoricalForecastBatch(sensorId, emissionDate, revealedThrough || undefined).then(
      (batch) => {
        if (batchSeq.current !== seq) return;
        setBatchState({ status: "ready", batch, context });
      },
      (error: Error) => {
        if (batchSeq.current !== seq) return;
        setBatchState({ status: "error", message: error.message, context });
      },
    );
  }, [sensorId, emissionDate, revealedThrough, context, batchRetry]);

  const [readingsState, setReadingsState] = useState<ReadingsState & { context?: string }>({ status: "idle" });
  const [readingsRetry, setReadingsRetry] = useState(0);
  const readingsSeq = useRef(0);
  useEffect(() => {
    const seq = ++readingsSeq.current;
    if (!effectiveReveal) {
      setReadingsState({ status: "idle" });
      return;
    }
    setReadingsState({ status: "loading", context });
    getHistoricalReadings(sensorId, effectiveReveal, 10).then(
      (data) => {
        if (readingsSeq.current !== seq) return;
        setReadingsState({ status: "ready", data, context });
      },
      (error: Error) => {
        if (readingsSeq.current !== seq) return;
        setReadingsState({ status: "error", message: error.message, context });
      },
    );
  }, [sensorId, effectiveReveal, context, readingsRetry]);

  // Generación del contexto vigente en este render: sensor, emisión y
  // reloj efectivo del recorrido, resumidos en el mismo contador que ya
  // invalida el lote (`batchSeq`) -- se incrementa ante cualquier cambio
  // de esos tres valores, incluida la selección vacía. Capturarlo aquí
  // (no adentro de `reviewed`) fija el valor vigente en el momento en que
  // se crean `reviewed`/`submitReviewFn`/`refetchFn` para las tarjetas
  // que se están mostrando ahora; si el usuario cambia de contexto
  // (incluso conservando la misma emisión, solo con otro reloj de
  // recorrido) antes de que una operación en curso resuelva, `batchSeq`
  // ya avanzó y esta generación queda obsoleta. Comparar únicamente
  // `forecast_id` no alcanza: una respuesta tardía sobre la *misma*
  // emisión pero bajo un reloj anterior lleva un `reviewable` calculado
  // para el reloj viejo, no para el vigente.
  const renderGeneration = batchSeq.current;

  function reviewed(updated: Forecast) {
    setBatchState((current) => {
      // La generación que originó esta actualización ya no es la
      // vigente: descartar el resultado de la pantalla, sin revertir lo
      // que ya se persistió en el backend (esto solo decide qué se
      // muestra, nunca deshace una escritura).
      if (batchSeq.current !== renderGeneration) return current;
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
        {defense && <p className="historical-provenance"><strong>Pergamino · datos externos ERA5-Land/NASA POWER.</strong> No son mediciones de un sensor instalado ni observaciones agronómicas directas. Emisiones disponibles: 13 al 17 de junio de 2023. Melchor Romero y sensores de prueba: próximos recorridos.</p>}
        <label>
          Emisión seleccionada
          {defense ? <select value={emissionDate} onChange={(event) => { setEmissionDate(event.target.value); setRevealedThrough(""); }}>
            {PERGAMINO_DATES.map((date) => <option key={date} value={date}>{displayForecastDate(date)}</option>)}
          </select> : <input
            type="date"
            value={emissionDate}
            onChange={(event) => {
              setEmissionDate(event.target.value);
              if (revealedThrough && revealedThrough < event.target.value) setRevealedThrough("");
            }}
          />}
        </label>
        <label>
          Recorrido hasta (observaciones y revisión)
          <input
            type="date"
            value={revealedThrough}
            min={emissionDate || undefined}
            max={defense ? "2023-06-20" : undefined}
            disabled={!emissionDate}
            onChange={(event) => {
              const value = event.target.value;
              if (defense && value && (value < emissionDate || value > "2023-06-20")) return;
              setRevealedThrough(value);
            }}
          />
        </label>
      </div>
      {emissionDate && (
        <p className="historical-walkthrough-clock">
          Viendo la emisión del <strong>{displayForecastDate(emissionDate)}</strong>
          {" · "}Recorrido avanzado hasta el <strong>{displayForecastDate(effectiveReveal)}</strong>
        </p>
      )}
      {defense && <div className="historical-quality" aria-label="Procedencia y calidad de datos">
        <h4>Procedencia y calidad de los datos disponibles</h4>
        {readingsState.status === "ready" && readingsState.context === context
          ? <p>{readingsState.data.window.expected_days} días esperados; {readingsState.data.missing_dates.length} fechas sin datos. {readingsState.data.variable_coverage.map((item) => `${item.variable}: ${item.observed_days} disponibles, ${item.missing_days} faltantes`).join(" · ")}. Procedencia: {readingsState.data.provenance === "external_reanalysis" ? "ERA5-Land/NASA POWER" : readingsState.data.provenance}.</p>
          : readingsState.status === "error" && readingsState.context === context
            ? <p role="alert">No se pudo consultar la disponibilidad: {readingsState.message} <button type="button" onClick={() => setReadingsRetry((n) => n + 1)}>Reintentar lecturas</button></p>
            : <p role="status">Cargando disponibilidad…</p>}
      </div>}

      {(batchState.status === "loading" || (emissionDate && batchState.context !== context)) && <p role="status">Cargando emisión histórica…</p>}
      {batchState.status === "error" && batchState.context === context && <p role="alert">No se pudo consultar la emisión: {batchState.message} <button type="button" onClick={() => setBatchRetry((n) => n + 1)}>Reintentar emisión</button></p>}
      {batchState.status === "ready" && batchState.context === context && (
        <ul className="forecast-list forecast-outlook-grid">
          {batchState.batch.slots.map((slot) => (
            <li key={`${context}|${slot.horizon_days}`}>
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
                  <h4>+{slot.horizon_days} · {slot.target_date ? displayForecastDate(slot.target_date) : "Fecha objetivo no disponible"}</h4>
                  <p><strong>Sin pronóstico disponible</strong></p>
                  <p>Motivo: {slot.reason_code}</p>
                </article>
              )}
              {slot.target_date && <p className="historical-target-observation"><strong>Observación posterior:</strong> {slot.target_date > effectiveReveal
                ? "Todavía no disponible según el reloj del recorrido."
                : readingsState.status === "ready" && readingsState.context === context
                  ? (() => { const row = readingsState.data.rows.find((item) => item.date === slot.target_date); return row && row.soil_moisture !== null ? `${formatReadingValue("soil_moisture", row.soil_moisture, readingsState.data.units.soil_moisture)} · ${originLabel(row.origin)}` : "Dato faltante en la fuente para esta fecha."; })()
                  : readingsState.status === "error" && readingsState.context === context
                    ? "No se pudo consultar la observación; reintentá las lecturas."
                    : "Cargando dato posterior…"}</p>}
            </li>
          ))}
        </ul>
      )}

      {effectiveReveal && (
        <div className="historical-walkthrough-observations">
          <h4>Observaciones reveladas hasta el {displayForecastDate(effectiveReveal)}</h4>
          {(readingsState.status === "loading" || readingsState.context !== context) && <p role="status">Cargando observaciones…</p>}
          {readingsState.status === "error" && readingsState.context === context && <p role="alert">No se pudieron consultar las observaciones: {readingsState.message} <button type="button" onClick={() => setReadingsRetry((n) => n + 1)}>Reintentar lecturas</button></p>}
          {readingsState.status === "ready" && readingsState.context === context && (
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
