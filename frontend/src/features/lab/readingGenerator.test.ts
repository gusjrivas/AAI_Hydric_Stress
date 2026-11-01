import { describe, expect, it } from "vitest";
import { generateWaterBalanceReading, injectRangeAnomaly, labRangeFor, mulberry32 } from "./readingGenerator";
import type { LabReadingValues } from "./readingGenerator";

function history(seed: number, days: number): LabReadingValues[] {
  const rand = mulberry32(seed);
  const readings: LabReadingValues[] = [];
  let previous: LabReadingValues | null = null;
  for (let day = 0; day < days; day += 1) {
    previous = generateWaterBalanceReading(previous, rand, day);
    readings.push(previous);
  }
  return readings;
}

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

describe("generateWaterBalanceReading", () => {
  it("stays within the documented physical ranges even after many steps, wet or dry", () => {
    const rand = mulberry32(42);
    let previous: LabReadingValues | null = null;
    for (let day = 0; day < 500; day += 1) {
      previous = generateWaterBalanceReading(previous, rand, day, { dry: day % 40 > 25 });
      for (const column of Object.keys(previous) as (keyof LabReadingValues)[]) {
        const [low, high] = labRangeFor(column);
        expect(previous[column], `${column} día ${day}`).toBeGreaterThanOrEqual(low);
        expect(previous[column], `${column} día ${day}`).toBeLessThanOrEqual(high);
      }
    }
  });

  it("is reproducible for the same seed (fixed-seed scenario requirement)", () => {
    expect(history(42, 60)).toEqual(history(42, 60));
    expect(history(42, 60)).not.toEqual(history(7, 60));
  });

  it("builds a history with rain events that recharge the soil, not a flat or monotonic series", () => {
    const readings = history(42, 120);
    const rainDays = readings.filter((r) => r.precipitation > 0).length;
    expect(rainDays).toBeGreaterThan(10);
    expect(rainDays).toBeLessThan(80);
    const soil = readings.map((r) => r.soil_moisture);
    const rises = soil.slice(1).filter((value, i) => value > soil[i]).length;
    const falls = soil.slice(1).filter((value, i) => value < soil[i]).length;
    expect(rises).toBeGreaterThan(5);
    expect(falls).toBeGreaterThan(5);
  });

  it("dries the soil during a dry spell: no rain, hotter days and a sustained drop in moisture", () => {
    const rand = mulberry32(42);
    const wet = history(42, 120);
    let previous: LabReadingValues | null = { ...wet[wet.length - 1], soil_moisture: 0.4 };
    const start = previous.soil_moisture;
    for (let day = 120; day < 134; day += 1) {
      previous = generateWaterBalanceReading(previous, rand, day, { dry: true });
      expect(previous.precipitation).toBe(0);
    }
    expect(previous.soil_moisture).toBeLessThan(start - 0.15);
  });

  it("starts from a moderate moisture when there is no previous reading", () => {
    const first = generateWaterBalanceReading(null, mulberry32(42), 0);
    expect(first.soil_moisture).toBeGreaterThan(0.2);
    expect(first.soil_moisture).toBeLessThan(0.5);
  });
});

describe("injectRangeAnomaly", () => {
  it("forces temperature strictly above the documented physical range", () => {
    const base = history(42, 1)[0];
    const anomalous = injectRangeAnomaly(base);
    const [, high] = labRangeFor("temperature");
    expect(anomalous.temperature).toBeGreaterThan(high);
    // Ninguna otra variable se toca: la perturbación es explícita y acotada.
    expect(anomalous.soil_moisture).toBe(base.soil_moisture);
    expect(anomalous.relative_humidity).toBe(base.relative_humidity);
  });
});
