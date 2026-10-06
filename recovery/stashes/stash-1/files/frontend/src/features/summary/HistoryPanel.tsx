import { useEffect, useState } from "react";
import { displayDate, getMeasurementHistory } from "./historyApi";
import type { MeasurementHistory } from "./historyApi";
import "./HistoryPanel.css";

const DAY = 86400000;
const epoch = (date: string) => Date.parse(`${date}T00:00:00Z`);
const moisture = (value: number | null) => value === null ? "Sin medición" : `${(value * 100).toFixed(1)} %`;

export function HistoryPanel({ sensorId, refreshToken }: { sensorId: string; refreshToken: number | string }) {
  const [days, setDays] = useState(30);
  const [retry, setRetry] = useState(0);
  const key = `${sensorId}:${days}:${refreshToken}:${retry}`;
  const [result, setResult] = useState<{ key: string; data: MeasurementHistory | null; error?: string } | null>(null);
  useEffect(() => {
    let cancelled = false;
    getMeasurementHistory(sensorId, days).then(
      (data) => { if (!cancelled) setResult({ key, data }); },
      (error: Error) => { if (!cancelled) setResult({ key, data: null, error: error.message }); },
    );
    return () => { cancelled = true; };
  }, [sensorId, days, refreshToken, retry, key]);

  const current = result?.key === key ? result : null;
  const data = current?.data;
  const rows = data?.rows ?? [];
  const latest = rows.at(-1);
  const points = rows.filter((row) => row.soil_moisture !== null);
  const start = data?.period_start ? epoch(data.period_start) : 0;
  const end = data?.period_end ? epoch(data.period_end) : start;
  const max = Math.max(0.1, ...points.map((row) => row.soil_moisture!));
  const ceiling = Math.ceil(max * 10) / 10;
  const x = (date: string) => 52 + (epoch(date) - start) / Math.max(DAY, end - start) * 620;
  const y = (value: number) => 180 - value / ceiling * 140;
  // No unir períodos faltantes ni inferir valores entre días no observados.
  const segments = rows.flatMap((row, i) => {
    const prev = rows[i - 1];
    if (!prev || prev.soil_moisture === null || row.soil_moisture === null || epoch(row.fecha) - epoch(prev.fecha) !== DAY) return [];
    return [{ from: prev, to: row }];
  });

  return (
    <section className="history-panel" aria-labelledby="history-title">
      <div className="history-header">
        <div>
          <p className="history-eyebrow">1 · Lo que muestran los datos</p>
          <h3 id="history-title">¿Cómo cambió la humedad del suelo?</h3>
        </div>
        <label>Período del historial
          <select value={days} onChange={(event) => setDays(Number(event.target.value))}>
            <option value={7}>Últimos 7 días del historial</option>
            <option value={30}>Últimos 30 días del historial</option>
            <option value={90}>Últimos 90 días del historial</option>
          </select>
        </label>
      </div>
      <p>Son mediciones guardadas, no proyecciones. El período termina en el último día disponible.</p>
      {!current && <p role="status">Cargando mediciones…</p>}
      {current?.error && <p role="alert">{current.error} <button onClick={() => setRetry((n) => n + 1)}>Reintentar mediciones</button></p>}
      {current && !current.error && rows.length === 0 && <p role="status">Todavía no hay mediciones para mostrar. Elegí un punto con datos o iniciá una demostración.</p>}
      {latest && data && (
        <>
          <p className="history-origin">{rows.every((row) => row.origen === "sintetico")
            ? "Datos simulados · Solo para demostración"
            : rows.every((row) => row.origen === "real") ? "Datos registrados de la fuente" : "Fuentes mixtas o sin identificar · Consultá el detalle"}</p>
          <dl className="history-metrics">
            <div><dt>Humedad del suelo</dt><dd>{moisture(latest.soil_moisture)}</dd></div>
            <div><dt>Temperatura</dt><dd>{latest.temperature === null ? "Sin medición" : `${latest.temperature.toFixed(1)} °C`}</dd></div>
            <div><dt>Lluvia</dt><dd>{latest.precipitation === null ? "Sin medición" : `${latest.precipitation.toFixed(1)} mm`}</dd></div>
          </dl>
          <p>Valores del {displayDate(latest.fecha)}. La humedad expresa el porcentaje del volumen del suelo ocupado por agua.</p>
          {points.length === 0 ? <p>No hay valores de humedad disponibles en este período.</p> : (
            <figure className="history-chart">
              <svg viewBox="0 0 720 230" role="img" aria-label="Evolución de humedad del suelo. Valores por fecha disponibles en la tabla de mediciones.">
                {[0, 0.5, 1].map((fraction) => <g key={fraction}>
                  <line x1="52" x2="672" y1={y(ceiling * fraction)} y2={y(ceiling * fraction)} stroke="#d9e0d5" />
                  <text x="45" y={y(ceiling * fraction) + 4} textAnchor="end">{Math.round(ceiling * fraction * 100)}%</text>
                </g>)}
                {segments.map(({ from, to }) => <line key={to.fecha} x1={x(from.fecha)} y1={y(from.soil_moisture!)} x2={x(to.fecha)} y2={y(to.soil_moisture!)} stroke="#1f5b6b" strokeWidth="3" />)}
                {points.map((row) => <circle key={row.fecha} cx={x(row.fecha)} cy={y(row.soil_moisture!)} r="4" fill="#1f5b6b" />)}
                <text x="52" y="213">{data.period_start ? displayDate(data.period_start) : ""}</text>
                <text x="672" y="213" textAnchor="end">{displayDate(latest.fecha)}</text>
              </svg>
              <figcaption>Cada punto es un día con medición. Los huecos no se completan ni se interpretan como cero.</figcaption>
            </figure>
          )}
          <details>
            <summary>Ver mediciones por fecha ({rows.length})</summary>
            <div className="history-table" tabIndex={0} role="region" aria-label="Tabla de mediciones">
              <table><caption>Valores guardados, sin completar faltantes</caption>
                <thead><tr><th scope="col">Fecha</th><th scope="col">Humedad</th><th scope="col">Temperatura</th><th scope="col">Lluvia</th><th scope="col">Origen</th></tr></thead>
                <tbody>{rows.map((row) => <tr key={row.fecha}>
                  <th scope="row">{displayDate(row.fecha)}</th><td>{moisture(row.soil_moisture)}</td>
                  <td>{row.temperature === null ? "Sin medición" : `${row.temperature.toFixed(1)} °C`}</td>
                  <td>{row.precipitation === null ? "Sin medición" : `${row.precipitation.toFixed(1)} mm`}</td>
                  <td>{row.origen === "sintetico" ? "Simulado" : row.origen === "real" ? "Fuente real" : "No identificado"}</td>
                </tr>)}</tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}
