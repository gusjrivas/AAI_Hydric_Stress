import { useEffect, useState } from "react";
import {
  READING_VARIABLES,
  displayDate,
  formatReadingValue,
  getSensorReadings,
  originLabel,
  provenanceLabel,
} from "./readingsApi";
import type { ReadingsResult } from "./readingsApi";
import "./ProducerHistoryPanel.css";

const VARIABLE_LABELS: Record<string, string> = {
  soil_moisture: "Humedad del suelo",
  temperature: "Temperatura",
  precipitation: "Lluvia",
  relative_humidity: "Humedad del aire",
  solar_radiation: "Radiación solar",
  wind_speed: "Viento",
  et0: "Demanda de agua del ambiente (ET₀)",
};

const DAY = 86400000;
const epoch = (date: string) => Date.parse(`${date}T00:00:00Z`);

type State =
  | { key: string; status: "loading" }
  | { key: string; status: "error"; message: string }
  | { key: string; status: "ready"; data: ReadingsResult };

/**
 * Historial de mediciones desde el catálogo v2. Una respuesta atrasada de
 * otro sensor o período no reemplaza la selección actual: cada resultado
 * lleva la clave `sensorId:days` con la que se pidió y se descarta si ya no
 * coincide con la selección vigente al resolver.
 */
export function ProducerHistoryPanel({ sensorId }: { sensorId: string }) {
  const [days, setDays] = useState<7 | 30>(30);
  const [retry, setRetry] = useState(0);
  const key = `${sensorId}:${days}:${retry}`;
  const [state, setState] = useState<State>({ key, status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ key, status: "loading" });
    getSensorReadings(sensorId, days).then(
      (data) => {
        if (cancelled) return;
        setState({ key, status: "ready", data });
      },
      (error: Error) => {
        if (cancelled) return;
        setState({ key, status: "error", message: error.message });
      },
    );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sensorId, days, retry]);

  const current = state.key === key ? state : null;

  const rows = current?.status === "ready" ? current.data.rows : [];
  const latest = rows.at(-1);
  const points = rows.filter((row) => row.soil_moisture !== null);
  const data = current?.status === "ready" ? current.data : null;
  const start = data ? epoch(data.window.start_date) : 0;
  const end = data ? epoch(data.window.end_date) : start;
  const max = Math.max(0.1, ...points.map((row) => row.soil_moisture!));
  const ceiling = Math.ceil(max * 10) / 10;
  const x = (date: string) => 52 + (epoch(date) - start) / Math.max(DAY, end - start) * 620;
  const y = (value: number) => 180 - value / ceiling * 140;
  const segments = rows.flatMap((row, i) => {
    const prev = rows[i - 1];
    if (!prev || prev.soil_moisture === null || row.soil_moisture === null || epoch(row.date) - epoch(prev.date) !== DAY) {
      return [];
    }
    return [{ from: prev, to: row }];
  });

  return (
    <section className="history-panel" aria-labelledby="producer-history-title">
      <div className="history-header">
        <div>
          <p className="history-eyebrow">Mediciones</p>
          <h3 id="producer-history-title">¿Cómo cambió la humedad del suelo?</h3>
        </div>
        <label>Período
          <select value={days} onChange={(event) => setDays(Number(event.target.value) as 7 | 30)}>
            <option value={7}>Últimos 7 días</option>
            <option value={30}>Últimos 30 días</option>
          </select>
        </label>
      </div>
      <p>Son mediciones guardadas, no proyecciones. El período termina en el último día disponible.</p>

      {!current && <p role="status">Cargando mediciones…</p>}
      {current?.status === "error" && (
        <p role="alert">
          {current.message}{" "}
          <button onClick={() => setRetry((n) => n + 1)}>Reintentar mediciones</button>
        </p>
      )}
      {current?.status === "ready" && data?.status === "no_readings" && (
        <p role="status">Todavía no hay mediciones para este punto. Elegí otro punto o esperá a que se registren datos.</p>
      )}

      {current?.status === "ready" && data && data.status === "ready" && (
        <>
          <p className="history-origin">{provenanceLabel(data.provenance)}</p>
          <p>
            Última lectura: {data.last_reading_date ? displayDate(data.last_reading_date) : "sin registrar"}.{" "}
            {data.data_age_days === null
              ? "No se puede calcular la antigüedad de los datos."
              : data.data_age_days === 0
                ? "Corresponde al día de hoy (UTC)."
                : `Antigüedad: ${data.data_age_days} ${data.data_age_days === 1 ? "día" : "días"}.`}
          </p>
          {data.missing_dates.length > 0 && (
            <p>
              {data.missing_dates.length} {data.missing_dates.length === 1 ? "fecha falta" : "fechas faltan"} en este
              período. Los huecos no se completan ni se interpretan como cero.
            </p>
          )}

          {latest && (
            <dl className="history-metrics">
              <div><dt>Humedad del suelo</dt><dd>{formatReadingValue("soil_moisture", latest.soil_moisture, data.units.soil_moisture)}</dd></div>
              <div><dt>Temperatura</dt><dd>{formatReadingValue("temperature", latest.temperature, data.units.temperature)}</dd></div>
              <div><dt>Lluvia</dt><dd>{formatReadingValue("precipitation", latest.precipitation, data.units.precipitation)}</dd></div>
            </dl>
          )}
          {latest && <p>Valores del {displayDate(latest.date)}. La humedad expresa el porcentaje del volumen del suelo ocupado por agua.</p>}

          {points.length === 0 ? (
            <p>No hay valores de humedad disponibles en este período.</p>
          ) : (
            <figure className="history-chart">
              <svg viewBox="0 0 720 230" role="img" aria-label="Evolución de humedad del suelo. Valores por fecha disponibles en la tabla de mediciones.">
                {[0, 0.5, 1].map((fraction) => (
                  <g key={fraction}>
                    <line x1="52" x2="672" y1={y(ceiling * fraction)} y2={y(ceiling * fraction)} stroke="#E6EAE8" />
                    <text x="45" y={y(ceiling * fraction) + 4} textAnchor="end">{Math.round(ceiling * fraction * 100)}%</text>
                  </g>
                ))}
                {segments.map(({ from, to }) => (
                  <line key={to.date} x1={x(from.date)} y1={y(from.soil_moisture!)} x2={x(to.date)} y2={y(to.soil_moisture!)} stroke="#1F6FB2" strokeWidth="3" />
                ))}
                {points.map((row) => (
                  <circle key={row.date} cx={x(row.date)} cy={y(row.soil_moisture!)} r="4" fill="#1F6FB2" />
                ))}
                <text x="52" y="213">{displayDate(data.window.start_date)}</text>
                <text x="672" y="213" textAnchor="end">{displayDate(latest!.date)}</text>
              </svg>
              <figcaption>Cada punto es un día con medición. Los huecos no se completan ni se interpretan como cero.</figcaption>
            </figure>
          )}

          <details>
            <summary>Ver mediciones por fecha ({rows.length})</summary>
            <div className="history-table" tabIndex={0} role="region" aria-label="Tabla de mediciones">
              <table>
                <caption>Valores guardados, sin completar faltantes</caption>
                <thead>
                  <tr>
                    <th scope="col">Fecha</th>
                    {READING_VARIABLES.map((variable) => <th key={variable} scope="col">{VARIABLE_LABELS[variable]}</th>)}
                    <th scope="col">Origen</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.date}>
                      <th scope="row">{displayDate(row.date)}</th>
                      {READING_VARIABLES.map((variable) => (
                        <td key={variable}>{formatReadingValue(variable, row[variable], data.units[variable])}</td>
                      ))}
                      <td>{originLabel(row.origin)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}
