import { describe, expect, it } from "vitest";
import { daysBetweenIso, isoDayRange } from "./dateUtils";

describe("daysBetweenIso", () => {
  it("returns 0 for the same date", () => {
    expect(daysBetweenIso("2024-10-19", "2024-10-19")).toBe(0);
  });
  it("returns a positive count forward", () => {
    expect(daysBetweenIso("2024-10-19", "2024-10-22")).toBe(3);
  });
  it("returns a negative count backward", () => {
    expect(daysBetweenIso("2024-10-22", "2024-10-19")).toBe(-3);
  });
  it("handles a month boundary", () => {
    expect(daysBetweenIso("2024-10-30", "2024-11-02")).toBe(3);
  });
});

describe("isoDayRange", () => {
  it("includes both endpoints, one entry per calendar day", () => {
    expect(isoDayRange("2024-10-19", "2024-10-22")).toEqual([
      "2024-10-19",
      "2024-10-20",
      "2024-10-21",
      "2024-10-22",
    ]);
  });
  it("returns an empty list when the range is inverted", () => {
    expect(isoDayRange("2024-10-22", "2024-10-19")).toEqual([]);
  });
});
