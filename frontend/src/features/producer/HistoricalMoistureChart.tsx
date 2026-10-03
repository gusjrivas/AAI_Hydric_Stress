import { useLayoutEffect, useRef, useState, type ReactElement } from "react";
import type { ReadingsResult } from "./readingsApi";
import "./HistoricalMoistureChart.css";

type PointStatus = "observed" | "imputed" | "unverified" | "missing" | "future";

interface Point {
  date: string;
  value: number | null;
  status: PointStatus;
}

function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + days));
  return date.toISOString().slice(0, 10);
}

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
function shortDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}`;
}
const pct = (value: number, decimals = 1) => `${(value * 100).toFixed(decimals)} %`; // mismo formato que el resto de la app (p. ej. «36.3 %»)

/**
 * Serie de humedad del suelo hasta el reloj del recorrido. Solo usa filas ya
 * reveladas por el backend: el eje se extiende hasta el último horizonte de la
 * emisión únicamente como zona «aún no revelada», sin valores. Los huecos y los
 * valores imputados o de procedencia no verificada se distinguen del dato
 * observado y nunca se unen con trazo continuo.
 */
export function HistoricalMoistureChart({
  readings,
  emissionDate,
  revealedThrough,
  threshold,
}: {
  readings: ReadingsResult;
  emissionDate: string;
  revealedThrough: string;
  /** Umbral del protocolo en las mismas unidades que `soil_moisture` (fracción), si es comparable. */
  threshold: number | null;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  useLayoutEffect(() => {
    const update = () => setWidth(wrapRef.current?.clientWidth || 640);
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  const byDate = new Map(readings.rows.map((row) => [row.date, row]));
  const start = readings.window.start_date;
  const lastTarget = addDays(emissionDate, 3);
  const end = lastTarget > readings.window.end_date ? lastTarget : readings.window.end_date;
  const points: Point[] = [];
  for (let date = start; date <= end; date = addDays(date, 1)) {
    if (date > revealedThrough) {
      points.push({ date, value: null, status: "future" });
      continue;
    }
    const row = byDate.get(date);
    if (!row || row.soil_moisture === null) points.push({ date, value: null, status: "missing" });
    else if (row.imputed_variables.includes("soil_moisture")) points.push({ date, value: row.soil_moisture, status: "imputed" });
    else if (row.unverified_variables.includes("soil_moisture")) points.push({ date, value: row.soil_moisture, status: "unverified" });
    else points.push({ date, value: row.soil_moisture, status: "observed" });
  }

  const compact = width < 520;
  const height = compact ? 280 : 330;
  const margin = { left: 52, right: 12, top: 30, bottom: compact ? 64 : 58 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const n = points.length;
  const slot = plotW / Math.max(n, 1);
  const x = (i: number) => margin.left + slot * (i + 0.5);

  const values = points.map((p) => p.value).filter((v): v is number => v !== null);
  if (threshold !== null) values.push(threshold);
  const rawMin = values.length ? Math.min(...values) : 0.2;
  const rawMax = values.length ? Math.max(...values) : 0.4;
  const span = Math.max(rawMax - rawMin, 0.04);
  const step = span > 0.16 ? 0.05 : span > 0.08 ? 0.02 : 0.01;
  const lo = Math.floor((rawMin - span * 0.12) / step) * step;
  const hi = Math.ceil((rawMax + span * 0.12) / step) * step;
  const y = (v: number) => margin.top + plotH * (1 - (v - lo) / (hi - lo));
  const ticks: number[] = [];
  for (let t = lo; t <= hi + 1e-9; t += step) ticks.push(Number(t.toFixed(4)));

  const emissionIndex = points.findIndex((p) => p.date === emissionDate);
  const clockIndex = points.findIndex((p) => p.date === revealedThrough);
  const bandFrom = emissionIndex >= 0 ? Math.min(emissionIndex + 1, n - 1) : -1;
  const bandTo = emissionIndex >= 0 ? Math.min(emissionIndex + 3, n - 1) : -1;
  const labelStep = Math.max(1, Math.ceil(56 / slot));
  const counts = {
    observed: points.filter((p) => p.status === "observed").length,
    imputed: points.filter((p) => p.status === "imputed").length,
    unverified: points.filter((p) => p.status === "unverified").length,
    missing: points.filter((p) => p.status === "missing").length,
  };
  const ariaLabel =
    `Humedad del suelo del ${shortDate(start)} al ${shortDate(revealedThrough)}: ${counts.observed} observados, ${counts.imputed} imputados, ` +
    `${counts.unverified} de procedencia no verificada y ${counts.missing} sin dato.` +
    (threshold !== null ? ` Umbral del protocolo ${pct(threshold)}.` : "");

  const segments: ReactElement[] = [];
  for (let i = 0; i < n - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    if (a.value === null || b.value === null) continue;
    const dashed = a.status !== "observed" || b.status !== "observed";
    segments.push(
      <line key={`s${i}`} x1={x(i)} y1={y(a.value)} x2={x(i + 1)} y2={y(b.value)} className={dashed ? "hmc-line hmc-line--dashed" : "hmc-line"} />,
    );
  }

  return (
    <figure className="hmc" aria-label="Gráfico de humedad del suelo">
      <div ref={wrapRef} className="hmc-chart">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel} focusable="false">
          <defs>
            <pattern id="hmc-future" width="8" height="8" patternUnits="userSpaceOnUse">
              <rect width="8" height="8" fill="#f4f7fb" />
              <path d="M0 8L8 0" stroke="#dbe3ee" strokeWidth="1.5" />
            </pattern>
            <pattern id="hmc-miss" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" strokeWidth="2" />
            </pattern>
          </defs>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={margin.left} x2={width - margin.right} y1={y(t)} y2={y(t)} className="hmc-grid" />
              <text x={margin.left - 8} y={y(t) + 4} textAnchor="end" className="hmc-axis">{(t * 100).toFixed(0)} %</text>
            </g>
          ))}
          <text x={14} y={margin.top + plotH / 2} transform={`rotate(-90 14 ${margin.top + plotH / 2})`} textAnchor="middle" className="hmc-axis">
            Humedad del suelo (%)
          </text>
          {clockIndex >= 0 && clockIndex < n - 1 && (
            <g>
              <rect x={x(clockIndex) + slot / 2} y={margin.top} width={width - margin.right - (x(clockIndex) + slot / 2)} height={plotH} fill="url(#hmc-future)" />
              {width - margin.right - (x(clockIndex) + slot / 2) > 96 && (
                <text x={x(clockIndex) + slot / 2 + 8} y={margin.top + plotH - 8} className="hmc-axis hmc-italic">Aún no revelado</text>
              )}
            </g>
          )}
          {bandFrom >= 0 && (
            <g>
              <rect x={x(bandFrom) - slot / 2} y={margin.top} width={(bandTo - bandFrom + 1) * slot} height={plotH} className="hmc-band" />
              <text x={x(bandFrom) - slot / 2 + ((bandTo - bandFrom + 1) * slot) / 2} y={margin.top + 14} textAnchor="middle" className="hmc-band-label">+1 +2 +3</text>
            </g>
          )}
          {points.map((p, i) => p.status === "missing" && (
            <rect key={`m${p.date}`} x={x(i) - slot / 2 + 1} y={margin.top} width={Math.max(slot - 2, 1)} height={plotH} fill="url(#hmc-miss)" opacity={0.35} />
          ))}
          {threshold !== null && (
            <g>
              <line x1={margin.left} x2={width - margin.right} y1={y(threshold)} y2={y(threshold)} className="hmc-threshold" />
              <text x={margin.left + 6} y={y(threshold) - 6} className="hmc-threshold-label">Umbral {pct(threshold)}</text>
            </g>
          )}
          {emissionIndex >= 0 && (
            <g>
              <line x1={x(emissionIndex)} x2={x(emissionIndex)} y1={margin.top - 4} y2={margin.top + plotH} className="hmc-emission" />
              <text x={x(emissionIndex)} y={margin.top - 10} textAnchor={x(emissionIndex) < margin.left + 60 ? "start" : "middle"} className="hmc-emission-label">Emisión {shortDate(emissionDate)}</text>
            </g>
          )}
          {clockIndex >= 0 && (
            <g>
              <line x1={x(clockIndex)} x2={x(clockIndex)} y1={margin.top} y2={margin.top + plotH + 6} className="hmc-clock" />
              <path d={`M${x(clockIndex) - 6} ${margin.top + plotH + 14}L${x(clockIndex) + 6} ${margin.top + plotH + 14}L${x(clockIndex)} ${margin.top + plotH + 6}z`} className="hmc-clock-mark" />
            </g>
          )}
          {segments}
          {points.map((p, i) => {
            if (p.status === "observed" && p.value !== null) return <circle key={p.date} cx={x(i)} cy={y(p.value)} r={5} className="hmc-obs" />;
            if (p.status === "imputed" && p.value !== null) {
              const cy = y(p.value);
              return <path key={p.date} d={`M${x(i)} ${cy - 7}L${x(i) + 7} ${cy}L${x(i)} ${cy + 7}L${x(i) - 7} ${cy}z`} className="hmc-imp" />;
            }
            if (p.status === "unverified" && p.value !== null) return <rect key={p.date} x={x(i) - 5.5} y={y(p.value) - 5.5} width={11} height={11} className="hmc-unv" />;
            if (p.status === "missing") {
              const cy = margin.top + plotH - 12;
              return <path key={p.date} d={`M${x(i) - 5} ${cy - 5}l10 10M${x(i) + 5} ${cy - 5}l-10 10`} className="hmc-miss" />;
            }
            return null;
          })}
          {clockIndex >= 0 && points[clockIndex].value !== null && (
            <text x={x(clockIndex)} y={y(points[clockIndex].value as number) + (points[clockIndex - 1]?.value != null && (points[clockIndex - 1].value as number) > (points[clockIndex].value as number) ? 24 : -12)} textAnchor="middle" className="hmc-last">
              {pct(points[clockIndex].value as number)}
            </text>
          )}
          {points.map((p, i) => i % labelStep === 0 && (
            <text key={`x${p.date}`} x={x(i)} y={margin.top + plotH + 32} textAnchor="middle" className="hmc-axis">{shortDate(p.date)}</text>
          ))}
          {clockIndex >= 0 && (
            <text x={x(clockIndex)} y={margin.top + plotH + 50} textAnchor={x(clockIndex) > width - 60 ? "end" : "middle"} className="hmc-clock-label">Reloj: {shortDate(revealedThrough)}</text>
          )}
        </svg>
      </div>
      <ul className="hmc-legend" aria-label="Leyenda del gráfico">
        <li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5" className="hmc-obs" /></svg>Observado</li>
        <li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5L14.5 8 8 14.5 1.5 8z" className="hmc-imp" /></svg>Imputado (no es una medición)</li>
        <li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="3" width="10" height="10" className="hmc-unv" /></svg>Procedencia no verificada</li>
        <li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" className="hmc-miss" /></svg>Sin dato (el trazo no se une)</li>
        {threshold !== null && <li><svg width="26" height="16" viewBox="0 0 26 16" aria-hidden="true"><line x1="1" x2="25" y1="8" y2="8" className="hmc-threshold" /></svg>Umbral del protocolo</li>}
        <li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><line x1="8" x2="8" y1="1" y2="15" className="hmc-emission" /></svg>Fecha de emisión</li>
        <li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><line x1="8" x2="8" y1="1" y2="15" className="hmc-clock" /></svg>Reloj del recorrido</li>
      </ul>
      <figcaption className="hmc-note">
        No se muestran valores posteriores al reloj del recorrido. Los huecos no se conectan como si hubiera mediciones. La tabla de observaciones de abajo es la alternativa accesible a este gráfico.
      </figcaption>
    </figure>
  );
}
