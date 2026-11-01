import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LAB_DEMO_PAUSE_MS, useLabDemoRun } from "./useLabDemoRun";
import type { LabDemoSource } from "./useLabDemoRun";
import type { LabPhase } from "./useSensorLabScenarios";

function fakeLab(phase: LabPhase, order: string[]): LabDemoSource {
  const step = (name: string) => vi.fn(async () => void order.push(name));
  return {
    phase,
    busy: false,
    runScenarioA: step("A"),
    runScenarioB: step("B"),
    runScenarioC: step("C"),
    runScenarioD: step("D"),
    runScenarioE: step("E"),
  };
}

/** Deja correr las promesas pendientes sin avanzar el reloj simulado. */
async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe("useLabDemoRun", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("runs A to E in order with a pause between steps", async () => {
    const order: string[] = [];
    const { result } = renderHook(() => useLabDemoRun(fakeLab("idle", order)));
    expect(result.current.running).toBe(false);

    act(() => result.current.start());
    await flush();
    expect(order).toEqual(["A"]);
    expect(result.current.running).toBe(true);

    for (const expected of ["B", "C", "D", "E"]) {
      await act(async () => void vi.advanceTimersByTime(LAB_DEMO_PAUSE_MS - 1));
      expect(order[order.length - 1]).not.toBe(expected);
      await act(async () => void vi.advanceTimersByTime(1));
      await flush();
      expect(order[order.length - 1]).toBe(expected);
    }
    expect(order).toEqual(["A", "B", "C", "D", "E"]);
    await flush();
    expect(result.current.running).toBe(false);
  });

  it("starts from the next pending step when the session is already under way", async () => {
    const order: string[] = [];
    const { result } = renderHook(() => useLabDemoRun(fakeLab("anomaly", order)));
    act(() => result.current.start());
    await flush();
    expect(order).toEqual(["C"]);
  });

  it("does nothing once the drought step has been completed", async () => {
    const order: string[] = [];
    const { result } = renderHook(() => useLabDemoRun(fakeLab("drought", order)));
    act(() => result.current.start());
    await flush();
    expect(order).toEqual([]);
    expect(result.current.running).toBe(false);
  });

  it("can be stopped between steps and then does not run anything else", async () => {
    const order: string[] = [];
    const { result } = renderHook(() => useLabDemoRun(fakeLab("idle", order)));
    act(() => result.current.start());
    await flush();
    act(() => result.current.stop());
    expect(result.current.running).toBe(false);
    await act(async () => void vi.advanceTimersByTime(LAB_DEMO_PAUSE_MS * 10));
    await flush();
    expect(order).toEqual(["A"]);
  });

  it("stops by itself when a step ends in error", async () => {
    const order: string[] = [];
    const { result, rerender } = renderHook(({ lab }) => useLabDemoRun(lab), { initialProps: { lab: fakeLab("idle", order) } });
    act(() => result.current.start());
    await flush();
    rerender({ lab: fakeLab("error", order) });
    await act(async () => void vi.advanceTimersByTime(LAB_DEMO_PAUSE_MS));
    await flush();
    expect(order).toEqual(["A"]);
    expect(result.current.running).toBe(false);
  });

  it("ignores a second start while it is running or the lab is busy", async () => {
    const order: string[] = [];
    const { result } = renderHook(() => useLabDemoRun(fakeLab("idle", order)));
    act(() => {
      result.current.start();
      result.current.start();
    });
    await flush();
    expect(order).toEqual(["A"]);

    const busy: string[] = [];
    const busyHook = renderHook(() => useLabDemoRun({ ...fakeLab("idle", busy), busy: true }));
    act(() => busyHook.result.current.start());
    await flush();
    expect(busy).toEqual([]);
  });

  it("does not keep running after unmount", async () => {
    const order: string[] = [];
    const { result, unmount } = renderHook(() => useLabDemoRun(fakeLab("idle", order)));
    act(() => result.current.start());
    await flush();
    unmount();
    await act(async () => void vi.advanceTimersByTime(LAB_DEMO_PAUSE_MS * 10));
    expect(order).toEqual(["A"]);
  });
});
