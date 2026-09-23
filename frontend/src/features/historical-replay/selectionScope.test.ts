import { describe, expect, it } from "vitest";
import { belongsToSelection, taggedFor, visibleFor } from "./selectionScope";

const LOADING = { y_pred: -1 } as const;

describe("selectionScope", () => {
  it("a result tagged for the current selection is visible", () => {
    const tagged = taggedFor("2024-10-19", "2024-10-22", { y_pred: 0 });
    expect(belongsToSelection(tagged, "2024-10-19", "2024-10-22")).toBe(true);
    expect(visibleFor(tagged, "2024-10-19", "2024-10-22", LOADING)).toEqual({ y_pred: 0 });
  });

  it("a result tagged for a different origin is not visible, regardless of matching date", () => {
    const tagged = taggedFor("2024-10-19", "2024-10-22", { y_pred: 0 });
    expect(belongsToSelection(tagged, "2024-10-20", "2024-10-22")).toBe(false);
    expect(visibleFor(tagged, "2024-10-20", "2024-10-22", LOADING)).toEqual(LOADING);
  });

  it("a result tagged for a different simulated date is not visible, regardless of matching origin", () => {
    const tagged = taggedFor("2024-10-19", "2024-10-22", { y_pred: 0 });
    expect(belongsToSelection(tagged, "2024-10-19", "2024-10-23")).toBe(false);
    expect(visibleFor(tagged, "2024-10-19", "2024-10-23", LOADING)).toEqual(LOADING);
  });

  it("this holds independently of any effect having run: it is a pure function of the tag and the live selection", () => {
    // Simula el peor caso: el resultado guardado es el de la selección
    // ANTERIOR (B), y la selección vigente ya cambió a A, sin que ningún
    // efecto haya tenido oportunidad de correr todavía.
    const staleResultFromB = taggedFor("2024-10-20", "2024-10-23", { y_pred: 1 });
    const currentSelection = { origin: "2024-10-19", date: "2024-10-22" };

    expect(
      belongsToSelection(staleResultFromB, currentSelection.origin, currentSelection.date),
    ).toBe(false);
    expect(
      visibleFor(staleResultFromB, currentSelection.origin, currentSelection.date, LOADING),
    ).toEqual(LOADING);
  });

  it("a stale result for the SAME (origin, date) pair revisited after a detour is still visible (this function does not fix ordering — the generation guard does that)", () => {
    // A→B→A: la etiqueta de un resultado obsoleto de "A" (de antes del
    // desvío por B) coincide en origen/fecha con la selección vigente
    // ("A" otra vez). `belongsToSelection` por sí sola no distingue esta
    // carrera de reingreso — para eso sigue haciendo falta el guardado por
    // generación en el efecto que resuelve la promesa (no es responsabilidad
    // de este módulo).
    const staleResultFromEarlierA = taggedFor("2024-10-19", "2024-10-22", { y_pred: 0 });
    expect(belongsToSelection(staleResultFromEarlierA, "2024-10-19", "2024-10-22")).toBe(true);
  });
});
