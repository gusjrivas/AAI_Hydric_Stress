import { useCallback, useState } from "react";
import { SectorSensorPicker } from "./SectorSensorPicker";
import { ProducerHistoryPanel } from "./ProducerHistoryPanel";
import { EmissionPanel } from "./EmissionPanel";
import { ForecastReviewsProvider } from "./ForecastReviewsContext";
import { ProducerTabs, PRODUCER_TAB_LABELS } from "./ProducerTabs";
import type { ProducerTab } from "./ProducerTabs";
import { ProducerHistoryScreen } from "./ProducerHistoryScreen";
import { ProducerDataScreen } from "./ProducerDataScreen";
import { sensorLabel } from "./sensorLabels";
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
  const handleSelect = useCallback((selected: SensorSummary | null) => {
    setSensor(selected);
  }, []);

  return (
    <div className="producer-view">
      <header className="producer-page-head">
        <p className="producer-eyebrow">Mi cultivo · seguimiento en vivo</p>
        <h1 id="productor-heading" tabIndex={-1}>Mi cultivo</h1>
        <p className="producer-lead">¿Habrá falta de agua en los próximos días? Elegí tu lote y mirá qué se espera.</p>
      </header>
      <section className="producer-picker-card" aria-label="Sector y punto de medición">
        <SectorSensorPicker onSelect={handleSelect} />
      </section>
      {sensor && <div className="producer-context-caption">
        <span>Estás viendo <strong>{sensorLabel(sensor)}</strong></span>
        {sensor.source_kind === "synthetic" && <span className="producer-sensor-tag is-sim">Datos simulados</span>}
        {sensor.source_kind === "unknown" && <span className="producer-sensor-tag is-unknown">Origen de los datos sin declarar</span>}
      </div>}
      {sensor && <ProducerTabs active={tab} onSelect={setTab} />}

      {sensor ? <>
        <section className="producer-hero-heading" aria-labelledby="producer-tab-heading">
          <h2 id="producer-tab-heading">{PRODUCER_TAB_LABELS[tab]}</h2>
          <p>{TAB_SUBTITLES[tab]}</p>
        </section>

        {tab === "cultivo" && <ForecastReviewsProvider key={sensor.sensor_id}>
          <div className="producer-cultivo-grid">
            <div className="producer-cultivo-main">
              <EmissionPanel sensorId={sensor.sensor_id} onChanged={() => {}} />
              <ProducerHistoryPanel sensorId={sensor.sensor_id} />
            </div>
            <aside className="producer-cultivo-aside">
              <div className="producer-tip-box">
                <p className="producer-tip-title">Cómo leer esta pantalla</p>
                <ul className="producer-tip-list">
                  <li><strong>Alerta prevista:</strong> conviene revisar el cultivo por una posible falta de agua.</li>
                  <li><strong>Sin alerta prevista:</strong> no garantiza que el cultivo esté en buenas condiciones. Revisalo igual.</li>
                  <li><strong>Sin pronóstico:</strong> no hay información para ese día. Eso no significa que no haya riesgo.</li>
                  <li><strong>Acuerdo entre modelos:</strong> de 3 revisiones automáticas, cuántas indican alerta. No es una probabilidad ni un porcentaje de riesgo.</li>
                  <li>Esta herramienta no indica cuánto ni cuándo regar.</li>
                </ul>
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
