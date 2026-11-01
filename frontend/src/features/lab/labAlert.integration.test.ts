/**
 * Verificación de integración del laboratorio contra el backend REAL.
 *
 * Solo corre si se define `LAB_BACKEND_URL` (y `VITE_API_BASE_URL` con el mismo valor); en `npm test` se omite.
 * Comprueba que la semilla fija del laboratorio reproduce el contraste que la demostración muestra: sin alerta
 * después de la lectura anómala (B) y de la recuperación (D), y alerta después de la sequía (E).
 *
 *   LAB_BACKEND_URL=http://127.0.0.1:18299 VITE_API_BASE_URL=http://127.0.0.1:18299 \
 *     npx vitest run src/features/lab/labAlert.integration.test.ts
 *
 * `LAB_SWEEP=1,2,3` agrega un barrido informativo de otras semillas. Si se define `LAB_REPORT_FILE`, los
 * resultados también se agregan a ese archivo (Vitest oculta `console.log` de las pruebas que pasan).
 * Cada corrida crea un sensor de prueba descartable en el backend indicado.
 */
import { appendFileSync } from "node:fs";
import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { API_BASE_URL } from "../../api/baseUrl";
import { runForecast } from "../forecast/api";
import { LAB_SEED, useSensorLabScenarios } from "./useSensorLabScenarios";

const BACKEND = process.env.LAB_BACKEND_URL;
const SWEEP = (process.env.LAB_SWEEP ?? "")
  .split(",")
  .map((value) => Number(value.trim()))
  .filter((value) => Number.isInteger(value) && value > 0);

interface Verdict {
  alerta: boolean;
  probabilidad: number;
}
interface Outcome {
  seed: number;
  A: Verdict | null;
  B: Verdict | null;
  D: Verdict | null;
  E: Verdict | null;
  /** Primer paso que terminó en error, con el motivo real del backend. */
  error?: string;
}

/** Recorre A a E con el pipeline real y devuelve el veredicto de cada pronóstico (A, B, D y E). */
async function sessionOutcome(seed: number): Promise<Outcome> {
  const sensorId = `lab-it-${seed}-${Date.now().toString(36)}`;
  const verdicts: Verdict[] = [];
  const hook = renderHook(() =>
    useSensorLabScenarios(sensorId, {
      onIngested: () => {},
      seed,
      runForecast: async () => {
        const response = await runForecast(sensorId);
        const last = response.verdicts[response.verdicts.length - 1];
        verdicts.push({ alerta: last.alerta, probabilidad: last.probabilidad });
      },
    }),
  );
  let error: string | undefined;
  for (const step of ["A", "B", "C", "D", "E"] as const) {
    await act(async () => {
      await hook.result.current[`runScenario${step}` as const]();
    });
    if (hook.result.current.phase === "error") {
      error = `paso ${step}: ${hook.result.current.error}`;
      break;
    }
  }
  hook.unmount();
  const [a = null, b = null, d = null, e = null] = verdicts;
  return { seed, A: a, B: b, D: d, E: e, error };
}

const label = (verdict: Verdict | null) =>
  verdict ? `${verdict.alerta ? "ALERTA" : "-"} ${verdict.probabilidad.toFixed(2)}` : "sin pronóstico";
function report(text: string) {
  console.log(text);
  if (process.env.LAB_REPORT_FILE) appendFileSync(process.env.LAB_REPORT_FILE, `${text}\n`);
}
const describe_ = (outcome: Outcome) =>
  `A ${label(outcome.A)} | B ${label(outcome.B)} | D ${label(outcome.D)} | E ${label(outcome.E)}${outcome.error ? ` | ERROR ${outcome.error}` : ""}`;

describe.skipIf(!BACKEND)("laboratorio contra el backend real", () => {
  it("apunta al backend indicado", () => {
    expect(API_BASE_URL).toBe(BACKEND);
  });

  it(
    "con la semilla fija: sin alerta tras B y D, y alerta tras la sequía (E)",
    async () => {
      const outcome = await sessionOutcome(LAB_SEED);
      report(`semilla ${LAB_SEED}: ${describe_(outcome)}`);
      expect(outcome.error, "ningún paso debe terminar en error").toBeUndefined();
      expect(outcome.A?.alerta, "A no debe alertar").toBe(false);
      expect(outcome.B?.alerta, "B no debe alertar").toBe(false);
      expect(outcome.D?.alerta, "D no debe alertar").toBe(false);
      expect(outcome.E?.alerta, "E debe alertar").toBe(true);
    },
    240_000,
  );

  it.runIf(SWEEP.length > 0)(
    "barrido informativo de semillas",
    async () => {
      const lines: string[] = [];
      let ok = 0;
      for (const seed of SWEEP) {
        const outcome = await sessionOutcome(seed);
        const meets =
          !outcome.error && outcome.A?.alerta === false && outcome.B?.alerta === false && outcome.D?.alerta === false && outcome.E?.alerta === true;
        ok += meets ? 1 : 0;
        const line = `semilla ${String(seed).padStart(3)} | ${describe_(outcome)}${meets ? "  <-- cumple" : ""}`;
        lines.push(line);
        report(line);
      }
      report(`cumplen: ${ok} de ${SWEEP.length}`);
      expect(lines.length).toBe(SWEEP.length);
    },
    SWEEP.length * 240_000 || 1,
  );
});
