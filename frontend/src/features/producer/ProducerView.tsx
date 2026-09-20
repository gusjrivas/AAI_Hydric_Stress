import { useCallback, useState } from "react";
import { SectorSensorPicker } from "./SectorSensorPicker";
import { ProducerHistoryPanel } from "./ProducerHistoryPanel";
import type { SensorSummary } from "./catalogApi";
import "./ProducerView.css";

/**
 * Primera entrega de la UI orientada al productor (HU6): selección de
 * sector/sensor contra el catálogo v2 y visualización de sus mediciones
 * históricas. Los pronósticos v2 todavía no están integrados aquí.
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
        <ProducerHistoryPanel sensorId={sensor.sensor_id} />
      ) : (
        <p role="status">Elegí un punto de medición para ver su historial.</p>
      )}

      <section className="producer-forecast-note" aria-label="Estado del pronóstico">
        <h3>Pronóstico</h3>
        <p>
          Los pronósticos del catálogo v2 todavía no están integrados en esta pantalla. Para
          consultar un pronóstico ya emitido, usá la sección «Resumen» con el identificador del
          sensor.
        </p>
      </section>
    </div>
  );
}
