import { describe, expect, it } from "vitest";
import { generateNormalReading, injectRangeAnomaly, labRangeFor, mulberry32 } from "./readingGenerator";

describe("mulberry32", () => {
  it("is deterministic for the same seed", () => {
    const a = mulberry32(42);
    const b = mulberry32(42);
    const seqA = [a(), a(), a()];
    const seqB = [b(), b(), b()];
    expect(seqA).toEqual(seqB);
  });

  it("produces different sequences for different seeds", () => {
    const a = mulberry32(42);
    const b = mulberry32(7);
    expect(a()).not.toBeCloseTo(b(), 6);
  });
});

describe("generateNormalReading", () => {
  it("stays within the documented physical ranges even after many steps", () => {
    const rand = mulberry32(42);
    let previous = null as ReturnType<typeof generateNormalReading> | null;
    for (let i = 0; i < 500; i += 1) {
      previous = generateNormalReading(previous, rand);
      for (const column of Object.keys(previous) as (keyof typeof previous)[]) {
        const [low, high] = labRangeFor(column);
        expect(previous[column]).toBeGreaterThanOrEqual(low);
        expect(previous[column]).toBeLessThanOrEqual(high);
      }
    }
  });

  it("is reproducible for the same seed (fixed-seed scenario requirement)", () => {
    const first = generateNormalReading(null, mulberry32(42));
    const second = generateNormalReading(null, mulberry32(42));
    expect(first).toEqual(second);
  });
});

describe("injectRangeAnomaly", () => {
  it("forces temperature strictly above the documented physical range", () => {
    const rand = mulberry32(42);
    const base = generateNormalReading(null, rand);
    const anomalous = injectRangeAnomaly(base);
    const [, high] = labRangeFor("temperature");
    expect(anomalous.temperature).toBeGreaterThan(high);
    // Ninguna otra variable se toca: la perturbación es explícita y acotada.
    expect(anomalous.soil_moisture).toBe(base.soil_moisture);
    expect(anomalous.relative_humidity).toBe(base.relative_humidity);
  });
});
