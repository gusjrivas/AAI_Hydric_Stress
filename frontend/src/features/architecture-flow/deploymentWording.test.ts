import { describe, expect, it } from "vitest";
import { DEPLOYMENT_COMPONENTS, DEPLOYMENT_TOUR } from "./deploymentCatalog";

describe("deployment wording follows the memoria", () => {
  it("names the combination as an average with an agreement indicator, not as an agreement ensemble", () => {
    const models = DEPLOYMENT_COMPONENTS.find((c) => c.id === "modelos")!;
    expect(models.lines.join(" ")).toMatch(/ensamble · promedio/i);
    const step = DEPLOYMENT_TOUR.find((s) => s.id === "p4")!;
    expect(step.caption).toMatch(/promedio/i);
    expect(step.caption).not.toMatch(/ensamble por acuerdo/i);
  });

  it("does not present the model output as a risk estimate", () => {
    const step = DEPLOYMENT_TOUR.find((s) => s.id === "p4")!;
    expect(step.caption).not.toMatch(/estiman el riesgo/i);
    expect(step.caption).toMatch(/baja humedad/i);
  });
});
