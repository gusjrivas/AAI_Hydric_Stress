/**
 * Nombre legible de un punto de medición para quien no conoce los identificadores técnicos.
 * Si el punto está registrado con un nombre propio, se respeta; los puntos de las demostraciones
 * (que el catálogo devuelve con el identificador como nombre) usan el nombre del sitio.
 */
const DEMO_SITE_LABELS: Record<string, string> = {
  "pergamino-ensemble-demo": "Pergamino · demostración",
  "melchor-romero-demo": "Melchor Romero · demostración",
};

function humanize(sensorId: string): string {
  const spaced = sensorId.replace(/[-_]+/g, " ").trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : sensorId;
}

export function sensorLabel(sensor: { sensor_id: string; display_name: string; registered?: boolean }): string {
  const named = sensor.display_name && sensor.display_name !== sensor.sensor_id;
  if (named) return sensor.display_name;
  return DEMO_SITE_LABELS[sensor.sensor_id] ?? humanize(sensor.sensor_id);
}
