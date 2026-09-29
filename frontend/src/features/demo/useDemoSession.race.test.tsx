import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useDemoSession } from "./useDemoSession";
import * as api from "./api";
import type { DemoSessionView } from "./api";

function session(overrides: Partial<DemoSessionView> = {}): DemoSessionView {
  return {
    session_id: "s1",
    sensor_id: "demo-x",
    status: "running",
    phase: "pending",
    cursor: 3,
    days: 10,
    simulated_date: "2024-01-03",
    last_ingested_date: "2024-01-03",
    last_forecast_date: null,
    interval_seconds: 5,
    revision: 10,
    error: null,
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useDemoSession: respuestas fuera de orden", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "isDemoControlConfigured").mockReturnValue(true);
    vi.spyOn(api, "newRequestId").mockReturnValue("req");
  });

  async function mountWith(initial: DemoSessionView) {
    const getSpy = vi.spyOn(api, "getDemoSession").mockResolvedValueOnce(initial);
    const hook = renderHook(() => useDemoSession());
    await waitFor(() => expect(hook.result.current.session?.revision).toBe(initial.revision));
    return { hook, getSpy };
  }

  it("does not undo a confirmed pause with an older GET (running rev 10 after paused rev 11)", async () => {
    const { hook, getSpy } = await mountWith(session());
    const oldGet = deferred<DemoSessionView | null>();
    getSpy.mockReturnValueOnce(oldGet.promise);
    vi.spyOn(api, "pauseDemo").mockResolvedValue(session({ status: "paused", revision: 11 }));

    let pendingRefresh!: Promise<void>;
    act(() => {
      pendingRefresh = hook.result.current.refresh();
    });
    await act(async () => {
      await hook.result.current.sendCommand("pause");
    });
    expect(hook.result.current.session?.status).toBe("paused");

    await act(async () => {
      oldGet.resolve(session({ status: "running", revision: 10 }));
      await pendingRefresh;
    });
    expect(hook.result.current.session?.status).toBe("paused");
    expect(hook.result.current.session?.revision).toBe(11);
    hook.unmount();
  });

  it("discards an older command response that arrives after a newer GET", async () => {
    const { hook, getSpy } = await mountWith(session());
    const pause = deferred<DemoSessionView>();
    vi.spyOn(api, "pauseDemo").mockReturnValue(pause.promise);

    let pendingCommand!: Promise<void>;
    act(() => {
      pendingCommand = hook.result.current.sendCommand("pause");
    });
    getSpy.mockResolvedValueOnce(session({ status: "running", revision: 12, cursor: 5 }));
    await act(async () => {
      await hook.result.current.refresh();
    });
    expect(hook.result.current.session?.revision).toBe(12);

    await act(async () => {
      pause.resolve(session({ status: "paused", revision: 11 }));
      await pendingCommand;
    });
    expect(hook.result.current.session?.revision).toBe(12);
    expect(hook.result.current.session?.status).toBe("running");
    hook.unmount();
  });

  it("discards a late response from a previous session once a new one was adopted", async () => {
    const { hook, getSpy } = await mountWith(session({ session_id: "s1", revision: 10 }));
    const pause = deferred<DemoSessionView>();
    vi.spyOn(api, "pauseDemo").mockReturnValue(pause.promise);

    let pendingCommand!: Promise<void>;
    act(() => {
      pendingCommand = hook.result.current.sendCommand("pause");
    });
    // Nueva sesión con revisión numéricamente menor: no se compara con la anterior.
    getSpy.mockResolvedValueOnce(session({ session_id: "s2", sensor_id: "demo-y", status: "prepared", revision: 1 }));
    await act(async () => {
      await hook.result.current.refresh();
    });
    expect(hook.result.current.session?.session_id).toBe("s2");
    expect(hook.result.current.session?.revision).toBe(1);

    await act(async () => {
      pause.resolve(session({ session_id: "s1", status: "paused", revision: 11 }));
      await pendingCommand;
    });
    expect(hook.result.current.session?.session_id).toBe("s2");
    expect(hook.result.current.session?.status).toBe("prepared");
    hook.unmount();
  });

  it("does not present a network error as a confirmed pause", async () => {
    const { hook, getSpy } = await mountWith(session());
    getSpy.mockRejectedValueOnce(new Error("network"));
    await act(async () => {
      await hook.result.current.refresh();
    });
    expect(hook.result.current.session?.status).toBe("running");
    expect(hook.result.current.connectionError).toMatch(/podría seguir en marcha/i);
    hook.unmount();
  });

  it("ignores responses that arrive after unmount", async () => {
    const { hook, getSpy } = await mountWith(session());
    const late = deferred<DemoSessionView | null>();
    getSpy.mockReturnValueOnce(late.promise);
    let pending!: Promise<void>;
    act(() => {
      pending = hook.result.current.refresh();
    });
    hook.unmount();
    late.resolve(session({ revision: 99 }));
    await expect(pending).resolves.toBeUndefined();
  });
});
