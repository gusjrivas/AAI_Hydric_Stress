import { useCallback, useState } from "react";
import { SectorSensorPicker } from "./SectorSensorPicker";
import { ProducerHistoryPanel } from "./ProducerHistoryPanel";
import { EmissionPanel } from "./EmissionPanel";
import { ForecastReviewsProvider } from "./ForecastReviewsContext";
import { ProducerTabs, PRODUCER_TAB_LABELS } from "./ProducerTabs";
import type { ProducerTab } from "./ProducerTabs";
import { ProducerHistoryScreen } from "./ProducerHistoryScreen";
import { ProducerDataScreen } from "./ProducerDataScreen";
import { alertOutlookSummary, displayForecastDate } from "./forecastsApi";
import { provenanceLabel } from "./readingsApi";
import { FactsStrip } from "../shared/FactsStrip";
import type { Fact } from "../shared/FactsStrip";
import type { ForecastBatch } from "./forecastsApi";
import type { SensorSummary } from "./catalogApi";
import "./ProducerView.css";

const TAB_SUBTITLES: Record<ProducerTab, string> = {
  cultivo: "Cómo está el suelo hoy y qué esperar en los próximos días.",
  historial: "Los pronósticos de días que ya pasaron y lo que registraste en el cultivo.",
  datos: "Revisá qué datos hay y si faltan mediciones.",
};

export function ProducerView() {
  const [sensor, setSensor] = useState<SensorSummary | null>(null);
  const [tab, setTab] = useState<ProducerTab>("cultivo");
  const [batch, setBatch] = useState<ForecastBatch | null>(null);
  const handleSelect = useCallback((selected: SensorSummary | null) => {
    setSensor(selected);
    setBatch(null);
  }, []);
  const outlook = batch ? alertOutlookSummary(batch) : null;

  const targets = batch ? batch.slots.map((slot) => slot.target_date).filter((date): date is string => !!date).sort() : [];
  const facts: Fact[] | null = batch ? [
    { label: "Datos que se ven", value: provenanceLabel(batch.provenance), sub: sensor?.display_name },
    { label: "Pronóstico emitido", value: batch.as_of_date ? displayForecastDate(batch.as_of_date) : "No disponible", sub: "con la última medición disponible" },
    { label: "Aplica para", value: targets.length ? (targets.length > 1 ? `${displayForecastDate(targets[0])} – ${displayForecastDate(targets[targets.length - 1])}` : displayForecastDate(targets[0])) : "No disponible", sub: "horizontes +1, +2 y +3 días" },
    { label: "Antigüedad de los datos", value: batch.data_age_days === null ? "No disponible" : `${batch.data_age_days} día${batch.data_age_days === 1 ? "" : "s"}`, sub: "desde la última medición" },
  ] : null;

  return (
    <div className="producer-view">
      <header className="producer-page-head">
        <p className="producer-eyebrow">Mi cultivo · seguimiento en vivo</p>
        <h1 id="productor-heading" tabIndex={-1}>Mi cultivo</h1>
        <p className="producer-lead">Elegí tu sector y punto de medición para ver el pronóstico, el historial y los datos disponibles.</p>
      </header>
      <section className="producer-picker-card" aria-label="Sector y punto de medición">
        <SectorSensorPicker onSelect={handleSelect} />
      </section>
      {sensor && <div className="producer-context-caption">
        <span>Estás viendo <strong>{sensor.display_name}</strong></span>
        {sensor.source_kind === "synthetic" && <span className="producer-sensor-tag is-sim">Datos simulados</span>}
        {sensor.source_kind === "unknown" && <span className="producer-sensor-tag is-unknown">Procedencia sin declarar</span>}
      </div>}
      {sensor && <ProducerTabs active={tab} onSelect={setTab} />}

      {sensor ? <>
        {tab === "cultivo" && facts && <FactsStrip facts={facts} />}
        <section className="producer-hero-heading" aria-labelledby="producer-tab-heading">
          <h2 id="producer-tab-heading">{PRODUCER_TAB_LABELS[tab]}</h2>
          <p>{TAB_SUBTITLES[tab]}</p>
        </section>

        {tab === "cultivo" && outlook && (
          <section className={`producer-alert-banner ${outlook.alert ? "is-alert" : ""}`}>
            <span className={`producer-alert-badge ${outlook.alert ? "is-alert" : ""}`}>
              <span className="producer-alert-dot" aria-hidden="true" />
              {outlook.alert ? "Requiere atención" : "Sin alerta próxima"}
            </span>
            <p>
              {outlook.alert
                ? `Posible falta de agua: ${outlook.days.join(", ")}.`
                : "Ningún horizonte disponible anticipa alerta por ahora. Esto no reemplaza revisar el cultivo."}
            </p>
          </section>
        )}

        {tab === "cultivo" && <ForecastReviewsProvider key={sensor.sensor_id}>
          <div className="producer-cultivo-grid">
            <div className="producer-cultivo-main">
              <EmissionPanel sensorId={sensor.sensor_id} onChanged={() => {}} onBatch={setBatch} />
              <ProducerHistoryPanel sensorId={sensor.sensor_id} />
            </div>
            <aside className="producer-cultivo-aside">
              <div className="producer-tip-box">
                <p className="producer-tip-title">Cómo leer esta pantalla</p>
                <p>
                  El acuerdo entre modelos es la cantidad de los 3 modelos que indican alerta para ese día — no es
                  una probabilidad ni un porcentaje de riesgo. La alerta combinada es la decisión de nivel superior;
                  el acuerdo es información adicional sobre cuánto coinciden los modelos.
                </p>
              </div>
            </aside>
          </div>
        </ForecastReviewsProvider>}
        {tab === "historial" && <ProducerHistoryScreen sensorId={sensor.sensor_id} />}
        {tab === "datos" && <ProducerDataScreen sensorId={sensor.sensor_id} />}
      </> : <div className="producer-empty" role="status">
        <h2>Empezá por tu sector</h2>
        <p>Elegí un punto de medición para ver su historial y sus pronósticos.</p>
      </div>}
      <footer className="producer-footnote">Una ayuda para observar y decidir. No indica cuánto ni cuándo regar.</footer>
    </div>
  );
}
