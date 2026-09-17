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
          <h3 className="rv-side-heading">Último pronóstico guardado</h3>
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
            <>
            <p className={`rv-verdict ${lastRow.alerta_generada ? "rv-verdict--alert" : ""}`}>
              {lastRow.alerta_generada ? "Hay una alerta para revisar" : "No se emitió una alerta"}
            </p>
            <p className="rv-guidance">
              {lastRow.alerta_generada
                ? "El resultado señala una posible falta de agua. Contrastalo con las mediciones y la situación del cultivo."
                : "Esto no garantiza que el cultivo tenga suficiente agua. Seguí revisando las mediciones y su estado."}
            </p>
            <dl className="rv-summary">
              <div>
                <dt>Datos usados hasta</dt>
                <dd>{lastRow.fecha}</dd>
              </div>
              <div>
                <dt>Alerta</dt>
                <dd>{lastRow.alerta_generada ? "Alerta" : "Sin alerta"}</dd>
              </div>
              <div>
                <dt>Pronóstico para el día</dt>
                <dd>{lastRow.fecha_objetivo ?? "No disponible"}</dd>
              </div>
            </dl>
            <details className="app-technical">
              <summary>Ver el valor calculado</summary>
              <p>Valor de la señal (de 0 a 1): <span>{lastRow.y_proba != null ? lastRow.y_proba.toFixed(2) : "No disponible"}</span>.</p>
              <p>No es un porcentaje de certeza ni confirma por sí solo una falta de agua.</p>
            </details>
            </>
          )}
          <p className="rv-pendientes">
            Pendientes de revisión: <strong>{pendientesRevision}</strong>{" "}
            <a href="#prediccion">Ir a Historial y observaciones</a>
          </p>
          <button
            type="button"
            className="rv-run-btn"
            onClick={() => void workspace.runForecast()}
            disabled={busy}
          >
            {workspace.activeMutation === "forecast" ? "Preparando pronóstico..." : "Generar pronóstico"}
          </button>
          <p className="rv-guidance">Se usa la última fecha con datos. Si esa fecha no cambia, no se agregan días nuevos al historial.</p>
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
          <h3 className="rv-side-heading">Datos disponibles</h3>
          {qualityStatus === "loading" && <p role="status">Consultando calidad…</p>}
          {qualityStatus === "empty" && <p role="status">Todavía no hay mediciones cargadas para este punto.</p>}
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
            <a href="#calidad">Revisar las mediciones disponibles</a>
            <br />
            <a href="#linaje">Usar mis observaciones en próximos pronósticos</a>
          </p>
        </section>
      </div>
    </div>
  );
}
