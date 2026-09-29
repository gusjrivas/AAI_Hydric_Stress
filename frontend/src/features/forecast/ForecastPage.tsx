import { useRef, useState } from "react";
import "./ForecastPage.css";
import { CorrectionForm } from "./CorrectionForm";
import type { ForecastWorkspace } from "./useForecastWorkspace";
import type { DemoWriteGate } from "../demo/lock";
import {
  TARGET_UNVERIFIABLE_MESSAGE,
  targetImmatureMessage,
  targetMaturity,
  useUtcToday,
  utcToday,
} from "./targetMaturity";
import type { TargetMaturity } from "./targetMaturity";

function maturityMessage(maturity: TargetMaturity): string | null {
  if (maturity.status === "immature") return targetImmatureMessage(maturity.target);
  if (maturity.status === "unverifiable") return TARGET_UNVERIFIABLE_MESSAGE;
  return null;
}

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
  demoGate?: DemoWriteGate;
}

export function ForecastPage({ workspace, demoGate }: ForecastPageProps) {
  const [alertaFilter, setAlertaFilter] = useState<AlertaFilter>(DEFAULT_FILTERS.alerta);
  const [estadoFilter, setEstadoFilter] = useState<EstadoFilter>(DEFAULT_FILTERS.estado);
  const [fechaDesde, setFechaDesde] = useState(DEFAULT_FILTERS.desde);
  const [fechaHasta, setFechaHasta] = useState(DEFAULT_FILTERS.hasta);
  const [openCorrectionFecha, setOpenCorrectionFecha] = useState<string | null>(null);
  const [guardErrors, setGuardErrors] = useState<Record<string, string>>({});
  const correctionButtonRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const today = useUtcToday();

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

  /** Comprobación con el día UTC real en el momento de actuar, para no
   * depender de un valor de render ya vencido (formulario abierto). */
  function blockedNow(row: { fecha: string; fecha_objetivo?: string | null }): boolean {
    const message = maturityMessage(targetMaturity(row.fecha_objetivo, utcToday()));
    setGuardErrors((prev) => {
      if (message === null) {
        if (!(row.fecha in prev)) return prev;
        const next = { ...prev };
        delete next[row.fecha];
        return next;
      }
      return { ...prev, [row.fecha]: message };
    });
    return message !== null;
  }

  function handleConfirm(row: { fecha: string; fecha_objetivo?: string | null }) {
    if (blockedNow(row)) return;
    void workspace.confirm(row.fecha);
  }

  async function handleSaveCorrection(
    row: { fecha: string; fecha_objetivo?: string | null },
    etiquetaCorregida: 0 | 1,
    observacion: string,
  ) {
    if (blockedNow(row)) return;
    const fecha = row.fecha;
    const ok = await workspace.reject(fecha, etiquetaCorregida, observacion);
    if (ok) {
      setOpenCorrectionFecha(null);
    }
    // en caso de error (p. ej. 409) el formulario permanece abierto y
    // workspace.rowErrors[fecha] muestra el motivo junto a la fila.
  }

  return (
    <div className="fp-page">
      <p className="fp-subtitle">Consultá los días guardados y registrá si el resultado coincide con lo observado.</p>

      <div className="fp-banner" role="note">
        <strong>Cómo revisar:</strong> cuando haya terminado el día indicado, compará el resultado
        con lo observado. Elegí «Confirmar» si coincide o «Corregir resultado» si fue distinto.
        Guardar tu observación no cambia automáticamente los próximos pronósticos.
      </div>

      <p className="fp-disclaimer">
        Una alerta señala una posible falta de agua; no la confirma. La ausencia de alerta
        tampoco garantiza que el cultivo esté bien.
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
            Resultados por revisar: <strong>{feedbackPendienteRevision}</strong>
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
              Revisión del resultado
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
              Datos hasta: desde
              <input
                type="date"
                value={fechaDesde}
                onChange={(event) => setFechaDesde(event.target.value)}
              />
            </label>
            <label>
              Datos hasta: hasta
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
          <p role="status" className="fp-feedback-stats">
            Mostrando {filteredRows.length} de {workspace.rows.length} resultados guardados.
          </p>
          <p className="fp-disclaimer">Los filtros buscan entre los días guardados. Las fechas corresponden al último día de datos usado en cada pronóstico.</p>

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
                const rowBlockedByDemo = demoGate ? !demoGate.isRowReviewable(row) : false;
                const timeMessage = maturityMessage(targetMaturity(row.fecha_objetivo, today));
                const rowBlockedByTime = timeMessage !== null;
                const rowBlocked = rowBlockedByDemo || rowBlockedByTime;
                const guardError = guardErrors[row.fecha] ?? null;
                return (
                  <li key={row.fecha} className={`fp-row fp-row--${severity}`}>
                    <span className="fp-signal" aria-hidden="true" />
                    <div className="fp-row-main">
                      <div className="fp-row-date">{row.fecha}</div>
                      {row.fecha_objetivo && <div>Para el día: {row.fecha_objetivo}</div>}
                      <div className="fp-row-verdict">
                        {row.alerta_generada ? "Alerta" : "Sin alerta"}
                      </div>
                    </div>
                    <details className="fp-gauge">
                      <summary>Valor calculado</summary>
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
                      <p className="fp-disclaimer">Señal del modelo de 0 a 1. No representa un porcentaje de certeza.</p>
                    </details>
                    <span className={`fp-badge fp-badge--${row.estado_validacion}`}>
                      {({ pendiente: "Por revisar", confirmada: "Coincide con lo observado", rechazada: "Corregido por una persona" } as Record<string, string>)[row.estado_validacion] ?? "Estado no disponible"}
                    </span>
                    <div className="fp-actions">
                      <button onClick={() => handleConfirm(row)} disabled={busy || rowBlocked}>
                        {rowBusy && workspace.activeMutation === `confirm:${row.fecha}`
                          ? "Guardando..."
                          : "Confirmar"}
                      </button>
                      <button
                        ref={(el) => {
                          correctionButtonRefs.current[row.fecha] = el;
                        }}
                        onClick={() => setOpenCorrectionFecha(row.fecha)}
                        disabled={busy || rowBlocked}
                      >
                        Corregir resultado
                      </button>
                    </div>
                    {rowBlockedByDemo && (
                      <p className="fp-disclaimer">{demoGate!.rowUnavailableReason(row)}</p>
                    )}
                    {rowBlockedByTime && <p className="fp-disclaimer">{timeMessage}</p>}
                    {correctionOpen && (
                      <CorrectionForm
                        row={row}
                        saving={workspace.activeMutation === `reject:${row.fecha}`}
                        serverError={workspace.rowErrors[row.fecha] ?? guardError}
                        onCancel={() => closeCorrection(row.fecha)}
                        onSave={(etiquetaCorregida, observacion) =>
                          void handleSaveCorrection(row, etiquetaCorregida, observacion)
                        }
                      />
                    )}
                    {!correctionOpen && (workspace.rowErrors[row.fecha] ?? guardError) && (
                      <p role="alert" className="fp-error">
                        {workspace.rowErrors[row.fecha] ?? guardError}
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
