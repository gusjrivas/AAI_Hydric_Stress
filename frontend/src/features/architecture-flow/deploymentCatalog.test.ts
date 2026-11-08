import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { DEPLOYMENT_COMPONENTS, DEPLOYMENT_EDGES, DEPLOYMENT_TOUR } from "./deploymentCatalog";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../../../..");
const FORBIDDEN = /en ejecución|en curso|en tiempo real|latencia|trazas?|\d+\s?ms\b/i;

function allText(): string[] {
  return [
    ...DEPLOYMENT_COMPONENTS.flatMap((c) => [c.label, ...c.lines, c.responsibility, c.connections, c.limits]),
    ...DEPLOYMENT_EDGES.map((e) => e.label ?? ""),
    ...DEPLOYMENT_TOUR.map((s) => s.caption),
  ];
}

describe("deployment catalog", () => {
  it("declares the technical components of the Docker Compose deployment", () => {
    const ids = DEPLOYMENT_COMPONENTS.map((c) => c.id);
    for (const id of ["frontend", "backend", "nucleo", "modelos", "mlflow", "postgres", "minio"]) {
      expect(ids).toContain(id);
    }
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("points every evidence reference to an existing repository path", () => {
    for (const component of DEPLOYMENT_COMPONENTS) {
      expect(component.evidence.length, component.id).toBeGreaterThan(0);
      for (const path of component.evidence) {
        expect(existsSync(resolve(REPO_ROOT, path)), `${component.id}: ${path}`).toBe(true);
      }
    }
  });

  it("only declares ports that appear in docker-compose.yml", () => {
    const compose = readFileSync(resolve(REPO_ROOT, "docker-compose.yml"), "utf-8");
    for (const component of DEPLOYMENT_COMPONENTS) {
      for (const port of component.ports ?? []) {
        expect(compose, `${component.id}: ${port}`).toContain(port);
      }
    }
  });

  it("connects only declared components", () => {
    const ids = new Set(DEPLOYMENT_COMPONENTS.map((c) => c.id));
    for (const edge of DEPLOYMENT_EDGES) {
      expect(ids.has(edge.from), `${edge.id}.from`).toBe(true);
      expect(ids.has(edge.to), `${edge.id}.to`).toBe(true);
    }
  });

  it("builds a tour whose steps reference existing components and connections", () => {
    const ids = new Set(DEPLOYMENT_COMPONENTS.map((c) => c.id));
    const edgeIds = new Set(DEPLOYMENT_EDGES.map((e) => e.id));
    expect(DEPLOYMENT_TOUR.length).toBeGreaterThanOrEqual(9);
    for (const step of DEPLOYMENT_TOUR) {
      expect(step.caption.trim().length, step.id).toBeGreaterThan(0);
      for (const id of step.nodes) expect(ids.has(id), `${step.id}: ${id}`).toBe(true);
      for (const id of step.edges) expect(edgeIds.has(id), `${step.id}: ${id}`).toBe(true);
    }
  });

  it("registers MLflow only on the recalibration step, never on the forecast", () => {
    const mlflowSteps = DEPLOYMENT_TOUR.filter((s) => s.nodes.includes("mlflow"));
    expect(mlflowSteps.length).toBeGreaterThan(0);
    const firstMlflow = DEPLOYMENT_TOUR.indexOf(mlflowSteps[0]);
    const feedbackStep = DEPLOYMENT_TOUR.findIndex((s) => /retroalimentación|revisa/i.test(s.caption));
    expect(feedbackStep).toBeGreaterThanOrEqual(0);
    expect(firstMlflow).toBeGreaterThan(feedbackStep);
    expect(DEPLOYMENT_TOUR[firstMlflow].caption).toMatch(/reajuste de un predictor individual/i);
  });

  it("keeps the ensemble review separate from the base-application recalibration circuit", () => {
    const byId = Object.fromEntries(DEPLOYMENT_TOUR.map((s) => [s.id, s]));
    expect(byId.p7.caption).toMatch(/no modifica sus modelos ni ejecuta una recalibración/);
    expect(byId.p8.caption).toMatch(/Circuito distinto: en la aplicación base/);
    expect(byId.p8.nodes).not.toContain("modelos");
    expect(byId.p9.caption).toMatch(/no actualiza los modelos del ensamble/);
  });

  it("never uses wording that suggests live execution, metrics or traces", () => {
    for (const text of allText()) expect(text).not.toMatch(FORBIDDEN);
  });
});
