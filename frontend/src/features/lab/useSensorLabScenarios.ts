import { userFacingErrorMessage } from "../shared/errorMessage";
import { useLayoutEffect, useRef, useState } from "react";
import { getQualityReport } from "../quality/api";
import type { QualityReport } from "../quality/api";
import { addDaysUtc, labBackfillEndDateUtc } from "./labSensor";
import { generateWaterBalanceReading, injectRangeAnomaly, mulberry32 } from "./readingGenerator";
import type { LabReadingValues } from "./readingGenerator";
import { ingestLabReading } from "./sensorLabApi";

/** Semilla/configuración fija (escenarios reproducibles, sección 3 del
 * mandato). `LAB_HISTORY_DAYS` reutiliza el mismo tamaño de historial ya
 * verificado end-to-end contra el backend real en
 * `openspec/specs/demo-simulation/spec.md` (`history_days=120`), en vez
 * de adivinar un mínimo nuevo. */
export const LAB_SEED = 42;
export const LAB_HISTORY_DAYS = 120;
export const LAB_GAP_DAYS = 4;
/** Días secos y calurosos del paso E (sequía). */
export const LAB_DRY_DAYS = 14;

export const LAB_ERROR_NO_LAST_READING =
  "No se pudo determinar la última lectura guardada. La recuperación se detuvo. Iniciá una sesión nueva.";

const LAB_ERROR_NO_QUALITY = "El backend no devolvió el informe de calidad de las lecturas guardadas.";

export type LabPhase =
  | "idle"
  | "seeding"
  | "normal"
  | "injecting-anomaly"
  | "anomaly"
  | "interrupting"
  | "interrupted"
  | "recovering"
  | "recovered"
  | "drying"
  | "drought"
  | "error";

export interface LabLogEntry {
  id: string;
  scenario: "A" | "B" | "C" | "D" | "E";
  message: string;
}

/** Tipo de lectura de la sesión, para distinguirla en los gráficos. */
export type LabReadingKind = "normal" | "anomaly" | "dry";

/** Una lectura sintética ya aceptada por el backend. */
export interface LabSeriesPoint {
  date: string;
  values: LabReadingValues;
  kind: LabReadingKind;
}

interface UseSensorLabScenariosOptions {
  /** Se dispara tras cada ingesta confirmada, para refrescar paneles de
   * solo lectura (p. ej. `QualityPanel`) sin acoplar este hook a ellos. */
  onIngested: () => void;
  /** Delegado al workspace de pronóstico ya existente
   * (`useForecastWorkspace`); este hook nunca llama al pipeline
   * directamente. */
  runForecast: () => Promise<void>;
  /** Semilla del generador; por defecto `LAB_SEED`. */
  seed?: number;
}

export interface SensorLabScenarios {
  phase: LabPhase;
  busy: boolean;
  error: string | null;
  log: LabLogEntry[];
  clockDate: string | null;
  lastQuality: QualityReport | null;
  /** Lecturas aceptadas por el backend en esta sesión, en orden de fecha. */
  readings: LabSeriesPoint[];
  runScenarioA: () => Promise<void>;
  runScenarioB: () => Promise<void>;
  runScenarioC: () => Promise<void>;
  runScenarioD: () => Promise<void>;
  runScenarioE: () => Promise<void>;
}

/** Señal interna: la ejecución dejó de ser vigente (pantalla desmontada
 * o sesión reemplazada). No es un error de escenario y no se muestra. */
class StaleRun extends Error {}

interface RunContext {
  sensorId: string;
  /** Lanza `StaleRun` si la ejecución fue invalidada. Se invoca antes de
   * cada solicitud nueva y después de cada `await`. */
  ensure: () => void;
}

/**
 * Orquestación cliente del laboratorio (tercer modo de la UI de defensa):
 * un `sensor_id` propio por sesión, avance de escenarios A→B→C→D→E
 * (más el paso E de sequía) mediante los endpoints reales de `alerting-ui`
 * (`POST /sensors/{id}/readings`, `GET /quality/{id}`,
 * `POST /forecast/{id}/run` vía `runForecast`), nunca un backend
 * paralelo.
 *
 * Ciclo de vida: cada ejecución captura una generación; desmontar la
 * pantalla o cambiar de `sensorId` la invalida. Una ejecución invalidada
 * no inicia solicitudes nuevas ni modifica el estado de la sesión
 * vigente. Cancelar en el cliente no revierte un POST ya enviado: si el
 * servidor lo recibió, sus datos se conservan.
 *
 * Reintentos: una sesión con error no admite nuevos pasos (evita
 * reenviar valores distintos para fechas ya aceptadas); la salida es una
 * sesión nueva con otro `sensor_id`, semilla y calendario reiniciados.
 */
export function useSensorLabScenarios(
  sensorId: string,
  options: UseSensorLabScenariosOptions,
): SensorLabScenarios {
  const generationRef = useRef(0);
  const runningRef = useRef(false);
  const phaseRef = useRef<LabPhase>("idle");
  const clockRef = useRef<string | null>(null);
  const rngRef = useRef(mulberry32(LAB_SEED));
  const prevValuesRef = useRef<LabReadingValues | null>(null);
  const dayIndexRef = useRef(0);
  const readingsRef = useRef<LabSeriesPoint[]>([]);
  const optionsRef = useRef(options);
  useLayoutEffect(() => {
    optionsRef.current = options;
  });

  const [trackedSensorId, setTrackedSensorId] = useState(sensorId);
  const [phase, setPhaseState] = useState<LabPhase>("idle");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [log, setLog] = useState<LabLogEntry[]>([]);
  const [clockDate, setClockState] = useState<string | null>(null);
  const [lastQuality, setLastQuality] = useState<QualityReport | null>(null);
  const [readings, setReadings] = useState<LabSeriesPoint[]>([]);

  if (sensorId !== trackedSensorId) {
    setTrackedSensorId(sensorId);
    setPhaseState("idle");
    setBusy(false);
    setError(null);
    setLog([]);
    setClockState(null);
    setLastQuality(null);
    setReadings([]);
  }

  // Inicio de ciclo de vida (montaje o nuevo sensor): reinicia el estado
  // sincrónico. La limpieza (desmontaje o cambio de sensor) invalida toda
  // ejecución en curso. Bajo StrictMode, montaje→limpieza→montaje deja una
  // generación nueva y vigente antes de cualquier acción de la persona.
  useLayoutEffect(() => {
    generationRef.current += 1;
    runningRef.current = false;
    phaseRef.current = "idle";
    clockRef.current = null;
    rngRef.current = mulberry32(optionsRef.current.seed ?? LAB_SEED);
    prevValuesRef.current = null;
    dayIndexRef.current = 0;
    readingsRef.current = [];
    return () => {
      generationRef.current += 1;
      runningRef.current = false;
    };
  }, [sensorId]);

  function setPhase(next: LabPhase) {
    phaseRef.current = next;
    setPhaseState(next);
  }

  function setClock(next: string) {
    clockRef.current = next;
    setClockState(next);
  }

  function appendLog(scenario: LabLogEntry["scenario"], message: string) {
    setLog((prev) => [...prev, { id: `${scenario}-${prev.length}-${Date.now()}`, scenario, message }]);
  }

  async function withStep(
    required: LabPhase,
    nextPhase: LabPhase,
    action: (ctx: RunContext) => Promise<void>,
  ) {
    // Bloqueo síncrono (no depende del estado React `busy`) y orden A→B→C→D.
    if (runningRef.current || phaseRef.current !== required) return;
    runningRef.current = true;
    const generation = generationRef.current;
    const ctx: RunContext = {
      sensorId,
      ensure: () => {
        if (generationRef.current !== generation) throw new StaleRun();
      },
    };
    setBusy(true);
    setPhase(nextPhase);
    setError(null);
    try {
      await action(ctx);
    } catch (err) {
      if (!(err instanceof StaleRun) && generationRef.current === generation) {
        setError(userFacingErrorMessage(err));
        setPhase("error");
      }
    } finally {
      if (generationRef.current === generation) {
        runningRef.current = false;
        setBusy(false);
        setReadings([...readingsRef.current]);
      }
    }
  }

  async function refreshQuality(ctx: RunContext, missingMessage = LAB_ERROR_NO_QUALITY): Promise<QualityReport> {
    ctx.ensure();
    const report = await getQualityReport(ctx.sensorId);
    ctx.ensure();
    if (report === null) throw new Error(missingMessage);
    setLastQuality(report);
    return report;
  }

  /** Siguiente lectura del generador de balance hídrico (el estado es la lectura previa y el día del ciclo). */
  function nextReading(dry = false): LabReadingValues {
    const reading = generateWaterBalanceReading(prevValuesRef.current, rngRef.current, dayIndexRef.current, { dry });
    dayIndexRef.current += 1;
    return reading;
  }

  async function ingest(ctx: RunContext, isoDate: string, reading: LabReadingValues, kind: LabReadingKind = "normal") {
    ctx.ensure();
    await ingestLabReading(ctx.sensorId, isoDate, reading);
    ctx.ensure();
    prevValuesRef.current = reading;
    readingsRef.current.push({ date: isoDate, values: reading, kind });
  }

  async function forecast(ctx: RunContext) {
    ctx.ensure();
    await optionsRef.current.runForecast();
    ctx.ensure();
  }

  async function runScenarioA() {
    await withStep("idle", "seeding", async (ctx) => {
      const endDate = labBackfillEndDateUtc();
      const startDate = addDaysUtc(endDate, -(LAB_HISTORY_DAYS - 1));
      let cursor = startDate;
      for (let i = 0; i < LAB_HISTORY_DAYS; i += 1) {
        await ingest(ctx, cursor, nextReading());
        cursor = addDaysUtc(cursor, 1);
      }
      setClock(endDate);
      const report = await refreshQuality(ctx);
      optionsRef.current.onIngested();
      appendLog(
        "A",
        `Historial sintético cargado: ${report.total_rows} lecturas normales, del ${startDate} al ${endDate} (confirmado por GET /quality).`,
      );
      await forecast(ctx);
      setPhase("normal");
    });
  }

  async function runScenarioB() {
    await withStep("normal", "injecting-anomaly", async (ctx) => {
      const anomalyDate = addDaysUtc(clockRef.current as string, 1);
      const reading = injectRangeAnomaly(nextReading());
      await ingest(ctx, anomalyDate, reading, "anomaly");
      setClock(anomalyDate);
      const report = await refreshQuality(ctx);
      optionsRef.current.onIngested();
      const flagged = report.out_of_range.temperature ?? [];
      const wasFlagged = flagged.some((d) => d.startsWith(anomalyDate));
      appendLog(
        "B",
        wasFlagged
          ? `Lectura del ${anomalyDate} marcada por el control de calidad: temperatura ${reading.temperature.toFixed(1)} °C fuera del rango físico esperado (motivo real: out_of_range.temperature de GET /quality). Es una anomalía de medición, no una alerta de estrés hídrico.`
          : `Lectura del ${anomalyDate} ingerida (temperatura ${reading.temperature.toFixed(1)} °C); el control de calidad no la marcó fuera de rango en esta consulta -- se muestra el resultado real devuelto, no el esperado.`,
      );
      await forecast(ctx);
      setPhase("anomaly");
    });
  }

  async function runScenarioC() {
    await withStep("anomaly", "interrupting", async (ctx) => {
      const interruptedThrough = addDaysUtc(clockRef.current as string, LAB_GAP_DAYS);
      setClock(interruptedThrough);
      const report = await refreshQuality(ctx);
      appendLog(
        "C",
        `Interrupción simulada: el generador dejó de enviar lecturas durante ${LAB_GAP_DAYS} días simulados (no se desconectó ningún dispositivo físico). El reloj simulado avanzó al ${interruptedThrough}, pero la última lectura guardada sigue siendo del ${report.period_end ?? "sin dato"} (${report.total_rows} filas totales, sin cambio). No se vuelve a pedir un pronóstico: no hay datos nuevos que lo sustenten.`,
      );
      setPhase("interrupted");
    });
  }

  async function runScenarioD() {
    await withStep("interrupted", "recovering", async (ctx) => {
      const before = await refreshQuality(ctx, LAB_ERROR_NO_LAST_READING);
      const lastConfirmed = before.period_end;
      if (!lastConfirmed) throw new Error(LAB_ERROR_NO_LAST_READING);
      let cursor = addDaysUtc(lastConfirmed, 1);
      const recoveryEnd = clockRef.current as string;
      while (cursor <= recoveryEnd) {
        await ingest(ctx, cursor, nextReading());
        cursor = addDaysUtc(cursor, 1);
      }
      const report = await refreshQuality(ctx);
      optionsRef.current.onIngested();
      appendLog(
        "D",
        `Se generaron y enviaron lecturas sintéticas para las fechas pendientes hasta el ${report.period_end ?? "?"} (${report.total_rows} filas totales, confirmado por el backend).`,
      );
      await forecast(ctx);
      appendLog(
        "D",
        "Se solicitó un nuevo pronóstico; su resultado, o el motivo real si no pudo emitirse, se muestra más abajo.",
      );
      setPhase("recovered");
    });
  }

  /** Paso E: racha seca y calurosa sin lluvia; la humedad del suelo cae y se pide un pronóstico nuevo. */
  async function runScenarioE() {
    await withStep("recovered", "drying", async (ctx) => {
      let cursor = addDaysUtc(clockRef.current as string, 1);
      for (let i = 0; i < LAB_DRY_DAYS; i += 1) {
        await ingest(ctx, cursor, nextReading(true), "dry");
        setClock(cursor);
        cursor = addDaysUtc(cursor, 1);
      }
      const report = await refreshQuality(ctx);
      optionsRef.current.onIngested();
      appendLog(
        "E",
        `Sequía simulada: ${LAB_DRY_DAYS} días secos y calurosos, sin lluvia, hasta el ${clockRef.current} (${report.total_rows} filas totales, confirmado por el backend). La humedad del suelo generada baja de forma sostenida.`,
      );
      await forecast(ctx);
      appendLog(
        "E",
        "Se solicitó un nuevo pronóstico; su resultado real, alerta o sin alerta, se muestra en el panel de pronóstico.",
      );
      setPhase("drought");
    });
  }

  return {
    phase,
    busy,
    error,
    log,
    clockDate,
    lastQuality,
    readings,
    runScenarioA,
    runScenarioB,
    runScenarioC,
    runScenarioD,
    runScenarioE,
  };
}
