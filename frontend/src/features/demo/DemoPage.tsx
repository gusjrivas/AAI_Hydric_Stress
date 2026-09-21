import "./DemoPage.css";
import type { DemoSessionState } from "./useDemoSession";

const STATUS_LABELS: Record<string, string> = {
  prepared: "Preparada, sin iniciar",
  running: "En ejecución",
  pausing: "Pausa solicitada — terminando el paso actual",
  paused: "Pausada",
  blocked: "Bloqueada",
  completed: "Completada",
};

interface DemoPageProps {
  demo: DemoSessionState;
}

/**
 * Vista secundaria de demostración (tasks 3.1-3.5). No prepara ni crea
 * sesiones: solo consulta y envía órdenes explícitas al controlador
 * local ya configurado y preparado por CLI (entregas 1 y 2).
 */
export function DemoPage({ demo }: DemoPageProps) {
  const { configured, session, loading, connectionError, pendingCommand, commandError, sendCommand } = demo;

  if (!configured) {
    return (
      <div className="dp-page">
        <p role="status">
          La demostración con datos simulados no está configurada en este entorno. El resto de la
          aplicación funciona normalmente sin ella.
        </p>
      </div>
    );
  }

  return (
    <div className="dp-page">
      <p className="dp-badge">Demostración con datos simulados</p>

      {connectionError && (
        <p role="alert" className="dp-error">
          {connectionError}
        </p>
      )}

      {loading && !session && <p role="status">Consultando la demostración…</p>}

      {!loading && !session && !connectionError && (
        <p role="status">
          Todavía no hay una sesión de demostración preparada. Prepará una desde la línea de comandos
          (<code>python -m scripts.demo_simulation prepare</code>) antes de usar esta vista.
        </p>
      )}

      {session && (
        <>
          <dl className="dp-summary">
            <dt>Sensor</dt>
            <dd>{session.sensor_id}</dd>
            <dt>Estado</dt>
            <dd>{STATUS_LABELS[session.status] ?? session.status}</dd>
            <dt>Día simulado</dt>
            <dd>{session.simulated_date ?? "No disponible"}</dd>
            <dt>Días recorridos</dt>
            <dd>
              {session.cursor} de {session.days}
            </dd>
          </dl>

          {session.status === "blocked" && session.error && (
            <p role="alert" className="dp-error">
              {session.error}
            </p>
          )}

          {commandError && (
            <p role="alert" className="dp-error">
              {commandError}
            </p>
          )}

          <div className="dp-controls">
            <button
              type="button"
              onClick={() => void sendCommand("start")}
              disabled={session.status !== "prepared" || pendingCommand !== null}
            >
              {pendingCommand === "start" ? "Iniciando…" : "Iniciar"}
            </button>
            <button
              type="button"
              onClick={() => void sendCommand("pause")}
              disabled={session.status !== "running" || pendingCommand !== null}
            >
              {pendingCommand === "pause" ? "Pausando…" : "Pausar"}
            </button>
            <button
              type="button"
              onClick={() => void sendCommand("resume")}
              disabled={(session.status !== "paused" && session.status !== "blocked") || pendingCommand !== null}
            >
              {pendingCommand === "resume" ? "Continuando…" : "Continuar"}
            </button>
          </div>

          <p className="dp-note">
            Cerrar esta pestaña no pausa la demostración: el controlador sigue avanzando en segundo
            plano hasta que se solicite pausa o termine la sesión.
          </p>

          {session.status === "completed" && (
            <p role="status">
              Sesión completada. Podés revisar los resultados con objetivo observable en{" "}
              <a href="#prediccion">Historial y observaciones</a>.
            </p>
          )}
        </>
      )}
    </div>
  );
}
