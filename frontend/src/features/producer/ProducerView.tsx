import { useCallback, useState } from "react";
import { SectorSensorPicker } from "./SectorSensorPicker";
import { ProducerHistoryPanel } from "./ProducerHistoryPanel";
import { ForecastsSection } from "./ForecastsSection";
import type { SensorSummary } from "./catalogApi";
import "./ProducerView.css";

/**
 * UI orientada al productor (HU6): selección de sector/sensor contra el
 * catálogo v2, mediciones históricas y consulta/revisión de pronósticos.
 */
export function ProducerView() {
  const [sensor, setSensor] = useState<SensorSummary | null>(null);
  const handleSelect = useCallback((selected: SensorSummary | null) => {
    setSensor(selected);
  }, []);

  return (
    <div className="producer-view">
      <p>Elegí tu sector y el punto de medición para ver cómo cambió la humedad del suelo.</p>
      <SectorSensorPicker onSelect={handleSelect} />

      {sensor && (
        <p>
          Mostrando <strong>{sensor.display_name}</strong>
          {sensor.source_kind === "synthetic" && (
            <span className="producer-sensor-tag">Datos simulados</span>
          )}
          {sensor.source_kind === "unknown" && (
            <span className="producer-sensor-tag">Procedencia sin declarar</span>
          )}
        </p>
      )}

      {sensor ? (
        <>
          <ProducerHistoryPanel sensorId={sensor.sensor_id} />
          <ForecastsSection sensorId={sensor.sensor_id} />
        </>
      ) : (
        <p role="status">Elegí un punto de medición para ver su historial y sus pronósticos.</p>
      )}
    </div>
  );
}
