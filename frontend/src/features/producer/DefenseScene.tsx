import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { ForecastCard } from "./ForecastCard";
import { agreementLabel, displayForecastDate } from "./forecastsApi";
import type { Forecast, ForecastBatch, ForecastReview, ReviewRequest } from "./forecastsApi";
import type { SourceSummary } from "./HistoricalWalkthrough";
import "./DefenseScene.css";

export type SceneBatch =
  | { kind: "loading" }
  | { kind: "error"; message: string; onRetry: () => void }
  | { kind: "ready"; batch: ForecastBatch };

type AvailableSlot = Forecast & { status: "available" };

const HISTORICAL_NOTICE = "Revisión de prueba técnica en modo histórico: queda aislada del historial operativo real, no se incorpora a reentrenamiento ni recalibración.";
const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const REVIEW_TAGS = { pending: "pendiente", confirmed: "confirmada", rejected: "rechazada" } as const;

function shortDate(iso: string): string {
  const [, month, day] = iso.split("-").map(Number);
  return `${day} ${MONTHS[month - 1]}`;
}

function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000);
}

function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

function headline(emissionDate: string, slots: AvailableSlot[]): string {
  const date = displayForecastDate(emissionDate);
  if (slots.length === 0) return `${date} · No hay pronósticos disponibles para esta emisión`;
  const alerts = slots.filter((slot) => slot.alert).length;
  if (alerts === 0) {
    return slots.length === 3
      ? `${date} · Según los modelos, sin alerta de humedad baja en los 3 días siguientes`
      : `${date} · Según los modelos, sin alerta de humedad baja en ${slots.length} horizonte${slots.length === 1 ? "" : "s"} disponible${slots.length === 1 ? "" : "s"}`;
  }
  return `${date} · Según los modelos, alerta de humedad baja en ${alerts} de ${slots.length} horizonte${slots.length === 1 ? "" : "s"}`;
}

const ICON = { viewBox: "0 0 20 20", width: 18, height: 18, "aria-hidden": true, focusable: false } as const;

const TAB_LABELS = ["Cómo leer", "Datos y calidad", "Trazabilidad", "Observaciones"] as const;

/**
 * Escena de lectura rápida del recorrido histórico (modo defensa). Es presentacional: el estado, las
 * consultas y la revisión viven en `HistoricalWalkthrough`. No calcula si un pronóstico acertó ni
 * muestra probabilidades: presenta el veredicto del backend, el acuerdo entre los modelos y el dato real
 * revelado con su procedencia.
 */
export function DefenseScene({
  sourceSummary, availableDates, emissionDate, onEmissionChange, revealMax, effectiveReveal, onRevealChange,
  batch, chart, qualityLine, readingsNotice, describeRealValue, sensorId, submitReviewFn, refetchFn, onReviewed,
  provenanceNotice, qualityPanel, tracePanel, observationsPanel, thresholdText,
}: {
  sourceSummary: SourceSummary;
  availableDates: string[];
  emissionDate: string;
  onEmissionChange: (date: string) => void;
  revealMax: string;
  effectiveReveal: string;
  /** Cadena vacía = reloj en la fecha de emisión. */
  onRevealChange: (date: string) => void;
  batch: SceneBatch;
  chart: ReactNode;
  qualityLine: ReactNode;
  readingsNotice: ReactNode;
  describeRealValue: (targetDate: string) => string;
  sensorId: string;
  submitReviewFn: (sensorId: string, forecastId: string, request: ReviewRequest) => Promise<ForecastReview>;
  refetchFn: (sensorId: string, forecastId: string) => Promise<Forecast>;
  onReviewed: (forecast: Forecast) => void;
  provenanceNotice: ReactNode;
  qualityPanel: ReactNode;
  tracePanel: ReactNode;
  observationsPanel: ReactNode;
  /** Umbral del protocolo ya formateado, solo si el backend lo entrega con su unidad. */
  thresholdText: string | null;
}) {
  const slots = batch.kind === "ready" ? batch.batch.slots : [];
  const available = slots.filter((slot): slot is AvailableSlot => slot.status === "available");
  const context = `${emissionDate}|${effectiveReveal}`;
  const [pick, setPick] = useState<{ context: string; horizon: number } | null>(null);
  const revealedHorizons = available.filter((slot) => slot.target_date <= effectiveReveal).map((slot) => slot.horizon_days);
  const activeHorizon = pick && pick.context === context ? pick.horizon : (revealedHorizons.length ? Math.max(...revealedHorizons) : null);
  const activeSlot = available.find((slot) => slot.horizon_days === activeHorizon) ?? null;

  const maxDays = Math.max(0, daysBetween(emissionDate, revealMax));
  const clockDays = Math.max(0, Math.min(maxDays, daysBetween(emissionDate, effectiveReveal)));
  const clockText = clockDays === 0
    ? `Al emitir · ${displayForecastDate(emissionDate)}`
    : `+${clockDays} día${clockDays === 1 ? "" : "s"} · ${displayForecastDate(effectiveReveal)}`;

  const [tab, setTab] = useState(0);
  const tabsId = useId();
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  function onTabKey(event: KeyboardEvent<HTMLButtonElement>) {
    const last = TAB_LABELS.length - 1;
    const next = event.key === "ArrowRight" ? (tab === last ? 0 : tab + 1)
      : event.key === "ArrowLeft" ? (tab === 0 ? last : tab - 1)
        : event.key === "Home" ? 0 : event.key === "End" ? last : null;
    if (next === null) return;
    event.preventDefault();
    setTab(next);
    tabRefs.current[next]?.focus();
  }
  const tabPanels = [
    <p key="how">
      Cada celda bajo el gráfico es el pronóstico de un horizonte: «alerta» o «sin alerta», según los modelos, junto con
      el acuerdo entre modelos (cuántos de los 3 indican alerta). La alerta resume la evaluación conjunta de tres modelos con la información disponible hasta la fecha de emisión;
      no es una explicación de causas ni depende solo del último dato. Al mover el reloj se revela
      el dato real de cada día; nunca se muestran datos posteriores. La revisión es tu opinión sobre si el resultado coincidió con lo que observaste.
    </p>,
    <div key="quality">{provenanceNotice}{qualityPanel}</div>,
    <div key="trace">{tracePanel}</div>,
    <div key="obs">{observationsPanel}</div>,
  ];

  return (
    <section className="defense-scene" aria-labelledby="defense-scene-title">
      <div className="ds-chips">
        <span className="ds-chip">{sourceSummary.label} · {sourceSummary.detail}</span>
      </div>

      <h2 id="defense-scene-title" className="ds-title">
        {batch.kind === "ready" ? headline(emissionDate, available) : `Recorrido histórico · ${displayForecastDate(emissionDate)}`}
      </h2>
      <p className="ds-sub">
        {thresholdText && <><strong>Alerta</strong> = los modelos evalúan que la humedad del suelo quede por debajo de {thresholdText} (umbral relativo: percentil 20 del entrenamiento). </>}
        Se reproduce una emisión guardada; este recorrido no genera pronósticos nuevos.
      </p>

      <div className="ds-emission" role="group" aria-label="Emisión (cuándo se hizo el pronóstico)">
        {availableDates.map((date) => (
          <button key={date} type="button" aria-pressed={date === emissionDate} onClick={() => onEmissionChange(date)}>
            {shortDate(date)}
          </button>
        ))}
      </div>

      {batch.kind === "loading" && <p role="status">Cargando emisión histórica…</p>}
      {batch.kind === "error" && (
        <p role="alert">No se pudo consultar la emisión: {batch.message} <button type="button" onClick={batch.onRetry}>Reintentar emisión</button></p>
      )}

      <div className="ds-scene">
        <div className="ds-chart">{chart}</div>
        {batch.kind === "ready" && (
          <div className="ds-strip" role="group" aria-label="Pronóstico por horizonte (seleccionar uno para revisarlo)">
            {slots.map((slot) => {
              if (slot.status !== "available") {
                return (
                  <div key={slot.horizon_days} className="ds-cell ds-cell--na">
                    <small>+{slot.horizon_days}{slot.target_date ? ` · ${displayForecastDate(slot.target_date)}` : ""}</small>
                    <strong>Sin pronóstico disponible</strong>
                  </div>
                );
              }
              const revealed = slot.target_date <= effectiveReveal;
              const votes = slot.ensemble && slot.ensemble.components.length === 3 ? agreementLabel(slot.ensemble) : null;
              return (
                <button
                  key={slot.horizon_days}
                  type="button"
                  className={`ds-cell ${slot.alert ? "ds-cell--alert" : "ds-cell--clear"}`}
                  aria-pressed={slot.horizon_days === activeHorizon}
                  onClick={() => setPick({ context, horizon: slot.horizon_days })}
                >
                  <small>+{slot.horizon_days} · {displayForecastDate(slot.target_date)}</small>
                  <strong>
                    {slot.alert
                      ? <svg {...ICON}><path d="M10 2.500 18.500 17h-17z" fill="currentColor" /></svg>
                      : <svg {...ICON}><circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="2.200" /></svg>}
                    {" "}{slot.alert ? "Alerta" : "Sin alerta"}
                  </strong>
                  {votes && <span className="ds-votes">{votes}</span>}
                  {revealed && <span className={`ds-tag ds-tag--${slot.review.status}`}>Revisión: {REVIEW_TAGS[slot.review.status]}</span>}
                </button>
              );
            })}
          </div>
        )}
        <div className="ds-clock">
          <label htmlFor={`${tabsId}-clock`}>
            <span>Reloj del recorrido</span>
            <span className="ds-clock-value">{clockText}</span>
          </label>
          <input
            id={`${tabsId}-clock`}
            type="range"
            min={0}
            max={maxDays}
            step={1}
            value={clockDays}
            aria-valuetext={clockText}
            onChange={(event) => {
              const days = Number(event.target.value);
              onRevealChange(days <= 0 ? "" : addDays(emissionDate, days));
            }}
          />
          <p className="ds-clock-hint">Se revelan los datos reales hasta la fecha del reloj.</p>
        </div>
      </div>

      {readingsNotice}
      {qualityLine}

      {batch.kind === "ready" && (
        <section className="ds-review" aria-labelledby={`${tabsId}-review`}>
          {activeSlot ? (
            <>
              <h3 id={`${tabsId}-review`}>Tu revisión · +{activeSlot.horizon_days} día{activeSlot.horizon_days === 1 ? "" : "s"} ({displayForecastDate(activeSlot.target_date)})</h3>
              {activeSlot.target_date <= effectiveReveal
                ? <p className="ds-real">Dato real revelado: {describeRealValue(activeSlot.target_date)}</p>
                : <p className="ds-real">Todavía no se puede revisar este resultado: avanzá el reloj hasta el {displayForecastDate(activeSlot.target_date)}.</p>}
              <ForecastCard
                key={activeSlot.forecast_id}
                sensorId={sensorId}
                forecast={activeSlot}
                onChanged={onReviewed}
                submitReviewFn={submitReviewFn}
                refetchFn={refetchFn}
                historicalNotice={HISTORICAL_NOTICE}
                compact
              />
            </>
          ) : (
            <>
              <h3 id={`${tabsId}-review`}>Tu revisión</h3>
              <p className="ds-real">Seleccionar un horizonte (+1, +2 o +3) para ver su resultado. Cuando el reloj llegue a ese día se podrá confirmar o rechazar.</p>
            </>
          )}
        </section>
      )}

      <p className="ds-limit">
        Apoyo a la decisión, no automatización del riego. «Sin alerta» no garantiza ausencia de estrés en el cultivo.
      </p>

      <div className="ds-tabs" role="tablist" aria-label="Detalles">
        {TAB_LABELS.map((label, index) => (
          <button
            key={label}
            ref={(element) => { tabRefs.current[index] = element; }}
            id={`${tabsId}-tab-${index}`}
            role="tab"
            type="button"
            aria-selected={tab === index}
            aria-controls={`${tabsId}-panel`}
            tabIndex={tab === index ? 0 : -1}
            onClick={() => setTab(index)}
            onKeyDown={onTabKey}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="ds-panel" role="tabpanel" id={`${tabsId}-panel`} aria-labelledby={`${tabsId}-tab-${tab}`}>
        {tabPanels[tab]}
      </div>
    </section>
  );
}
