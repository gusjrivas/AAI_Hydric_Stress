import "./LabStage.css";
import type { FeedbackRow } from "../forecast/api";
import type { QualityReport } from "../quality/api";
import { labRangeFor } from "./readingGenerator";
import { LAB_DRY_DAYS, LAB_GAP_DAYS, LAB_HISTORY_DAYS } from "./useSensorLabScenarios";
import type { LabPhase, LabSeriesPoint } from "./useSensorLabScenarios";

/** Días que abarca el eje: historial, lectura anómala, interrupción y sequía. Fijo, para que el eje no se mueva entre pasos. */
const TOTAL_DAYS = LAB_HISTORY_DAYS + 1 + LAB_GAP_DAYS + LAB_DRY_DAYS;
const VIEW_W = 1000;
const X0 = 56;
const X1 = 972;
const SOIL = { h: 250, top: 22, bottom: 26, max: 0.62 };
const TEMP = { h: 190, top: 14, bottom: 22, min: -10, max: 95 };
const DAY_MS = 86_400_000;

const dayNumber = (isoDate: string) => Math.round(Date.parse(`${isoDate.slice(0, 10)}T00:00:00Z`) / DAY_MS);
const decimal = (value: number) => value.toFixed(2).replace(".", ",");

function xOf(offset: number): number {
  return X0 + ((X1 - X0) * offset) / (TOTAL_DAYS - 1);
}
function ySoil(value: number): number {
  return SOIL.top + (SOIL.h - SOIL.top - SOIL.bottom) * (1 - value / SOIL.max);
}
function yTemp(value: number): number {
  return TEMP.top + (TEMP.h - TEMP.top - TEMP.bottom) * (1 - (value - TEMP.min) / (TEMP.max - TEMP.min));
}

interface Plotted {
  offset: number;
  point: LabSeriesPoint;
}

/** Un pronóstico emitido ubicado sobre la serie, con la letra del paso que lo pidió. */
interface ForecastEntry {
  row: FeedbackRow;
  item: Plotted;
  letter: "A" | "B" | "D" | "E";
}

function stepLetter(item: Plotted): ForecastEntry["letter"] {
  if (item.point.kind === "dry") return "E";
  if (item.point.kind === "anomaly") return "B";
  return item.offset < LAB_HISTORY_DAYS ? "A" : "D";
}

/** Pronósticos cuya fecha de emisión corresponde a una lectura de la sesión, en orden de fecha. */
function forecastEntries(items: Plotted[], rows: FeedbackRow[]): ForecastEntry[] {
  return rows
    .map((row) => ({ row, item: items.find((i) => i.point.date === row.fecha) }))
    .filter((entry): entry is { row: FeedbackRow; item: Plotted } => entry.item !== undefined)
    .map(({ row, item }) => ({ row, item, letter: stepLetter(item) }))
    .sort((a, b) => (a.row.fecha < b.row.fecha ? -1 : 1));
}

/** Trazado continuo; se corta donde faltan días (la interrupción) para no unir lecturas separadas. */
function pathOf(items: Plotted[], y: (p: LabSeriesPoint) => number): string {
  let d = "";
  let previous: number | null = null;
  for (const item of items) {
    const command = previous !== null && item.offset === previous + 1 ? "L" : "M";
    d += `${command}${xOf(item.offset).toFixed(1)},${y(item.point).toFixed(1)}`;
    previous = item.offset;
  }
  return d;
}

function flaggedCount(quality: QualityReport | null): number {
  if (!quality) return 0;
  return Object.values(quality.out_of_range).reduce((total, dates) => total + dates.length, 0);
}

function latestRow(rows: FeedbackRow[]): FeedbackRow | null {
  return rows.reduce<FeedbackRow | null>((latest, row) => (latest === null || row.fecha > latest.fecha ? row : latest), null);
}

function verdictSentence(row: FeedbackRow | null): string {
  if (!row || row.y_proba == null) return "";
  return row.alerta_generada === 1
    ? `Pronóstico: ALERTA (probabilidad ${decimal(row.y_proba)}).`
    : `Pronóstico: sin alerta (probabilidad ${decimal(row.y_proba)}).`;
}

function captionFor(
  phase: LabPhase,
  readings: LabSeriesPoint[],
  rows: FeedbackRow[],
  quality: QualityReport | null,
): string {
  const verdict = latestRow(rows);
  switch (phase) {
    case "idle":
      return "Todavía no se ejecutó ningún paso. Empezá por el paso A o tocá «Ver la demostración».";
    case "seeding":
      return "Generando el historial de prueba…";
    case "normal": {
      const rowsCount = quality?.total_rows ?? readings.length;
      const dups = quality?.duplicate_timestamps.length ?? 0;
      return `Se generó un historial de ${rowsCount} lecturas con lluvias y calor y el sistema lo validó: ${dups} fechas repetidas y ${flaggedCount(quality)} valores fuera del rango esperado.`;
    }
    case "injecting-anomaly":
      return "Enviando la lectura anómala…";
    case "anomaly": {
      const anomaly = readings.find((r) => r.kind === "anomaly");
      const degrees = anomaly ? Math.round(anomaly.values.temperature) : 85;
      const [, high] = labRangeFor("temperature");
      const flagged = anomaly
        ? (quality?.out_of_range.temperature ?? []).some((d) => d.startsWith(anomaly.date))
        : false;
      const head = `Se envió una lectura de ${degrees} °C, fuera del rango físico (−10 a ${high} °C).`;
      const qualitySentence = flagged
        ? "El control de calidad la marca como fuera de rango. Es una anomalía de medición, no es una alerta de estrés hídrico."
        : "El control de calidad no la marcó en esta consulta; se muestra el resultado real devuelto.";
      return `${head} ${qualitySentence} ${verdictSentence(verdict)}`.trim();
    }
    case "interrupting":
      return "Simulando la interrupción…";
    case "interrupted":
      return `El generador dejó de enviar lecturas durante ${LAB_GAP_DAYS} días simulados (no se desconectó ningún dispositivo físico). La última lectura guardada no cambia y no se pide un pronóstico nuevo: no hay datos que lo sustenten.`;
    case "recovering":
      return "Simulando la recuperación…";
    case "recovered":
      return `Se enviaron lecturas sintéticas para las ${LAB_GAP_DAYS} fechas pendientes y se solicitó un nuevo pronóstico. ${verdictSentence(verdict)}`.trim();
    case "drying":
      return "Generando la sequía simulada…";
    case "drought": {
      const tail = "Son datos sintéticos de demostración: no es evidencia científica.";
      const head = `Se generaron ${LAB_DRY_DAYS} días secos y calurosos, sin lluvia: la humedad del suelo cae.`;
      if (verdict && verdict.alerta_generada === 1 && verdict.y_proba != null) {
        return `${head} El pronóstico real emitió una ALERTA (probabilidad ${decimal(verdict.y_proba)}): el modelo estima que la humedad quedará por debajo de su nivel de estrés. Una alerta señala una posible falta de agua; no la confirma. ${tail}`;
      }
      if (verdict && verdict.y_proba != null) {
        return `${head} El pronóstico real no emitió alerta (probabilidad ${decimal(verdict.y_proba)}). ${tail}`;
      }
      return `${head} ${tail}`;
    }
    case "error":
      return "El paso no pudo completarse. Los datos de la sesión anterior se conservan.";
  }
}

function SoilChart({ items, entries, phase }: { items: Plotted[]; entries: ForecastEntry[]; phase: LabPhase }) {
  const normal = items.filter((i) => i.point.kind !== "dry");
  const dry = items.filter((i) => i.point.kind === "dry");
  const lastNormal = normal[normal.length - 1];
  const dryWithAnchor = dry.length && lastNormal ? [lastNormal, ...dry] : dry;
  const first = items[0];
  const last = items[items.length - 1];
  const bottom = ySoil(0);
  return (
    <svg
      className="ls-svg"
      viewBox={`0 0 ${VIEW_W} ${SOIL.h}`}
      role="img"
      aria-label="Humedad del suelo diaria del sensor de prueba, con los pronósticos emitidos"
    >
      {[0, 0.2, 0.4, 0.6].map((tick) => (
        <g key={tick}>
          <line className="ls-grid" x1={X0} x2={X1} y1={ySoil(tick)} y2={ySoil(tick)} />
          <text className="ls-ax" x={X0 - 8} y={ySoil(tick) + 4} textAnchor="end">
            {tick.toFixed(1).replace(".", ",")}
          </text>
        </g>
      ))}
      {phase === "interrupted" && last && (
        <rect
          data-testid="gap-band"
          className="ls-gap"
          x={xOf(last.offset)}
          y={SOIL.top}
          width={xOf(last.offset + LAB_GAP_DAYS) - xOf(last.offset)}
          height={bottom - SOIL.top}
        />
      )}
      {dry.length > 0 && (
        <g>
          <rect
            data-testid="dry-band"
            className="ls-dry-band"
            x={xOf(dry[0].offset)}
            y={SOIL.top}
            width={xOf(dry[dry.length - 1].offset) - xOf(dry[0].offset)}
            height={bottom - SOIL.top}
          />
          <text className="ls-callout ls-callout--dry" x={xOf(dry[dry.length - 1].offset)} y={SOIL.top - 6} textAnchor="end">
            {LAB_DRY_DAYS} días sin lluvia y con calor
          </text>
        </g>
      )}
      {normal.length > 0 && <path className="ls-line" d={pathOf(normal, (p) => ySoil(p.values.soil_moisture))} />}
      {dryWithAnchor.length > 0 && <path className="ls-line ls-line--dry" d={pathOf(dryWithAnchor, (p) => ySoil(p.values.soil_moisture))} />}
      {entries.map(({ row, item, letter }, index) => {
        const cx = xOf(item.offset);
        const cy = ySoil(item.point.values.soil_moisture);
        const alert = row.alerta_generada === 1;
        const r = alert ? 11 : 8;
        return (
          <g key={row.fecha} data-testid="forecast-marker">
            <path
              data-testid={alert ? "alert-marker" : undefined}
              className={alert ? "ls-fc ls-fc--alert" : "ls-fc ls-fc--ok"}
              d={`M${cx},${cy - r}L${cx + r},${cy}L${cx},${cy + r}L${cx - r},${cy}Z`}
            />
            {/* Solo la letra del paso: el detalle está en la leyenda debajo del gráfico, sin superposición. */}
            <text className={alert ? "ls-fclbl ls-fclbl--alert" : "ls-fclbl"} x={cx} y={cy - r - 4 - (index % 2) * 13} textAnchor="middle">
              {letter}
            </text>
          </g>
        );
      })}
      {first && (
        <g className="ls-ax">
          <text x={X0} y={SOIL.h - 6}>día 1</text>
          <text x={xOf(LAB_HISTORY_DAYS - 1)} y={SOIL.h - 6} textAnchor="end">día {LAB_HISTORY_DAYS}</text>
        </g>
      )}
    </svg>
  );
}

function TemperatureChart({ items }: { items: Plotted[] }) {
  const [low, high] = labRangeFor("temperature");
  const regular = items.filter((i) => i.point.kind !== "anomaly");
  const anomaly = items.find((i) => i.point.kind === "anomaly");
  const dry = regular.filter((i) => i.point.kind === "dry");
  const normal = regular.filter((i) => i.point.kind !== "dry");
  const lastNormal = normal[normal.length - 1];
  const dryWithAnchor = dry.length && lastNormal ? [lastNormal, ...dry] : dry;
  return (
    <svg
      className="ls-svg"
      viewBox={`0 0 ${VIEW_W} ${TEMP.h}`}
      role="img"
      aria-label="Temperatura diaria del sensor de prueba con el rango físico esperado"
    >
      {[0, 25, 50, 75].map((tick) => (
        <g key={tick}>
          <line className="ls-grid" x1={X0} x2={X1} y1={yTemp(tick)} y2={yTemp(tick)} />
          <text className="ls-ax" x={X0 - 8} y={yTemp(tick) + 4} textAnchor="end">{tick}</text>
        </g>
      ))}
      <rect className="ls-band" x={X0} y={yTemp(high)} width={X1 - X0} height={yTemp(low) - yTemp(high)} />
      <text className="ls-bandlbl" x={X1 - 6} y={yTemp(high) - 4} textAnchor="end">
        rango físico esperado ({low} a {high} °C)
      </text>
      {normal.length > 0 && <path className="ls-line" d={pathOf(normal, (p) => yTemp(p.values.temperature))} />}
      {dryWithAnchor.length > 0 && <path className="ls-line ls-line--dry" d={pathOf(dryWithAnchor, (p) => yTemp(p.values.temperature))} />}
      {anomaly && (
        <g data-testid="anomaly-marker">
          <circle className="ls-pt-bad" cx={xOf(anomaly.offset)} cy={yTemp(anomaly.point.values.temperature)} r={7} />
          <text className="ls-callout" x={xOf(anomaly.offset) - 12} y={yTemp(anomaly.point.values.temperature) + 4} textAnchor="end">
            {Math.round(anomaly.point.values.temperature)} °C · fuera de rango
          </text>
        </g>
      )}
    </svg>
  );
}

/**
 * Escena del laboratorio: dos gráficos que se completan paso a paso, un
 * subtítulo que dice qué hizo el sistema e indicadores de calidad y pronóstico.
 * Todo se deriva de lo que el backend ya devolvió (lecturas aceptadas, informe de
 * calidad y pronósticos emitidos); no inventa resultados ni umbrales.
 */
export function LabStage({
  phase,
  readings,
  forecastRows,
  quality,
}: {
  phase: LabPhase;
  readings: LabSeriesPoint[];
  forecastRows: FeedbackRow[];
  quality: QualityReport | null;
}) {
  const start = readings.length ? dayNumber(readings[0].date) : 0;
  const items: Plotted[] = readings.map((point) => ({ offset: dayNumber(point.date) - start, point }));
  const entries = forecastEntries(items, forecastRows);
  const flagged = flaggedCount(quality);
  const verdict = latestRow(forecastRows);
  const alert = verdict?.alerta_generada === 1;

  return (
    <section className="ls-stage" aria-label="Qué está pasando en el laboratorio">
      <p className="ls-caption" data-testid="lab-caption" aria-live="polite">
        <strong>Qué hizo el sistema</strong>
        <br />
        {captionFor(phase, readings, forecastRows, quality)}
      </p>

      <div className="ls-chart">
        <h2>Humedad del suelo del sensor de prueba, y los pronósticos que emitió el sistema</h2>
        <div className="ls-scroll" tabIndex={0} role="region" aria-label="Gráfico de humedad del suelo, desplazable en pantallas angostas">
          <SoilChart items={items} entries={entries} phase={phase} />
        </div>
        {entries.length > 0 && (
          <div className="ls-legend-row">
            <ul className="ls-legend" aria-label="Pronósticos emitidos">
              {entries.map(({ row, letter }) => (
                <li key={row.fecha} className={row.alerta_generada === 1 ? "ls-legend--alert" : undefined}>
                  {letter} · {row.alerta_generada === 1 ? "ALERTA" : "sin alerta"}
                  {row.y_proba != null ? ` · prob. ${decimal(row.y_proba)}` : ""}
                </li>
              ))}
            </ul>
            <p className="ls-legend-key" aria-hidden="true">◇ sin alerta · ◆ con alerta</p>
          </div>
        )}
      </div>
      <div className="ls-chart">
        <h2>Temperatura (°C) y rango físico esperado, para el control de calidad</h2>
        <div className="ls-scroll" tabIndex={0} role="region" aria-label="Gráfico de temperatura, desplazable en pantallas angostas">
          <TemperatureChart items={items} />
        </div>
      </div>

      <div className="ls-tiles">
        <div className={`ls-tile${flagged > 0 ? " ls-tile--flag" : ""}`} data-testid="quality-tile">
          <small>Control de calidad</small>
          <div className="ls-value">{quality ? `${flagged} ${flagged === 1 ? "valor marcado" : "valores marcados"}` : "—"}</div>
          <div>{quality ? `${quality.total_rows} filas · ${quality.duplicate_timestamps.length} fechas repetidas` : "Sin datos todavía."}</div>
        </div>
        <div className={`ls-tile${verdict ? (alert ? " ls-tile--alert" : " ls-tile--ok") : ""}`} data-testid="forecast-tile">
          <small>Último pronóstico</small>
          <div className="ls-value">
            {verdict && verdict.y_proba != null
              ? `${alert ? "ALERTA" : "Sin alerta"} · prob. ${decimal(verdict.y_proba)}`
              : "—"}
          </div>
          <div>
            {verdict
              ? "Resultado real del backend. Una alerta señala una posible falta de agua; no la confirma."
              : "Se solicita después de los pasos A, B, D y E."}
          </div>
        </div>
      </div>
    </section>
  );
}
