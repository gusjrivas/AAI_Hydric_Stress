import type { ReactNode } from "react";
import type { ForecastBatch } from "./forecastsApi";
import { describeOutlook, staleNotice } from "./producerOutlook";
import type { DayState } from "./producerOutlook";
import { provenanceLabel } from "./readingsApi";
import { displayForecastDate } from "./forecastsApi";
import "./ProducerAnswer.css";

const STATE_TEXT: Record<DayState, string> = { alert: "Posible falta de agua", clear: "Sin alerta", none: "Sin pronóstico" };

const ICON = { viewBox: "0 0 20 20", width: 20, height: 20, "aria-hidden": true, focusable: false } as const;
function StateIcon({ state }: { state: DayState }) {
  if (state === "alert") return <svg {...ICON}><path d="M10 2.500 18.500 17h-17z" fill="currentColor" /><path d="M10 8v4.200M10 14.200v.6" stroke="#fff" strokeWidth="1.800" strokeLinecap="round" /></svg>;
  if (state === "clear") return <svg {...ICON}><circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="2.200" /></svg>;
  return <svg {...ICON}><circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="3 2.400" /><path d="M5.500 14.500l9-9" stroke="currentColor" strokeWidth="2" /></svg>;
}

/**
 * Respuesta principal de «Mi cultivo» para quien no conoce la jerga: una frase clara, los próximos tres días
 * de un vistazo y de dónde salen los datos. Los detalles técnicos quedan en la tarjeta de cada día.
 */
export function ProducerAnswer({ batch, children }: { batch: ForecastBatch; children?: ReactNode }) {
  const outlook = describeOutlook(batch);
  const stale = staleNotice(batch);
  return (
    <section className={`pa pa--${outlook.tone}`} aria-labelledby="pa-headline">
      <p className="pa-eyebrow">Próximos 3 días</p>
      <h3 id="pa-headline" className="pa-headline">{outlook.headline}</h3>
      <p className="pa-detail">{outlook.detail}</p>
      <ul className="pa-days" aria-label="Los próximos tres días">
        {outlook.days.map((day) => (
          <li key={day.horizon} className={`pa-day pa-day--${day.state}`}>
            <span className="pa-day-when">{day.label}</span>
            <span className="pa-day-state"><StateIcon state={day.state} />{STATE_TEXT[day.state]}</span>
          </li>
        ))}
      </ul>
      {stale && <p className="pa-stale" role="status">{stale}</p>}
      <p className="pa-source">
        {batch.as_of_date && <>Con mediciones hasta el <strong>{displayForecastDate(batch.as_of_date)}</strong>. </>}
        <span className="pa-provenance">{provenanceLabel(batch.provenance)}</span>
      </p>
      {children}
    </section>
  );
}
