import { useState } from "react";
import type { ReplayHistoryRow } from "./api";
import { addDaysIso, compareIso, daysBetweenIso, isoDayRange } from "./dateUtils";

const WIDTH = 720;
const AXIS_MARGIN_LEFT = 52;
// Suficiente para que la etiqueta "Objetivo" y la banda de clase predicha
// (que siempre terminan exactamente en `domainEnd`, porque la fecha
// objetivo es siempre el borde derecho del dominio) no queden recortadas
// contra el borde del viewBox.
const AXIS_MARGIN_RIGHT = 46;
const AXIS_MARGIN_TOP = 28;
const PLOT_HEIGHT = 160;
const BAND_HEIGHT = 30;
const BAND_GAP = 10;
const AXIS_MARGIN_BOTTOM = 22;
const HEIGHT = AXIS_MARGIN_TOP + PLOT_HEIGHT + BAND_GAP + BAND_HEIGHT + AXIS_MARGIN_BOTTOM;
const PLOT_LEFT = AXIS_MARGIN_LEFT;
const PLOT_RIGHT = WIDTH - AXIS_MARGIN_RIGHT;
const PLOT_WIDTH = PLOT_RIGHT - PLOT_LEFT;
const PLOT_TOP = AXIS_MARGIN_TOP;
const PLOT_BOTTOM = AXIS_MARGIN_TOP + PLOT_HEIGHT;
const BAND_TOP = PLOT_BOTTOM + BAND_GAP;
const BAND_BOTTOM = BAND_TOP + BAND_HEIGHT;

const DEFAULT_WINDOW_DAYS = 30;

export interface MoistureThreshold {
  value: number;
  unit: string;
  variable: string;
}

export interface MoisturePredictedClass {
  value: 0 | 1;
  label: string;
}

interface Props {
  /** Historial ya filtrado por causalidad (nunca posterior al reloj
   * simulado) — este componente no vuelve a pedir ni recorta datos, solo
   * los proyecta en una escala temporal real. */
  rows: ReplayHistoryRow[];
  originDate: string;
  targetDate: string;
  simulatedDate: string;
  threshold: MoistureThreshold;
  /** `null` mientras la predicción todavía no cargó; nunca se dibuja una
   * curva de humedad pronosticada — solo esta clase, en una banda propia. */
  predictedClass: MoisturePredictedClass | null;
}

/**
 * Gráfico principal integrado (Paso "recorrido guiado" §C). Escala temporal
 * real (no por índice de fila): cada fecha de calendario entre el inicio de
 * la ventana y la fecha objetivo ocupa su posición proporcional, incluidos
 * los días ausentes por completo en la respuesta del backend — se tratan
 * igual que un valor nulo, nunca se interpolan ni se saltan con una línea
 * recta. La clase predicha se dibuja en una banda separada del eje numérico
 * de humedad: nunca se traza una curva de humedad "pronosticada", porque esa
 * serie no existe (es una clase binaria, no una estimación numérica).
 */
export function MoistureHistoryChart({
  rows,
  originDate,
  targetDate,
  simulatedDate,
  threshold,
  predictedClass,
}: Props) {
  const [expanded, setExpanded] = useState(false);

  if (rows.length === 0) {
    return (
      <p role="status" className="hr-chart-empty">
        Todavía no hay historial disponible hasta la fecha simulada.
      </p>
    );
  }

  const rowByDate = new Map(rows.map((row) => [row.fecha, row.soil_moisture]));
  const earliestAvailable = rows[0].fecha;
  const fullDomainStart = compareIso(earliestAvailable, originDate) < 0 ? earliestAvailable : originDate;
  const domainEnd = targetDate;
  const defaultDomainStart = clampNotBefore(
    addDaysIso(domainEnd, -(DEFAULT_WINDOW_DAYS - 1)),
    fullDomainStart,
  );
  const canExpand = compareIso(fullDomainStart, defaultDomainStart) < 0;
  const domainStart = expanded ? fullDomainStart : defaultDomainStart;

  const dailySeries = isoDayRange(domainStart, domainEnd).map((fecha) => ({
    fecha,
    value: rowByDate.has(fecha) ? rowByDate.get(fecha) ?? null : null,
  }));

  const visibleValues = dailySeries
    .map((point) => point.value)
    .filter((v): v is number => v !== null);
  // El dominio Y se calcula solo con lo ya visible/revelado y el umbral —
  // nunca consultando valores futuros todavía no revelados, para no fijar
  // una escala "a medida" del resultado que se busca comparar (Paso "gráfico
  // integrado" §C, criterio de escala estable).
  const domainValues = [...visibleValues, threshold.value];
  const rawMin = Math.min(...domainValues);
  const rawMax = Math.max(...domainValues);
  const span = rawMax - rawMin || 1;
  const pad = span * 0.12;
  const min = rawMin - pad;
  const max = rawMax + pad;
  const range = max - min || 1;

  const totalDays = Math.max(daysBetweenIso(domainStart, domainEnd), 1);

  function xForDate(iso: string): number {
    const offset = daysBetweenIso(domainStart, iso);
    return PLOT_LEFT + (offset / totalDays) * PLOT_WIDTH;
  }

  function yForValue(value: number): number {
    return PLOT_TOP + PLOT_HEIGHT - ((value - min) / range) * PLOT_HEIGHT;
  }

  // Segmentos contiguos de valores no nulos; un hueco (nulo o fecha
  // ausente, ya unificados en `dailySeries`) corta el trazo en vez de
  // unirlo con una línea recta engañosa.
  const segments: { points: [number, number][]; revealed: boolean }[] = [];
  let current: [number, number][] = [];
  let currentRevealed = false;
  dailySeries.forEach((point) => {
    if (point.value === null) {
      if (current.length) segments.push({ points: current, revealed: currentRevealed });
      current = [];
      return;
    }
    const isRevealed = compareIso(point.fecha, targetDate) >= 0;
    if (current.length && isRevealed !== currentRevealed) {
      segments.push({ points: current, revealed: currentRevealed });
      current = [];
    }
    currentRevealed = isRevealed;
    current.push([xForDate(point.fecha), yForValue(point.value)]);
  });
  if (current.length) segments.push({ points: current, revealed: currentRevealed });

  const gapCount = dailySeries.filter((point) => point.value === null).length;
  const revealedGapCount = dailySeries.filter(
    (point) => point.value === null && compareIso(point.fecha, targetDate) >= 0 && compareIso(point.fecha, simulatedDate) <= 0,
  ).length;

  const originInDomain = compareIso(originDate, domainStart) >= 0;
  const hiddenIntervalStart = compareIso(simulatedDate, targetDate) < 0 ? addDaysIso(simulatedDate, 1) : null;
  const thresholdY = yForValue(threshold.value);

  return (
    <figure className="hr-chart">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Historial de ${threshold.variable} en escala temporal real, del ${domainStart} al ${domainEnd}, con el umbral de ${threshold.value.toFixed(3)} ${threshold.unit} marcado y la clase predicha en una banda separada`}
      >
        {/* Zona por debajo del umbral, sombreada para lectura rápida. */}
        <rect
          className="hr-chart-below-threshold"
          x={PLOT_LEFT}
          y={thresholdY}
          width={PLOT_WIDTH}
          height={Math.max(PLOT_BOTTOM - thresholdY, 0)}
        />

        {/* Intervalo futuro todavía oculto (sin datos que mostrar, a
            propósito): desde el día siguiente al reloj simulado hasta la
            fecha objetivo. */}
        {hiddenIntervalStart && compareIso(hiddenIntervalStart, domainEnd) <= 0 && (
          <rect
            className="hr-chart-hidden-interval"
            x={xForDate(hiddenIntervalStart)}
            y={PLOT_TOP}
            width={Math.max(xForDate(domainEnd) - xForDate(hiddenIntervalStart), 1)}
            height={PLOT_HEIGHT}
          />
        )}

        <line className="hr-chart-threshold-line" x1={PLOT_LEFT} y1={thresholdY} x2={PLOT_RIGHT} y2={thresholdY} />
        <text className="hr-chart-threshold-label" x={PLOT_LEFT + 4} y={thresholdY - 4}>
          Umbral: {threshold.value.toFixed(3)} {threshold.unit}
        </text>

        <line className="hr-chart-axis" x1={PLOT_LEFT} y1={PLOT_TOP} x2={PLOT_LEFT} y2={PLOT_BOTTOM} />
        <line className="hr-chart-axis" x1={PLOT_LEFT} y1={PLOT_BOTTOM} x2={PLOT_RIGHT} y2={PLOT_BOTTOM} />
        <text className="hr-chart-axis-label" x={2} y={PLOT_TOP + 8}>
          {max.toFixed(2)} {threshold.unit}
        </text>
        <text className="hr-chart-axis-label" x={2} y={PLOT_BOTTOM}>
          {min.toFixed(2)} {threshold.unit}
        </text>

        {originInDomain && (
          <g>
            <line
              className="hr-chart-marker hr-chart-marker-origin"
              x1={xForDate(originDate)}
              y1={PLOT_TOP}
              x2={xForDate(originDate)}
              y2={PLOT_BOTTOM}
            />
            <text className="hr-chart-marker-label" x={xForDate(originDate) + 3} y={PLOT_TOP + 10}>
              Origen
            </text>
          </g>
        )}
        <g>
          <line
            className="hr-chart-marker hr-chart-marker-target"
            x1={xForDate(targetDate)}
            y1={PLOT_TOP}
            x2={xForDate(targetDate)}
            y2={PLOT_BOTTOM}
          />
          <text
            className="hr-chart-marker-label"
            x={xForDate(targetDate) - 3}
            y={PLOT_TOP + 22}
            textAnchor="end"
          >
            Objetivo
          </text>
        </g>

        {segments.map((segment, i) => (
          <polyline
            key={i}
            className={segment.revealed ? "hr-chart-line hr-chart-line-revealed" : "hr-chart-line"}
            fill="none"
            points={segment.points.map(([x, y]) => `${x},${y}`).join(" ")}
          />
        ))}
        {dailySeries.map((point) =>
          point.value === null ? null : (
            <circle
              key={point.fecha}
              className={
                compareIso(point.fecha, targetDate) >= 0
                  ? "hr-chart-point hr-chart-point-revealed"
                  : "hr-chart-point"
              }
              cx={xForDate(point.fecha)}
              cy={yForValue(point.value)}
              r={compareIso(point.fecha, targetDate) >= 0 ? 3.5 : 2}
            />
          ),
        )}

        {/* Banda de la clase predicha: deliberadamente separada del eje
            numérico de humedad — no es una curva de humedad pronosticada,
            es un marcador de clase binaria. */}
        <rect
          className="hr-chart-band-bg"
          x={PLOT_LEFT}
          y={BAND_TOP}
          width={PLOT_WIDTH}
          height={BAND_HEIGHT}
        />
        {predictedClass && (
          <g>
            <rect
              className={
                predictedClass.value === 1
                  ? "hr-chart-band-marker hr-chart-band-marker-alert"
                  : "hr-chart-band-marker hr-chart-band-marker-no-alert"
              }
              // La fecha objetivo es siempre el borde derecho del dominio
              // (`domainEnd`): se ancla la banda por su borde derecho para
              // que quede siempre dentro del área de trazado, en vez de
              // centrarla en un punto que coincide con el límite del
              // gráfico.
              x={Math.max(xForDate(targetDate) - 68, PLOT_LEFT)}
              y={BAND_TOP + 4}
              width={68}
              height={BAND_HEIGHT - 8}
            />
            <text
              className="hr-chart-band-label"
              x={Math.max(xForDate(targetDate) - 34, PLOT_LEFT + 34)}
              y={BAND_TOP + BAND_HEIGHT / 2 + 4}
              textAnchor="middle"
            >
              {predictedClass.value === 1 ? "Alerta anticipada" : "Sin alerta"}
            </text>
          </g>
        )}
        <text className="hr-chart-axis-label" x={PLOT_LEFT} y={BAND_BOTTOM + 14}>
          Predicción archivada (clase, no humedad)
        </text>

        <text className="hr-chart-axis-label" x={PLOT_LEFT} y={HEIGHT - 4} textAnchor="start">
          {domainStart}
        </text>
        <text className="hr-chart-axis-label" x={PLOT_RIGHT} y={HEIGHT - 4} textAnchor="end">
          {domainEnd}
        </text>
      </svg>

      <figcaption className="hr-chart-caption">
        {domainStart} a {domainEnd} · {threshold.variable} ({threshold.unit}) en escala temporal real.
        {gapCount > 0 && ` ${gapCount} día(s) sin medición o ausentes, no unidos en el trazo.`}
        {revealedGapCount > 0 &&
          ` De ellos, ${revealedGapCount} corresponden al intervalo revelado sin dato disponible.`}
      </figcaption>

      <ul className="hr-chart-legend">
        <li>
          <span className="hr-chart-legend-swatch hr-chart-legend-history" aria-hidden="true" />
          Historial disponible antes del objetivo
        </li>
        <li>
          <span className="hr-chart-legend-swatch hr-chart-legend-revealed" aria-hidden="true" />
          Observación revelada (en o después del objetivo)
        </li>
        <li>
          <span className="hr-chart-legend-swatch hr-chart-legend-threshold" aria-hidden="true" />
          Umbral estadístico de humedad
        </li>
        <li>
          <span className="hr-chart-legend-swatch hr-chart-legend-hidden" aria-hidden="true" />
          Intervalo futuro todavía oculto
        </li>
        <li>
          <span className="hr-chart-legend-swatch hr-chart-legend-band" aria-hidden="true" />
          Clase predicha (banda separada, no es humedad)
        </li>
      </ul>

      {canExpand && (
        <button type="button" className="hr-chart-expand" onClick={() => setExpanded((v) => !v)}>
          {expanded
            ? `Ver los últimos ${DEFAULT_WINDOW_DAYS} días`
            : "Ampliar al historial completo disponible"}
        </button>
      )}
    </figure>
  );
}

function clampNotBefore(candidate: string, floor: string): string {
  return compareIso(candidate, floor) < 0 ? floor : candidate;
}
