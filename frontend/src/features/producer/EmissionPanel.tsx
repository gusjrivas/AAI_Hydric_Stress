import { useEffect, useRef, useState } from "react";
import { ForecastCard } from "./ForecastCard";
import { displayForecastDate, emitForecasts, listForecasts, newRequestId } from "./forecastsApi";
import type { Forecast, ForecastBatch } from "./forecastsApi";
import { buildSavedBatch } from "./producerOutlook";
import { ProducerAnswer } from "./ProducerAnswer";
import { getSensorReadings } from "./readingsApi";

const REASONS: Record<string, string> = {
  no_readings: "Todavía no hay mediciones para este punto.",
  model_not_available: "Todavía no hay un pronóstico preparado para este día.",
  insufficient_data: "Faltan mediciones recientes para estimar este día.",
  incompatible_units: "Las unidades de las mediciones necesitan una revisión.",
  model_not_available_at_date: "Las mediciones son anteriores al período que puede usar este pronóstico.",
  not_saved: "Este día no tiene un pronóstico guardado.",
};

/**
 * Último pronóstico ya guardado del punto (solo lectura: `GET`, nunca emite). Devuelve null si todavía no hay
 * ninguno o si no se pudo consultar: en ese caso la pantalla sigue ofreciendo la consulta explícita.
 */
async function loadSavedBatch(sensorId: string): Promise<ForecastBatch | null> {
  const [list, readings] = await Promise.all([
    listForecasts(sensorId, { limit: 20 }),
    getSensorReadings(sensorId, 1).catch(() => null),
  ]);
  return buildSavedBatch(list.items, {
    server_today: readings?.server_today ?? new Date().toISOString().slice(0, 10),
    data_age_days: readings?.data_age_days ?? null,
    provenance: readings?.provenance ?? "unknown",
  });
}

export function EmissionPanel({
  sensorId,
  onChanged,
  onBatch,
}: {
  sensorId: string;
  onChanged: () => void;
  /** Notifica el lote vigente al contenedor sin duplicar el estado: sigue siendo este componente el único que lo posee. */
  onBatch?: (batch: ForecastBatch | null) => void;
}) {
  const [batch, setBatch] = useState<ForecastBatch | null>(null);
  const [fromSaved, setFromSaved] = useState(false);
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef<string | null>(null);
  const emittedHere = useRef(false);
  const alive = useRef(false);
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);
  useEffect(() => {
    // Cambiar de sensor descarta el lote anterior. Nunca se emite nada automáticamente al entrar ni al cambiar
    // de sensor: `POST /forecasts` prepara una emisión (aunque sea idempotente) y es una acción operativa
    // explícita. Lo único que se hace solo es LEER el último pronóstico ya guardado (`GET`).
    setBatch(null);
    setFromSaved(false);
    setError(null);
    requestId.current = null;
    emittedHere.current = false;
    onBatch?.(null);
    let cancelled = false;
    setLoadingSaved(true);
    loadSavedBatch(sensorId).then(
      (saved) => {
        if (cancelled || emittedHere.current) return;
        setLoadingSaved(false);
        if (!saved) return;
        setBatch(saved);
        setFromSaved(true);
        onBatch?.(saved);
      },
      () => {
        if (!cancelled) setLoadingSaved(false);
      },
    );
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sensorId]);
  async function generate() {
    if (busy) return;
    requestId.current ??= newRequestId();
    setBusy(true);
    setError(null);
    try {
      const result = await emitForecasts(sensorId, requestId.current);
      if (!alive.current) return;
      emittedHere.current = true;
      setBatch(result);
      setFromSaved(false);
      onBatch?.(result);
      requestId.current = null;
      onChanged();
    } catch (failure) {
      if (alive.current) setError(failure instanceof Error ? failure.message : "No pudimos recuperar el resultado.");
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  function reviewed(forecast: Forecast) {
    setBatch((current) => {
      if (!current) return current;
      const updated: ForecastBatch = { ...current, slots: current.slots.map((slot) =>
        slot.status === "available" && slot.forecast_id === forecast.forecast_id
          ? { ...forecast, status: "available" as const } : slot) };
      onBatch?.(updated);
      return updated;
    });
    onChanged();
  }

  const actions = (
    <div className="producer-outlook-actions">
      <button type="button" disabled={busy} onClick={() => void generate()}>
        {busy ? "Preparando pronósticos…" : error ? "Reintentar consulta" : batch ? "Actualizar pronóstico" : "Consultar próximos tres días"}
      </button>
      {fromSaved && <p className="producer-outlook-note">Este es el último pronóstico guardado. Tocá «Actualizar pronóstico» para calcular uno nuevo con las mediciones más recientes.</p>}
    </div>
  );

  return <section className="producer-outlook" aria-label="Próximos tres días">
    {!batch && <>
      <h3 id="next-days-heading">Los próximos tres días del cultivo</h3>
      <p>Consultá qué se espera para cada día a partir de la última medición disponible.</p>
      {loadingSaved && !busy && <p role="status">Buscando el último pronóstico guardado…</p>}
      {!loadingSaved && !error && !busy && <div className="producer-outlook-placeholder"><p>Todavía no hay un pronóstico guardado para este punto. Tocá el botón para calcularlo; si faltan datos, te lo vamos a indicar.</p></div>}
      {actions}
    </>}
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">Consultando los próximos tres días…</p>}
    {batch && <>
      <ProducerAnswer batch={batch}>{actions}</ProducerAnswer>
      <h3 id="next-days-heading" className="producer-day-detail-heading">Detalle de cada día y tu opinión</h3>
      <p className="producer-day-detail-lead">Acá podés ver el resultado de cada día y contarnos si coincidió con lo que observaste en el cultivo.</p>
      <ul className="forecast-list forecast-outlook-grid">
        {batch.slots.map((slot) => <li key={slot.horizon_days}>
          {slot.status === "available" ? <ForecastCard key={slot.forecast_id} sensorId={sensorId} forecast={slot} onChanged={reviewed} /> : <article className="forecast-card">
            <h4>{slot.target_date ? displayForecastDate(slot.target_date) : `Día ${slot.horizon_days}`}</h4>
            <p><strong>Sin pronóstico disponible</strong></p>
            <p>{REASONS[slot.reason_code] ?? "No se pudo usar el pronóstico de este día. Es necesario revisar su configuración."}</p>
            <p>Esto no significa que no haya riesgo.</p>
          </article>}
        </li>)}
      </ul>
    </>}
  </section>;
}
