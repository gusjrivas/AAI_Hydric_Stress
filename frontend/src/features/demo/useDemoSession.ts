import { useCallback, useEffect, useRef, useState } from "react";
import {
  DemoControlError,
  type DemoSessionView,
  getDemoSession,
  isDemoControlConfigured,
  newRequestId,
  pauseDemo,
  resumeDemo,
  startDemo,
} from "./api";

const POLL_INTERVAL_MS = 2000;

export type DemoCommand = "start" | "pause" | "resume";

export interface DemoSessionState {
  configured: boolean;
  /** Sesión conocida más reciente; se conserva ante un error de consulta
   * (una consulta fallida no equivale a pausa, diseño sección 7). */
  session: DemoSessionView | null;
  /** true mientras nunca se pudo completar ninguna consulta. */
  loading: boolean;
  /** Consulta de estado fallida (red/servicio): la demo podría seguir
   * activa igual, nunca se interpreta como "pausada". */
  connectionError: string | null;
  pendingCommand: DemoCommand | null;
  commandError: string | null;
  /** Cambia cada vez que avanza una fecha confirmada (ingesta o
   * pronóstico), para que la aplicación dispare un refresco por GET de
   * historial/calidad del sensor de demo (requerimiento "Refresco por
   * progreso confirmado"). */
  progressToken: number;
  refresh: () => Promise<void>;
  sendCommand: (command: DemoCommand) => Promise<void>;
}

function progressKey(session: DemoSessionView | null): string {
  if (!session) return "";
  return `${session.last_ingested_date ?? ""}|${session.last_forecast_date ?? ""}`;
}

export function useDemoSession(): DemoSessionState {
  const configured = isDemoControlConfigured();

  const [session, setSession] = useState<DemoSessionView | null>(null);
  const [loading, setLoading] = useState(configured);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [pendingCommand, setPendingCommand] = useState<DemoCommand | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [progressToken, setProgressToken] = useState(0);

  const inFlightRef = useRef(false);
  const lastProgressKeyRef = useRef("");
  const sessionRef = useRef<DemoSessionView | null>(null);

  const refresh = useCallback(async () => {
    if (!configured || inFlightRef.current) return;
    inFlightRef.current = true;
    try {
      const next = await getDemoSession();
      setSession(next);
      sessionRef.current = next;
      setConnectionError(null);
      const key = progressKey(next);
      if (key !== "" && key !== lastProgressKeyRef.current) {
        lastProgressKeyRef.current = key;
        setProgressToken((token) => token + 1);
      } else if (key === "") {
        lastProgressKeyRef.current = "";
      }
    } catch (err) {
      setConnectionError(
        err instanceof DemoControlError
          ? err.message
          : "No se pudo consultar el estado; la demostración podría seguir en marcha.",
      );
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  }, [configured]);

  useEffect(() => {
    if (!configured) return;

    let cancelled = false;

    async function tick() {
      if (cancelled) return;
      await refresh();
    }

    // La consulta corre mientras esta vista está montada ("observando la
    // sesión", diseño sección 7), sin condicionarla al estado de
    // visibilidad del documento: una pestaña recién abierta o restaurada
    // en segundo plano puede reportar `visibilityState === "hidden"` sin
    // que eso signifique que la persona cerró la pestaña, y esta vista
    // no debe quedar cargando indefinidamente por eso.
    void tick();
    const interval = setInterval(() => void tick(), POLL_INTERVAL_MS);

    function onVisibilityChange() {
      if (document.visibilityState === "visible") {
        // Al volver a la pestaña, consultar estado inmediatamente,
        // sin esperar al próximo tick del intervalo.
        void tick();
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      cancelled = true;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [configured, refresh]);

  const sendCommand = useCallback(
    async (command: DemoCommand) => {
      if (pendingCommand !== null) return; // doble clic: se ignora, no se reenvía.
      const current = sessionRef.current;
      if (current === null) return;
      setPendingCommand(command);
      setCommandError(null);
      const order = {
        session_id: current.session_id,
        expected_revision: current.revision,
        request_id: newRequestId(),
      };
      try {
        const dispatch = command === "start" ? startDemo : command === "pause" ? pauseDemo : resumeDemo;
        const next = await dispatch(order);
        setSession(next);
        sessionRef.current = next;
        setConnectionError(null);
      } catch (err) {
        setCommandError(
          err instanceof DemoControlError
            ? err.message
            : "No se pudo enviar la orden. Verificá la conexión e intentá de nuevo.",
        );
        // El estado local podría haber quedado desactualizado (p. ej.
        // revisión obsoleta): se vuelve a consultar, nunca se asume.
        void refresh();
      } finally {
        setPendingCommand(null);
      }
    },
    [pendingCommand, refresh],
  );

  return {
    configured,
    session,
    loading,
    connectionError,
    pendingCommand,
    commandError,
    progressToken,
    refresh,
    sendCommand,
  };
}
