import { useCallback, useEffect, useRef, useState } from "react";
import type { LabPhase, SensorLabScenarios } from "./useSensorLabScenarios";

/** Pausa entre pasos de la demostración automática, para que cada resultado se vea. */
export const LAB_DEMO_PAUSE_MS = 6000;

/** Lo mínimo del laboratorio que necesita la demostración automática. */
export type LabDemoSource = Pick<
  SensorLabScenarios,
  "phase" | "busy" | "runScenarioA" | "runScenarioB" | "runScenarioC" | "runScenarioD" | "runScenarioE"
>;

type StepName = "runScenarioA" | "runScenarioB" | "runScenarioC" | "runScenarioD" | "runScenarioE";

/** Cada paso con la fase desde la que puede ejecutarse. */
const STEPS: readonly { run: StepName; from: LabPhase }[] = [
  { run: "runScenarioA", from: "idle" },
  { run: "runScenarioB", from: "normal" },
  { run: "runScenarioC", from: "anomaly" },
  { run: "runScenarioD", from: "interrupted" },
  { run: "runScenarioE", from: "recovered" },
];

/**
 * Demostración automática: ejecuta los pasos pendientes del laboratorio, de a uno,
 * con una pausa entre ellos. Usa las mismas funciones que los botones, así que llama
 * al pipeline real. Se puede detener, y se detiene sola ante un error o al desmontar.
 */
export function useLabDemoRun(lab: LabDemoSource, pauseMs: number = LAB_DEMO_PAUSE_MS) {
  const labRef = useRef(lab);
  const runningRef = useRef(false);
  const cancelRef = useRef(false);
  const wakeRef = useRef<(() => void) | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    labRef.current = lab;
  });

  const stop = useCallback(() => {
    cancelRef.current = true;
    wakeRef.current?.();
    runningRef.current = false;
    setRunning(false);
  }, []);

  useEffect(() => stop, [stop]);

  const start = useCallback(() => {
    if (runningRef.current || labRef.current.busy) return;
    const first = STEPS.findIndex((step) => step.from === labRef.current.phase);
    if (first < 0) return;
    runningRef.current = true;
    cancelRef.current = false;
    setRunning(true);

    const sleep = () =>
      new Promise<void>((resolve) => {
        const timer = setTimeout(resolve, pauseMs);
        wakeRef.current = () => {
          clearTimeout(timer);
          resolve();
        };
      });

    void (async () => {
      for (let index = first; index < STEPS.length; index += 1) {
        if (cancelRef.current) return;
        await labRef.current[STEPS[index].run]();
        if (cancelRef.current || index === STEPS.length - 1) break;
        await sleep();
        if (cancelRef.current || labRef.current.phase === "error") break;
      }
      if (!cancelRef.current) {
        runningRef.current = false;
        setRunning(false);
      }
    })();
  }, [pauseMs]);

  return { running, start, stop };
}
