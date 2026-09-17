import { useRef, useState } from "react";
import "./ForecastPage.css";
import { CorrectionForm } from "./CorrectionForm";
import type { ForecastWorkspace } from "./useForecastWorkspace";

type AlertaFilter = "todas" | "alerta" | "sin_alerta";
type EstadoFilter = "todas" | "pendiente" | "confirmada" | "rechazada";

const DEFAULT_FILTERS = {
  alerta: "todas" as AlertaFilter,
  estado: "todas" as EstadoFilter,
  desde: "",
  hasta: "",
};

interface ForecastPageProps {
  sensorId: string;
  workspace: ForecastWorkspace;
}

export function ForecastPage({ workspace }: ForecastPageProps) {
  const [alertaFilter, setAlertaFilter] = useState<AlertaFilter>(DEFAULT_FILTERS.alerta);
  const [estadoFilter, setEstadoFilter] = useState<EstadoFilter>(DEFAULT_FILTERS.estado);
  const [fechaDesde, setFechaDesde] = useState(DEFAULT_FILTERS.desde);
  const [fechaHasta, setFechaHasta] = useState(DEFAULT_FILTERS.hasta);
  const [openCorrectionFecha, setOpenCorrectionFecha] = useState<string | null>(null);
  const correctionButtonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const feedbackPendienteRevision = workspace.rows.filter(
    (row) => row.estado_validacion === "pendiente",
  ).length;

  const busy = workspace.activeMutation !== null;

  const filtersActive =
    alertaFilter !== DEFAULT_FILTERS.alerta ||
    estadoFilter !== DEFAULT_FILTERS.estado ||
    fechaDesde !== DEFAULT_FILTERS.desde ||
    fechaHasta !== DEFAULT_FILTERS.hasta;

  const filteredRows = workspace.rows.filter((row) => {
    if (alertaFilter === "alerta" && !row.alerta_generada) return false;
    if (alertaFilter === "sin_alerta" && row.alerta_generada) return false;
    if (estadoFilter !== "todas" && row.estado_validacion !== estadoFilter) return false;
    if (fechaDesde && row.fecha < fechaDesde) return false;
    if (fechaHasta && row.fecha > fechaHasta) return false;
    return true;
  });

  function clearFilters() {
    setAlertaFilter(DEFAULT_FILTERS.alerta);
    setEstadoFilter(DEFAULT_FILTERS.estado);
    setFechaDesde(DEFAULT_FILTERS.desde);
    setFechaHasta(DEFAULT_FILTERS.hasta);
  }

  function closeCorrection(fecha: string) {
    setOpenCorrectionFecha(null);
    correctionButtonRefs.current[fecha]?.focus();
  }

  async function handleSaveCorrection(fecha: string, etiquetaCorregida: 0 | 1, observacion: string) {
    const ok = await workspace.reject(fecha, etiquetaCorregida, observacion);
    if (ok) {
      setOpenCorrectionFecha(null);
    }
    // en caso de error (p. ej. 409) el formulario permanece abierto y
    // workspace.rowErrors[fecha] muestra el motivo junto a la fila.
  }

  return (
    <div className="fp-page">
      <p className="fp-subtitle">Validación humana de alertas sobre el dataset consolidado</p>

      <div className="fp-banner" role="note">
        <strong>Qué prueba esta pantalla:</strong> consultar y filtrar el historial no genera un
        pronóstico nuevo — esa acción vive en Resumen. Confirmar o corregir guarda tu validación
        en el registro de retroalimentación; guardar una validación no reentrena el modelo. La
        recalibración manual vive en Modelo y trazabilidad.
      </div>

      <p className="fp-disclaimer">
        La probabilidad es una señal predictiva relativa del modelo y no un diagnóstico
        fisiológico ni una probabilidad agronómicamente calibrada.
      </p>

      {workspace.actionMessage && (
        <p role="status" className="fp-action-message">
          {workspace.actionMessage}
        </p>
      )}

      {workspace.historyStatus === "loading" && <p role="status">Consultando historial…</p>}

      {workspace.historyStatus === "empty" && (
        <p role="status">Todavía no hay pronósticos registrados.</p>
      )}

      {workspace.historyStatus === "error" && (
        <p role="alert" className="fp-error">
          {workspace.historyError ?? "No se pudo consultar el historial."}{" "}
          <button type="button" onClick={() => void workspace.reloadHistory()}>
            Reintentar
          </button>
        </p>
      )}

      {(workspace.historyStatus === "ready" || workspace.rows.length > 0) && (
        <>
          <p className="fp-feedback-stats">
            Feedback sin revisar: <strong>{feedbackPendienteRevision}</strong>
          </p>

          <fieldset className="fp-filters">
            <legend>Filtrar historial</legend>
            <label>
              Alerta
              <select
                value={alertaFilter}
                onChange={(event) => setAlertaFilter(event.target.value as AlertaFilter)}
              >
                <option value="todas">Todas</option>
                <option value="alerta">Alerta</option>
                <option value="sin_alerta">Sin alerta</option>
              </select>
            </label>
            <label>
              Estado de validación
              <select
                value={estadoFilter}
                onChange={(event) => setEstadoFilter(event.target.value as EstadoFilter)}
              >
                <option value="todas">Todas</option>
                <option value="pendiente">Pendiente</option>
                <option value="confirmada">Confirmada</option>
                <option value="rechazada">Rechazada</option>
              </select>
            </label>
            <label>
              Fecha de referencia desde
              <input
                type="date"
                value={fechaDesde}
                onChange={(event) => setFechaDesde(event.target.value)}
              />
            </label>
            <label>
              Fecha de referencia hasta
              <input
                type="date"
                value={fechaHasta}
                onChange={(event) => setFechaHasta(event.target.value)}
              />
            </label>
            <button type="button" onClick={clearFilters} disabled={!filtersActive}>
              Limpiar filtros
            </button>
          </fieldset>

          {filteredRows.length === 0 ? (
            <p role="status">Sin coincidencias con los filtros aplicados.</p>
          ) : (
            <ul className="fp-list">
              {filteredRows.map((row) => {
                const severity = row.alerta_generada ? "alert" : "safe";
                const rowBusy =
                  workspace.activeMutation === `confirm:${row.fecha}` ||
                  workspace.activeMutation === `reject:${row.fecha}`;
                const correctionOpen = openCorrectionFecha === row.fecha;
                return (
                  <li key={row.fecha} className={`fp-row fp-row--${severity}`}>
                    <span className="fp-signal" aria-hidden="true" />
                    <div className="fp-row-main">
                      <div className="fp-row-date">{row.fecha}</div>
                      {row.fecha_objetivo && <div>Objetivo: {row.fecha_objetivo}</div>}
                      <div className="fp-row-verdict">
                        {row.alerta_generada ? "Alerta" : "Sin alerta"}
                      </div>
                    </div>
                    <div className="fp-gauge">
                      {row.y_proba != null ? (
                        <>
                          <span className="fp-gauge-value">{row.y_proba.toFixed(2)}</span>
                          <span className="fp-gauge-bar">
                            <span
                              className="fp-gauge-fill"
                              style={{ width: `${Math.round(row.y_proba * 100)}%` }}
                            />
                          </span>
                        </>
                      ) : (
                        <span className="fp-gauge-value">No disponible</span>
                      )}
                    </div>
                    <span className={`fp-badge fp-badge--${row.estado_validacion}`}>
                      {row.estado_validacion}
                    </span>
                    <div className="fp-actions">
                      <button onClick={() => workspace.confirm(row.fecha)} disabled={busy}>
                        {rowBusy && workspace.activeMutation === `confirm:${row.fecha}`
                          ? "Guardando..."
                          : "Confirmar"}
                      </button>
                      <button
                        ref={(el) => {
                          correctionButtonRefs.current[row.fecha] = el;
                        }}
                        onClick={() => setOpenCorrectionFecha(row.fecha)}
                        disabled={busy}
                      >
                        Corregir resultado
                      </button>
                    </div>
                    {correctionOpen && (
                      <CorrectionForm
                        row={row}
                        saving={workspace.activeMutation === `reject:${row.fecha}`}
                        serverError={workspace.rowErrors[row.fecha] ?? null}
                        onCancel={() => closeCorrection(row.fecha)}
                        onSave={(etiquetaCorregida, observacion) =>
                          void handleSaveCorrection(row.fecha, etiquetaCorregida, observacion)
                        }
                      />
                    )}
                    {!correctionOpen && workspace.rowErrors[row.fecha] && (
                      <p role="alert" className="fp-error">
                        {workspace.rowErrors[row.fecha]}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
