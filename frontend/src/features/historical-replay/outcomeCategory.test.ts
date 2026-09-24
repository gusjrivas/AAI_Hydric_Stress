import { describe, expect, it } from "vitest";
import {
  distanceToThreshold,
  formatDistanceToThreshold,
  outcomeCategory,
} from "./outcomeCategory";

describe("outcomeCategory", () => {
  it("classifies a true positive as 'alerta correcta'", () => {
    expect(outcomeCategory(1, 1)).toBe("alerta_correcta");
  });
  it("classifies a false positive as 'falsa alerta'", () => {
    expect(outcomeCategory(1, 0)).toBe("falsa_alerta");
  });
  it("classifies a false negative as 'omisión de alerta'", () => {
    expect(outcomeCategory(0, 1)).toBe("omision_alerta");
  });
  it("classifies a true negative as 'ausencia de alerta correcta'", () => {
    expect(outcomeCategory(0, 0)).toBe("ausencia_correcta");
  });
});

describe("distanceToThreshold", () => {
  it("is negative and 'por_debajo' when the observation is under the threshold", () => {
    const distance = distanceToThreshold(0.28, { umbral: 0.3, unidad: "m3/m3" });
    expect(distance.value).toBeCloseTo(-0.02);
    expect(distance.relation).toBe("por_debajo");
    expect(distance.unit).toBe("m3/m3");
  });

  it("is positive and 'por_encima' when the observation is over the threshold", () => {
    const distance = distanceToThreshold(0.4, { umbral: 0.3, unidad: "m3/m3" });
    expect(distance.value).toBeCloseTo(0.1);
    expect(distance.relation).toBe("por_encima");
  });

  it("formats with an explicit sign, unit and relation, never as a model error", () => {
    const text = formatDistanceToThreshold(distanceToThreshold(0.28, { umbral: 0.3, unidad: "m3/m3" }));
    expect(text).toContain("m3/m3");
    expect(text).toContain("por debajo del umbral");
    expect(text.startsWith("-")).toBe(true);
    expect(text).not.toMatch(/error/i);
  });
});
