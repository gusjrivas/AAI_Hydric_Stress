import type { ReplayHistoryRow } from "./api";

const WIDTH = 480;
const HEIGHT = 120;
const PADDING = 8;
const AXIS_MARGIN_LEFT = 44;
const AXIS_MARGIN_BOTTOM = 18;
const PLOT_WIDTH = WIDTH - AXIS_MARGIN_LEFT - PADDING;
const PLOT_HEIGHT = HEIGHT - AXIS_MARGIN_BOTTOM - PADDING;

/**
 * Serie de humedad limitada al reloj simulado. Los huecos (`soil_moisture:
 * null`) se preservan como cortes reales del trazo — nunca se interpolan ni
 * se unen con el punto siguiente, para no presentar un faltante como si
 * fuera una medición observada (Paso 4 §3).
 */
export function MoistureHistoryChart({ rows }: { rows: ReplayHistoryRow[] }) {
  if (rows.length === 0) {
    return (
      <p role="status" className="hr-chart-empty">
        Todavía no hay historial disponible hasta la fecha simulada.
      </p>
    );
  }

  const values = rows.map((row) => row.soil_moisture).filter((v): v is number => v !== null);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const range = max - min || 1;

  const stepX = rows.length > 1 ? PLOT_WIDTH / (rows.length - 1) : 0;

  function toXY(index: number, value: number): [number, number] {
    const x = AXIS_MARGIN_LEFT + index * stepX;
    const y = PADDING + PLOT_HEIGHT - ((value - min) / range) * PLOT_HEIGHT;
    return [x, y];
  }

  // Agrupa en segmentos contiguos de valores no nulos; cada hueco corta el
  // segmento en vez de saltarlo con una línea recta engañosa.
  const segments: [number, number][][] = [];
  let current: [number, number][] = [];
  rows.forEach((row, index) => {
    if (row.soil_moisture === null) {
      if (current.length) segments.push(current);
      current = [];
      return;
    }
    current.push(toXY(index, row.soil_moisture));
  });
  if (current.length) segments.push(current);

  const gapCount = rows.filter((row) => row.soil_moisture === null).length;

  return (
    <figure className="hr-chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Historial de humedad de suelo, con huecos donde no hay medición">
        <line
          className="hr-chart-axis"
          x1={AXIS_MARGIN_LEFT}
          y1={PADDING}
          x2={AXIS_MARGIN_LEFT}
          y2={PADDING + PLOT_HEIGHT}
        />
        <line
          className="hr-chart-axis"
          x1={AXIS_MARGIN_LEFT}
          y1={PADDING + PLOT_HEIGHT}
          x2={WIDTH - PADDING}
          y2={PADDING + PLOT_HEIGHT}
        />
        <text className="hr-chart-axis-label" x={2} y={PADDING + 8}>
          {max.toFixed(2)} m³/m³
        </text>
        <text className="hr-chart-axis-label" x={2} y={PADDING + PLOT_HEIGHT}>
          {min.toFixed(2)} m³/m³
        </text>
        <text className="hr-chart-axis-label" x={AXIS_MARGIN_LEFT} y={HEIGHT - 2} textAnchor="start">
          {rows[0].fecha}
        </text>
        <text className="hr-chart-axis-label" x={WIDTH - PADDING} y={HEIGHT - 2} textAnchor="end">
          {rows[rows.length - 1].fecha}
        </text>
        {segments.map((segment, i) => (
          <polyline
            key={i}
            className="hr-chart-line"
            fill="none"
            points={segment.map(([x, y]) => `${x},${y}`).join(" ")}
          />
        ))}
        {rows.map((row, index) =>
          row.soil_moisture === null ? null : (
            <circle
              key={row.fecha}
              className="hr-chart-point"
              cx={toXY(index, row.soil_moisture)[0]}
              cy={toXY(index, row.soil_moisture)[1]}
              r={2}
            />
          ),
        )}
      </svg>
      <figcaption className="hr-chart-caption">
        {rows[0].fecha} a {rows[rows.length - 1].fecha} · humedad de suelo (m³/m³)
        {gapCount > 0 && ` · ${gapCount} día(s) sin medición, no unidos en el trazo`}
      </figcaption>
    </figure>
  );
}
