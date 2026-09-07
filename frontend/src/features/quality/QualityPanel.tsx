import { useEffect, useState } from "react";
import "./QualityPanel.css";
import { getQualityReport } from "./api";
import type { QualityReport } from "./api";

type Status = "loading" | "empty" | "error" | "ready";

export function QualityPanel({ sensorId }: { sensorId: string }) {
  const [status, setStatus] = useState<Status>("loading");
  const [report, setReport] = useState<QualityReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    setError(null);
    getQualityReport(sensorId)
      .then((result) => {
        if (cancelled) return;
        if (result === null) {
          setStatus("empty");
          return;
        }
        setReport(result);
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError((err as Error).message);
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [sensorId]);

  if (status === "loading") {
    return (
      <p role="status" className="qp-status">
        Cargando calidad de datos del sensor…
      </p>
    );
  }

  if (status === "empty") {
    return (
      <p role="status" className="qp-status">
        Todavía no hay datos ingeridos para «{sensorId}». Corré un pronóstico o cargá una
        lectura para ver su diagnóstico de calidad.
      </p>
    );
  }

  if (status === "error") {
    return (
      <p role="alert" className="qp-error">
        {error}
      </p>
    );
  }

  const variables = Object.keys(report!.missing_pct);
  const outOfRangeTotal = Object.values(report!.out_of_range).reduce(
    (sum, dates) => sum + dates.length,
    0,
  );

  return (
    <div className="qp-panel">
      <dl className="qp-summary">
        <div>
          <dt>Período disponible</dt>
          <dd>
            {report!.period_start} → {report!.period_end} ({report!.total_rows} registros)
          </dd>
        </div>
        <div>
          <dt>Timestamps duplicados</dt>
          <dd>{report!.duplicate_timestamps.length}</dd>
        </div>
        <div>
          <dt>Valores fuera de rango</dt>
          <dd>{outOfRangeTotal}</dd>
        </div>
        <div>
          <dt>Anomalías detectadas ({report!.anomaly_method})</dt>
          <dd>{report!.anomalies_detected}</dd>
        </div>
      </dl>

      <h3 className="qp-subheading">Faltantes por variable</h3>
      <ul className="qp-bars">
        {variables.map((variable) => {
          const pct = report!.missing_pct[variable];
          return (
            <li key={variable} className="qp-bar-row">
              <span className="qp-bar-label">{variable}</span>
              <span
                className="qp-bar-track"
                role="img"
                aria-label={`${pct.toFixed(1)}% de faltantes en ${variable}`}
              >
                <span className="qp-bar-fill" style={{ width: `${Math.min(pct, 100)}%` }} />
              </span>
              <span className="qp-bar-value">{pct.toFixed(1)}%</span>
            </li>
          );
        })}
      </ul>

      <p className="qp-note">
        <strong>Nota:</strong> una anomalía puede representar un evento real (una ola de calor,
        una lluvia intensa), no necesariamente un error de sensor.
      </p>
      <p className="qp-note qp-note--diagnostic">{report!.note}</p>
    </div>
  );
}
