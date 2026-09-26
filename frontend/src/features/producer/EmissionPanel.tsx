import { useEffect, useRef, useState } from "react";
import { ForecastCard } from "./ForecastCard";
import { displayForecastDate, emitForecasts, newRequestId } from "./forecastsApi";
import type { Forecast, ForecastBatch } from "./forecastsApi";
import { provenanceLabel } from "./readingsApi";

const REASONS: Record<string, string> = {
  no_readings: "Todavía no hay mediciones para este punto.",
  model_not_available: "Todavía no hay un pronóstico preparado para este día.",
  insufficient_data: "Faltan mediciones recientes para estimar este día.",
  incompatible_units: "Las unidades de las mediciones necesitan una revisión.",
  model_not_available_at_date: "Las mediciones son anteriores al período que puede usar este pronóstico.",
};

export function EmissionPanel({
  sensorId,
  onChanged,
  onBatch,
}: {
  sensorId: string;
  onChanged: () => void;
  /** Notifica el lote vigente al contenedor (p. ej. para el banner de
   * alerta resumen en la parte superior de la pantalla) sin duplicar el
   * estado: sigue siendo este componente el único que lo posee. */
  onBatch?: (batch: ForecastBatch | null) => void;
}) {
  const [batch, setBatch] = useState<ForecastBatch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef<string | null>(null);
  const alive = useRef(false);
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);
  useEffect(() => {
    // Consulta automática al entrar a la pantalla: es la misma emisión
    // idempotente por (sensor, fecha) que dispara el botón, así que no
    // repite inferencia si ya se generó hoy. Prioriza mostrar estado sobre
    // exigir un gesto manual, sin cambiar la semántica de la ruta.
    void generate();
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
      setBatch(result);
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
  return <section className="producer-outlook" aria-labelledby="next-days-heading">
    <p className="producer-eyebrow">PRÓXIMOS 3 DÍAS</p>
    <h3 id="next-days-heading">Los próximos tres días del cultivo</h3>
    <p>Consultá qué se espera para cada día a partir de la última medición disponible.</p>
    <button type="button" disabled={busy} onClick={() => void generate()}>
      {busy ? "Preparando pronósticos…" : error ? "Reintentar consulta" : batch ? "Actualizar" : "Consultar próximos tres días"}
    </button>
    {error && <p role="alert">{error}</p>}
    {!batch && !error && <p role="status">Consultando los próximos tres días…</p>}
    {batch && <>
      <p className="producer-provenance">{provenanceLabel(batch.provenance)}</p>
      {batch.as_of_date && <p>Mediciones hasta el <strong>{displayForecastDate(batch.as_of_date)}</strong>. Fechas en UTC.</p>}
      {batch.data_age_days !== null && batch.data_age_days > 0 && <p role="status">
        La última medición tiene {batch.data_age_days} días de antigüedad. Los resultados corresponden a esas fechas; no describen necesariamente la situación de hoy.
      </p>}
      {batch.slots.every((slot) => slot.status === "unavailable") && (
        <p role="alert" className="producer-insufficient-data">
          No hay información suficiente para emitir un pronóstico. Se recomienda verificar el estado del cultivo.
        </p>
      )}
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
