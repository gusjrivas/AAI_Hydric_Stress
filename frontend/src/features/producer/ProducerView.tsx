import { useCallback, useState } from "react";
import { SectorSensorPicker } from "./SectorSensorPicker";
import { ProducerHistoryPanel } from "./ProducerHistoryPanel";
import { EmissionPanel } from "./EmissionPanel";
import { ForecastReviewsProvider } from "./ForecastReviewsContext";
import { ProducerTabs, PRODUCER_TAB_LABELS } from "./ProducerTabs";
import type { ProducerTab } from "./ProducerTabs";
import { ProducerHistoryScreen } from "./ProducerHistoryScreen";
import { ProducerDataScreen } from "./ProducerDataScreen";
import { alertOutlookSummary } from "./forecastsApi";
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

  return (
    <div className="producer-view">
      <header className="producer-header">
        <div className="producer-header-left">
          <span className="producer-brand" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="22" height="22"><path d="M16 3c5.5 7 9 11.5 9 16a9 9 0 0 1-18 0c0-4.5 3.5-9 9-16z" fill="#1F6FB2" /></svg>
            Cultiv<em>IA</em>
          </span>
          {sensor && <ProducerTabs active={tab} onSelect={setTab} />}
        </div>
        <div className="producer-header-right">
          <SectorSensorPicker onSelect={handleSelect} />
        </div>
      </header>
      {sensor && <div className="producer-context-caption">
        <span>Estás viendo <strong>{sensor.display_name}</strong></span>
        {sensor.source_kind === "synthetic" && <span className="producer-sensor-tag">Datos simulados</span>}
        {sensor.source_kind === "unknown" && <span className="producer-sensor-tag">Procedencia sin declarar</span>}
      </div>}

      {sensor ? <>
        <section className="producer-hero-heading" aria-labelledby="producer-tab-heading">
          <h1 id="producer-tab-heading">{PRODUCER_TAB_LABELS[tab]}</h1>
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
        <h3>Empezá por tu sector</h3>
        <p>Elegí un punto de medición para ver su historial y sus pronósticos.</p>
      </div>}
      <footer className="producer-footnote">Una ayuda para observar y decidir. No indica cuánto ni cuándo regar.</footer>
    </div>
  );
}
