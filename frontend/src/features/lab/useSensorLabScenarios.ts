import { useLayoutEffect, useRef, useState } from "react";
import { getQualityReport } from "../quality/api";
import type { QualityReport } from "../quality/api";
import { addDaysUtc, labBackfillEndDateUtc } from "./labSensor";
import { generateNormalReading, injectRangeAnomaly, mulberry32 } from "./readingGenerator";
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
  | "error";

export interface LabLogEntry {
  id: string;
  scenario: "A" | "B" | "C" | "D";
  message: string;
}

interface UseSensorLabScenariosOptions {
  /** Se dispara tras cada ingesta confirmada, para refrescar paneles de
   * solo lectura (p. ej. `QualityPanel`) sin acoplar este hook a ellos. */
  onIngested: () => void;
  /** Delegado al workspace de pronóstico ya existente
   * (`useForecastWorkspace`); este hook nunca llama al pipeline
   * directamente. */
  runForecast: () => Promise<void>;
}

export interface SensorLabScenarios {
  phase: LabPhase;
  busy: boolean;
  error: string | null;
  log: LabLogEntry[];
  clockDate: string | null;
  lastQuality: QualityReport | null;
  runScenarioA: () => Promise<void>;
  runScenarioB: () => Promise<void>;
  runScenarioC: () => Promise<void>;
  runScenarioD: () => Promise<void>;
}

/**
 * Orquestación cliente del laboratorio (tercer modo de la UI de defensa):
 * un `sensor_id` propio por sesión, avance de escenarios A→B→C→D
 * mediante los endpoints reales de `alerting-ui`
 * (`POST /sensors/{id}/readings`, `GET /quality/{id}`,
 * `POST /forecast/{id}/run` vía `runForecast`), nunca un backend
 * paralelo. Sigue el mismo patrón de invalidación de respuestas tardías
 * que `useForecastWorkspace`: una referencia de sensor + un token de
 * sesión que se incrementa al cambiar de `sensor_id` (reinicio),
 * comparados antes de aplicar cualquier resultado asíncrono.
 */
export function useSensorLabScenarios(
  sensorId: string,
  options: UseSensorLabScenariosOptions,
): SensorLabScenarios {
  const sensorRef = useRef(sensorId);
  const tokenRef = useRef(0);
  const rngRef = useRef(mulberry32(LAB_SEED));
  const prevValuesRef = useRef<LabReadingValues | null>(null);

  const [trackedSensorId, setTrackedSensorId] = useState(sensorId);
  const [phase, setPhase] = useState<LabPhase>("idle");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [log, setLog] = useState<LabLogEntry[]>([]);
  const [clockDate, setClockDate] = useState<string | null>(null);
  const [lastQuality, setLastQuality] = useState<QualityReport | null>(null);

  if (sensorId !== trackedSensorId) {
    setTrackedSensorId(sensorId);
    setPhase("idle");
    setBusy(false);
    setError(null);
    setLog([]);
    setClockDate(null);
    setLastQuality(null);
  }

  useLayoutEffect(() => {
    if (sensorRef.current !== sensorId) {
      tokenRef.current += 1;
      rngRef.current = mulberry32(LAB_SEED);
      prevValuesRef.current = null;
    }
    sensorRef.current = sensorId;
  }, [sensorId]);

  function appendLog(scenario: LabLogEntry["scenario"], message: string) {
    setLog((prev) => [...prev, { id: `${scenario}-${prev.length}-${Date.now()}`, scenario, message }]);
  }

  function isCurrent(sensorAtCall: string, tokenAtCall: number): boolean {
    return sensorRef.current === sensorAtCall && tokenRef.current === tokenAtCall;
  }

  async function withStep(nextPhase: LabPhase, action: (sensorAtCall: string, tokenAtCall: number) => Promise<void>) {
    if (busy) return;
    const sensorAtCall = sensorId;
    const tokenAtCall = tokenRef.current;
    setBusy(true);
    setPhase(nextPhase);
    setError(null);
    try {
      await action(sensorAtCall, tokenAtCall);
    } catch (err) {
      if (isCurrent(sensorAtCall, tokenAtCall)) {
        setError((err as Error).message);
        setPhase("error");
      }
    } finally {
      if (isCurrent(sensorAtCall, tokenAtCall)) setBusy(false);
    }
  }

  async function refreshQuality(sensorAtCall: string, tokenAtCall: number): Promise<QualityReport | null> {
    const report = await getQualityReport(sensorAtCall);
    if (!isCurrent(sensorAtCall, tokenAtCall)) return null;
    setLastQuality(report);
    return report;
  }

  async function runScenarioA() {
    await withStep("seeding", async (sensorAtCall, tokenAtCall) => {
      const endDate = labBackfillEndDateUtc();
      const startDate = addDaysUtc(endDate, -(LAB_HISTORY_DAYS - 1));
      let cursor = startDate;
      for (let i = 0; i < LAB_HISTORY_DAYS; i += 1) {
        const reading = generateNormalReading(prevValuesRef.current, rngRef.current);
        await ingestLabReading(sensorAtCall, cursor, reading);
        if (!isCurrent(sensorAtCall, tokenAtCall)) return;
        prevValuesRef.current = reading;
        cursor = addDaysUtc(cursor, 1);
      }
      setClockDate(endDate);
      const report = await refreshQuality(sensorAtCall, tokenAtCall);
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      options.onIngested();
      appendLog(
        "A",
        `Historial sintético cargado: ${report?.total_rows ?? "?"} lecturas normales, del ${startDate} al ${endDate} (confirmado por GET /quality).`,
      );
      await options.runForecast();
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      setPhase("normal");
    });
  }

  async function runScenarioB() {
    if (!clockDate) return;
    await withStep("injecting-anomaly", async (sensorAtCall, tokenAtCall) => {
      const anomalyDate = addDaysUtc(clockDate, 1);
      const base = generateNormalReading(prevValuesRef.current, rngRef.current);
      const reading = injectRangeAnomaly(base);
      await ingestLabReading(sensorAtCall, anomalyDate, reading);
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      prevValuesRef.current = reading;
      setClockDate(anomalyDate);
      const report = await refreshQuality(sensorAtCall, tokenAtCall);
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      options.onIngested();
      const flagged = report?.out_of_range.temperature ?? [];
      const wasFlagged = flagged.some((d) => d.startsWith(anomalyDate));
      appendLog(
        "B",
        wasFlagged
          ? `Lectura del ${anomalyDate} marcada por el backend: temperatura ${reading.temperature.toFixed(1)} °C fuera del rango físico esperado (motivo real: out_of_range.temperature de GET /quality).`
          : `Lectura del ${anomalyDate} ingerida (temperatura ${reading.temperature.toFixed(1)} °C); el backend no la marcó en out_of_range en esta consulta -- se muestra el resultado real devuelto, no el esperado.`,
      );
      await options.runForecast();
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      setPhase("anomaly");
    });
  }

  async function runScenarioC() {
    if (!clockDate) return;
    await withStep("interrupting", async (sensorAtCall, tokenAtCall) => {
      const interruptedThrough = addDaysUtc(clockDate, LAB_GAP_DAYS);
      setClockDate(interruptedThrough);
      const report = await refreshQuality(sensorAtCall, tokenAtCall);
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      appendLog(
        "C",
        `Sin nuevas lecturas durante ${LAB_GAP_DAYS} días simulados: el reloj simulado avanzó al ${interruptedThrough}, pero la última lectura confirmada por el backend sigue siendo del ${report?.period_end ?? "sin dato"} (${report?.total_rows ?? "?"} filas totales, sin cambio). No se vuelve a pedir un pronóstico: no hay datos nuevos que lo sustenten.`,
      );
      setPhase("interrupted");
    });
  }

  async function runScenarioD() {
    if (!clockDate) return;
    await withStep("recovering", async (sensorAtCall, tokenAtCall) => {
      const before = await refreshQuality(sensorAtCall, tokenAtCall);
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      const lastConfirmed = before?.period_end;
      if (!lastConfirmed) {
        appendLog("D", "No se pudo confirmar la última lectura antes de reanudar; se aborta la recuperación.");
        return;
      }
      let cursor = addDaysUtc(lastConfirmed, 1);
      const recoveryEnd = clockDate;
      while (cursor <= recoveryEnd) {
        const reading = generateNormalReading(prevValuesRef.current, rngRef.current);
        await ingestLabReading(sensorAtCall, cursor, reading);
        if (!isCurrent(sensorAtCall, tokenAtCall)) return;
        prevValuesRef.current = reading;
        cursor = addDaysUtc(cursor, 1);
      }
      const report = await refreshQuality(sensorAtCall, tokenAtCall);
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      options.onIngested();
      appendLog(
        "D",
        `Lecturas reanudadas hasta el ${report?.period_end ?? "?"} (${report?.total_rows ?? "?"} filas totales, confirmado por el backend).`,
      );
      await options.runForecast();
      if (!isCurrent(sensorAtCall, tokenAtCall)) return;
      appendLog("D", "Pronóstico vuelto a ejecutar con las lecturas recuperadas; ver disponibilidad real más abajo (train_rows/test_rows o el motivo si no se pudo emitir).");
      setPhase("recovered");
    });
  }

  return {
    phase,
    busy,
    error,
    log,
    clockDate,
    lastQuality,
    runScenarioA,
    runScenarioB,
    runScenarioC,
    runScenarioD,
  };
}
