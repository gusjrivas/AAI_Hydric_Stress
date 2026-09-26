import { useEffect, useState } from "react";
import {
  READING_VARIABLES,
  displayDate,
  getSensorReadings,
  originLabel,
  provenanceLabel,
} from "./readingsApi";
import type { ReadingsResult, ReadingVariable } from "./readingsApi";
import "./ProducerDataScreen.css";

const VARIABLE_LABELS: Record<ReadingVariable, string> = {
  soil_moisture: "Humedad del suelo",
  temperature: "Temperatura",
  precipitation: "Lluvia",
  relative_humidity: "Humedad del aire",
  solar_radiation: "Radiación solar",
  wind_speed: "Viento",
  et0: "Demanda de agua del ambiente (ET₀)",
};

const UNIT_DISPLAY_LABELS: Record<string, string> = {
  "degC": "°C",
  "mm/day": "mm/día",
  "MJ/m2/day": "MJ/m²/día",
  "m/s": "m/s",
  "%": "%",
};

function unitLabel(variable: ReadingVariable, unit: string | undefined): string {
  if (variable === "soil_moisture") return "% del volumen del suelo";
  if (!unit) return "Sin unidad declarada";
  return UNIT_DISPLAY_LABELS[unit] ?? unit;
}

/** Solo se traducen los códigos de calidad que el backend efectivamente
 * emite (`src/data_ingestion/history.py`); nunca se inventa una anomalía
 * sin respaldo en `quality_flags`. */
const QUALITY_FLAG_LABELS: Record<string, (variable: string) => string> = {
  invalid_numeric: (variable) => `Valor no numérico registrado en ${VARIABLE_LABELS[variable as ReadingVariable] ?? variable}`,
  non_finite: (variable) => `Valor fuera de rango registrado en ${VARIABLE_LABELS[variable as ReadingVariable] ?? variable}`,
};

function describeFlag(flag: string): string {
  const [code, variable] = flag.split(":");
  if (code === "future_date") return "Fecha registrada posterior al día de referencia";
  if (code === "unknown_origin") return "Procedencia de la medición sin identificar";
  return QUALITY_FLAG_LABELS[code]?.(variable ?? "") ?? `Anomalía registrada (${flag})`;
}

type State =
  | { key: string; status: "loading" }
  | { key: string; status: "error"; message: string }
  | { key: string; status: "ready"; data: ReadingsResult };

export function ProducerDataScreen({ sensorId }: { sensorId: string }) {
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
  const data = current?.status === "ready" ? current.data : null;
  const rowsWithFlags = data ? data.rows.filter((row) => row.quality_flags.length > 0) : [];

  return (
    <section className="producer-data-screen" aria-labelledby="producer-data-title">
      <div className="producer-data-header">
        <div>
          <p className="producer-eyebrow">DATOS</p>
          <h3 id="producer-data-title">Datos disponibles</h3>
          <p>Revisá qué variables hay, con qué unidad y desde qué procedencia. No se completan los huecos.</p>
        </div>
        <label>Período
          <select value={days} onChange={(event) => setDays(Number(event.target.value) as 7 | 30)}>
            <option value={7}>Últimos 7 días</option>
            <option value={30}>Últimos 30 días</option>
          </select>
        </label>
      </div>

      {!current && <p role="status">Cargando datos…</p>}
      {current?.status === "loading" && <p role="status">Cargando datos…</p>}
      {current?.status === "error" && (
        <p role="alert">
          {current.message} <button type="button" onClick={() => setRetry((n) => n + 1)}>Reintentar</button>
        </p>
      )}
      {current?.status === "ready" && data?.status === "no_readings" && (
        <p role="status">Todavía no hay mediciones para este punto.</p>
      )}

      {current?.status === "ready" && data && data.status === "ready" && (
        <>
          <p className="producer-provenance">{provenanceLabel(data.provenance)}</p>
          <div className="producer-data-summary">
            <div><span>Período disponible</span><strong>{displayDate(data.window.start_date)} – {displayDate(data.window.end_date)}</strong></div>
            <div><span>Fechas sin medición</span><strong>{data.missing_dates.length}</strong></div>
            <div><span>Días con alguna anomalía registrada</span><strong>{rowsWithFlags.length}</strong></div>
          </div>

          <div className="producer-data-table" role="region" aria-label="Variables disponibles" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Variable</th>
                  <th scope="col">Unidad</th>
                  <th scope="col">Con medición</th>
                  <th scope="col">Sin medición</th>
                </tr>
              </thead>
              <tbody>
                {READING_VARIABLES.map((variable) => {
                  const coverage = data.variable_coverage.find((entry) => entry.variable === variable);
                  return (
                    <tr key={variable}>
                      <th scope="row">{VARIABLE_LABELS[variable]}</th>
                      <td>{unitLabel(variable, data.units[variable])}</td>
                      <td>{coverage ? coverage.observed_days : "—"}</td>
                      <td>{coverage ? coverage.missing_days : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {data.missing_dates.length > 0 && (
            <details className="producer-data-missing">
              <summary>Ver fechas sin medición ({data.missing_dates.length})</summary>
              <p>Un hueco no es un valor cero: significa que no se registró una medición para ese día.</p>
              <ul>{data.missing_dates.map((date) => <li key={date}>{displayDate(date)}</li>)}</ul>
            </details>
          )}

          {rowsWithFlags.length > 0 ? (
            <details className="producer-data-quality">
              <summary>Ver anomalías registradas ({rowsWithFlags.length})</summary>
              <p>
                Una anomalía puede ser un cambio real del tiempo o del suelo, no necesariamente un error. Se muestra
                solo cuando el propio dato la respalda.
              </p>
              <ul>
                {rowsWithFlags.map((row) => (
                  <li key={row.date}>
                    <strong>{displayDate(row.date)}</strong> · {originLabel(row.origin)}
                    <ul>{row.quality_flags.map((flag) => <li key={flag}>{describeFlag(flag)}</li>)}</ul>
                  </li>
                ))}
              </ul>
            </details>
          ) : (
            <p className="producer-data-quality-clean">No se registraron anomalías en este período.</p>
          )}
        </>
      )}
    </section>
  );
}
