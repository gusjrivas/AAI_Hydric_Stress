import { useCallback, useState } from "react";
import { SectorSensorPicker } from "./SectorSensorPicker";
import { ProducerHistoryPanel } from "./ProducerHistoryPanel";
import { EmissionPanel } from "./EmissionPanel";
import { ForecastsSection } from "./ForecastsSection";
import { ForecastReviewsProvider } from "./ForecastReviewsContext";
import type { SensorSummary } from "./catalogApi";
import "./ProducerView.css";

export function ProducerView() {
  const [forecastRefresh, setForecastRefresh] = useState(0);
  const [sensor, setSensor] = useState<SensorSummary | null>(null);
  const handleSelect = useCallback((selected: SensorSummary | null) => setSensor(selected), []);
  return (
    <div className="producer-view">
      <header className="producer-hero">
        <div>
          <p className="producer-eyebrow">TU CULTIVO, MÁS CLARO</p>
          <h3>Cuidar empieza por observar.</h3>
          <p>Las mediciones y los próximos días, en un solo lugar. Tu mirada en el campo completa la información.</p>
        </div>
        <div className="producer-hero-art" aria-hidden="true">
          <svg viewBox="0 0 180 150"><path d="M20 125 Q85 95 160 125 M20 140 Q90 110 160 140"/><path d="M90 120 V60"/><path d="M90 90 C40 95 35 45 35 45 C80 40 95 65 90 90Z"/><path d="M90 72 C135 76 150 22 150 22 C105 20 85 45 90 72Z"/><circle cx="38" cy="23" r="13"/></svg>
        </div>
      </header>
      <div className="producer-context">
        <p className="producer-eyebrow">01 / ELEGÍ DÓNDE MIRAR</p>
        <SectorSensorPicker onSelect={handleSelect} />
        {sensor && <div className="producer-context-caption">
          <span>Estás viendo <strong>{sensor.display_name}</strong></span>
          {sensor.source_kind === "synthetic" && <span className="producer-sensor-tag">Datos simulados</span>}
          {sensor.source_kind === "unknown" && <span className="producer-sensor-tag">Procedencia sin declarar</span>}
        </div>}
      </div>
      {sensor ? <ForecastReviewsProvider key={sensor.sensor_id}>
        <EmissionPanel sensorId={sensor.sensor_id} onChanged={() => setForecastRefresh((value) => value + 1)} />
        <div className="producer-section-label"><span>03 / TUS MEDICIONES</span><span>Lo que ya pasó</span></div>
        <ProducerHistoryPanel sensorId={sensor.sensor_id} />
        <ForecastsSection key={`${sensor.sensor_id}:${forecastRefresh}`} sensorId={sensor.sensor_id} />
      </ForecastReviewsProvider> : <div className="producer-empty" role="status">
        <h3>Empezá por tu sector</h3>
        <p>Elegí un punto de medición para ver su historial y sus pronósticos.</p>
      </div>}
      <footer className="producer-footnote">Una ayuda para observar y decidir. No indica cuánto ni cuándo regar.</footer>
    </div>
  );
}