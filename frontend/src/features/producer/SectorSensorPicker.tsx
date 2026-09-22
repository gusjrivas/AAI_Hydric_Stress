import { useEffect, useState } from "react";
import { listSectors, listSensors, ProducerV2UnavailableError } from "./catalogApi";
import type { Sector, SensorSummary } from "./catalogApi";

type SectorsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; sectors: Sector[] };

type SensorsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; sensors: SensorSummary[] };

const ALL_SECTORS = "";

/**
 * Selección de sector y punto de medición contra el catálogo v2. Una
 * respuesta atrasada de un sector previamente elegido no debe reemplazar la
 * lista del sector actualmente seleccionado (requerimiento de la entrega).
 */
export function SectorSensorPicker({
  onSelect,
}: {
  onSelect: (sensor: SensorSummary | null) => void;
}) {
  const [sectorsState, setSectorsState] = useState<SectorsState>({ status: "loading" });
  const [sectorRetry, setSectorRetry] = useState(0);
  const [sectorId, setSectorId] = useState<string>(ALL_SECTORS);

  const [sensorsState, setSensorsState] = useState<SensorsState>({ status: "loading" });
  const [sensorRetry, setSensorRetry] = useState(0);
  const [sensorId, setSensorId] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    setSectorsState({ status: "loading" });
    listSectors().then(
      (result) => {
        if (cancelled) return;
        setSectorsState({ status: "ready", sectors: result.items });
      },
      (error: Error) => {
        if (cancelled) return;
        const message =
          error instanceof ProducerV2UnavailableError
            ? error.message
            : `${error.message} No se pudieron cargar los sectores.`;
        setSectorsState({ status: "error", message });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [sectorRetry]);

  useEffect(() => {
    let cancelled = false;
    const requestSectorId = sectorId;
    const previousSensorId = sensorId;
    setSensorsState({ status: "loading" });
    listSensors(requestSectorId || undefined).then(
      (result) => {
        // Ignorar una respuesta de un sector que ya no es el elegido.
        if (cancelled) return;
        setSensorsState({ status: "ready", sensors: result.items });
        const stillValid = result.items.some((sensor) => sensor.sensor_id === previousSensorId);
        if (stillValid) return;
        const sectorInfo =
          sectorsState.status === "ready"
            ? sectorsState.sectors.find((sector) => sector.sector_id === requestSectorId)
            : undefined;
        const preferred =
          result.items.find((sensor) => sensor.sensor_id === sectorInfo?.primary_sensor_id) ??
          (result.items.length === 1 ? result.items[0] : undefined);
        setSensorId(preferred?.sensor_id ?? "");
      },
      (error: Error) => {
        if (cancelled) return;
        const message =
          error instanceof ProducerV2UnavailableError
            ? error.message
            : `${error.message} No se pudieron cargar los puntos de medición.`;
        setSensorsState({ status: "error", message });
      },
    );
    return () => {
      cancelled = true;
    };
    // sensorId y sectorsState se leen como valores de referencia (sensor
    // elegido y sectores ya cargados al momento del cambio de sector); no
    // disparan un nuevo pedido por sí solos.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectorId, sensorRetry]);

  useEffect(() => {
    if (sensorsState.status !== "ready") {
      onSelect(null);
      return;
    }
    onSelect(sensorsState.sensors.find((sensor) => sensor.sensor_id === sensorId) ?? null);
  }, [sensorId, sensorsState, onSelect]);

  return (
    <div className="producer-picker">
      <div className="producer-picker-field">
        <label htmlFor="producer-sector-select">Tu sector</label>
        {sectorsState.status === "loading" && <p role="status">Cargando sectores…</p>}
        {sectorsState.status === "error" && (
          <p role="alert">
            {sectorsState.message}{" "}
            <button type="button" onClick={() => setSectorRetry((n) => n + 1)}>
              Reintentar sectores
            </button>
          </p>
        )}
        {sectorsState.status === "ready" && (
          <select
            id="producer-sector-select"
            value={sectorId}
            onChange={(event) => setSectorId(event.target.value)}
          >
            <option value={ALL_SECTORS}>Todos los sectores</option>
            {sectorsState.sectors.map((sector) => (
              <option key={sector.sector_id} value={sector.sector_id}>
                {sector.display_name}
                {sector.crop ? ` · ${sector.crop}` : ""}
              </option>
            ))}
          </select>
        )}
        {sectorsState.status === "ready" && sectorsState.sectors.length === 0 && (
          <p>Todavía no hay sectores registrados. Podés elegir un punto de medición igualmente.</p>
        )}
      </div>

      <div className="producer-picker-field">
        <label htmlFor="producer-sensor-select">Punto de medición</label>
        {sensorsState.status === "loading" && <p role="status">Cargando puntos de medición…</p>}
        {sensorsState.status === "error" && (
          <p role="alert">
            {sensorsState.message}{" "}
            <button type="button" onClick={() => setSensorRetry((n) => n + 1)}>
              Reintentar puntos de medición
            </button>
          </p>
        )}
        {sensorsState.status === "ready" && sensorsState.sensors.length === 0 && (
          <p role="status">No hay puntos de medición para este sector.</p>
        )}
        {sensorsState.status === "ready" && sensorsState.sensors.length > 0 && (
          <select
            id="producer-sensor-select"
            value={sensorId}
            onChange={(event) => setSensorId(event.target.value)}
          >
            <option value="" disabled>
              Elegí un punto de medición
            </option>
            {sensorsState.sensors.map((sensor) => (
              <option key={sensor.sensor_id} value={sensor.sensor_id}>
                {sensor.display_name}
                {sensor.source_kind === "synthetic" ? " · Simulado" : ""}
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}
