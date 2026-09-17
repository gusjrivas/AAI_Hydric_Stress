import { useEffect, useState } from "react";
import "./ResumenView.css";
import { getQualityReport } from "../quality/api";
import type { ForecastWorkspace } from "../forecast/useForecastWorkspace";

type QualityStatus = "loading" | "empty" | "error" | "ready";

export function ResumenView({
  sensorId,
  workspace,
}: {
  sensorId: string;
  workspace: ForecastWorkspace;
}) {
  const [loadedFor, setLoadedFor] = useState(sensorId);
  const [qualityStatus, setQualityStatus] = useState<QualityStatus>("loading");
  const [periodEnd, setPeriodEnd] = useState<string | null>(null);
  const [qualityError, setQualityError] = useState<string | null>(null);

  if (sensorId !== loadedFor) {
    setLoadedFor(sensorId);
    setQualityStatus("loading");
    setPeriodEnd(null);
    setQualityError(null);
  }

  useEffect(() => {
    let cancelled = false;
    getQualityReport(sensorId)
      .then((report) => {
        if (cancelled) return;
        if (report === null) {
          setQualityStatus("empty");
          return;
        }
        setPeriodEnd(report.period_end);
        setQualityStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setQualityError((err as Error).message);
        setQualityStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [sensorId]);

  const lastRow = workspace.rows[0] ?? null;
  const pendientesRevision = workspace.rows.filter(
    (row) => row.estado_validacion === "pendiente",
  ).length;
  const busy = workspace.activeMutation !== null;

  return (
    <div className="rv-view">
      <div className="rv-main">
        <section className="rv-card" aria-label="Último pronóstico registrado">
          {workspace.historyStatus === "loading" && (
            <p role="status">Consultando historial…</p>
          )}
          {workspace.historyStatus === "error" && (
            <p role="alert" className="rv-error">
              {workspace.historyError ?? "No se pudo consultar el historial."}{" "}
              <button type="button" onClick={() => void workspace.reloadHistory()}>
                Reintentar
              </button>
            </p>
          )}
          {workspace.historyStatus !== "loading" && workspace.historyStatus !== "error" && !lastRow && (
            <p role="status">Todavía no hay pronósticos registrados para «{sensorId}».</p>
          )}
          {lastRow && (
            <dl className="rv-summary">
              <div>
                <dt>Fecha de referencia</dt>
                <dd>{lastRow.fecha}</dd>
              </div>
              <div>
                <dt>Alerta</dt>
                <dd>{lastRow.alerta_generada ? "Alerta" : "Sin alerta"}</dd>
              </div>
              <div>
                <dt>Probabilidad</dt>
                <dd>{lastRow.y_proba != null ? lastRow.y_proba.toFixed(2) : "No disponible"}</dd>
              </div>
              <div>
                <dt>Fecha objetivo</dt>
                <dd>{lastRow.fecha_objetivo ?? "No disponible"}</dd>
              </div>
            </dl>
          )}
          <p className="rv-pendientes">
            Pendientes de revisión: <strong>{pendientesRevision}</strong>{" "}
            <a href="#prediccion">Ir a Alertas y revisión</a>
          </p>
          <button
            type="button"
            className="rv-run-btn"
            onClick={() => void workspace.runForecast()}
            disabled={busy}
          >
            {workspace.activeMutation === "forecast" ? "Corriendo..." : "Correr pronóstico"}
          </button>
          {workspace.runError && (
            <p role="alert" className="rv-error">
              {workspace.runError}
            </p>
          )}
          {workspace.refreshPending && (
            <p role="alert" className="rv-error">
              No se pudo confirmar la actualización del historial.{" "}
              <button type="button" onClick={() => void workspace.reloadHistory()}>
                Actualizar
              </button>
            </p>
          )}
        </section>

        <section className="rv-side" aria-label="Contexto de calidad">
          <h3 className="rv-side-heading">Calidad de datos</h3>
          {qualityStatus === "loading" && <p role="status">Consultando calidad…</p>}
          {qualityStatus === "empty" && <p role="status">Sin dataset ingerido todavía.</p>}
          {qualityStatus === "error" && (
            <p role="alert" className="rv-error">
              {qualityError}
            </p>
          )}
          {qualityStatus === "ready" && (
            <p>
              Datos disponibles hasta: <strong>{periodEnd ?? "no disponible"}</strong>
            </p>
          )}
          <p className="rv-side-links">
            <a href="#calidad">Ver calidad completa</a>
            <br />
            <a href="#linaje">Ver predictor activo</a>
          </p>
        </section>
      </div>
    </div>
  );
}
