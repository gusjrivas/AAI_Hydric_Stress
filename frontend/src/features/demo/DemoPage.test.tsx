import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DemoPage } from "./DemoPage";
import { useDemoSession } from "./useDemoSession";
import * as api from "./api";
import type { DemoSessionView } from "./api";

function Harness() {
  const demo = useDemoSession();
  return <DemoPage demo={demo} />;
}

function baseSession(overrides: Partial<DemoSessionView> = {}): DemoSessionView {
  return {
    session_id: "demo-1",
    sensor_id: "demo-sensor-1",
    status: "prepared",
    phase: "pending",
    cursor: 0,
    days: 5,
    simulated_date: null,
    last_ingested_date: null,
    last_forecast_date: null,
    interval_seconds: 5,
    revision: 1,
    error: null,
    ...overrides,
  };
}

describe("DemoPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "isDemoControlConfigured").mockReturnValue(true);
    vi.spyOn(api, "newRequestId").mockImplementation(
      (() => {
        let n = 0;
        return () => `req-${n++}`;
      })(),
    );
  });

  it("shows the app works without the controller when it is not configured", async () => {
    vi.spyOn(api, "isDemoControlConfigured").mockReturnValue(false);
    const getSpy = vi.spyOn(api, "getDemoSession");

    render(<Harness />);

    expect(screen.getByText(/no está configurada en este entorno/i)).toBeInTheDocument();
    expect(getSpy).not.toHaveBeenCalled();
  });

  it("shows preparation instructions when no session exists yet, without creating one", async () => {
    vi.spyOn(api, "getDemoSession").mockResolvedValue(null);
    const startSpy = vi.spyOn(api, "startDemo");

    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByText(/todavía no hay una sesión de demostración preparada/i)).toBeInTheDocument();
    });
    expect(startSpy).not.toHaveBeenCalled();
  });

  it("shows the permanent simulated-data label, sensor, day and progress for a prepared session", async () => {
    vi.spyOn(api, "getDemoSession").mockResolvedValue(baseSession());

    render(<Harness />);

    await waitFor(() => screen.getByText("demo-sensor-1"));
    expect(screen.getByText("Demostración con datos simulados")).toBeInTheDocument();
    expect(screen.getByText(/0 de 5/)).toBeInTheDocument();
  });

  it("starts a prepared session on explicit click and ignores a rapid second click", async () => {
    vi.spyOn(api, "getDemoSession").mockResolvedValue(baseSession());
    let resolveStart!: (value: DemoSessionView) => void;
    const startSpy = vi
      .spyOn(api, "startDemo")
      .mockReturnValueOnce(new Promise((resolve) => (resolveStart = resolve)));

    render(<Harness />);
    await waitFor(() => screen.getByRole("button", { name: /^iniciar$/i }));

    const startButton = screen.getByRole("button", { name: /^iniciar$/i });
    await userEvent.click(startButton);
    await userEvent.click(startButton);

    expect(startSpy).toHaveBeenCalledTimes(1);
    expect(startSpy).toHaveBeenCalledWith({
      session_id: "demo-1",
      expected_revision: 1,
      request_id: "req-0",
    });

    resolveStart(baseSession({ status: "running", revision: 2, simulated_date: "2024-01-01" }));
    await waitFor(() => expect(screen.getByText(/en ejecución/i)).toBeInTheDocument());
  });

  it("shows pause as requested while the current step resolves, not as already paused", async () => {
    vi.spyOn(api, "getDemoSession").mockResolvedValue(
      baseSession({ status: "running", revision: 3, simulated_date: "2024-01-02" }),
    );
    vi.spyOn(api, "pauseDemo").mockResolvedValue(
      baseSession({ status: "pausing", revision: 4, simulated_date: "2024-01-02" }),
    );

    render(<Harness />);
    await waitFor(() => screen.getByRole("button", { name: /^pausar$/i, hidden: false }));

    await userEvent.click(screen.getByRole("button", { name: /^pausar$/i }));

    await waitFor(() => {
      expect(screen.getByText(/pausa solicitada/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/^pausada$/i)).not.toBeInTheDocument();
  });

  it("continues a paused session with an explicit resume action", async () => {
    vi.spyOn(api, "getDemoSession").mockResolvedValue(baseSession({ status: "paused", revision: 5 }));
    const resumeSpy = vi
      .spyOn(api, "resumeDemo")
      .mockResolvedValue(baseSession({ status: "running", revision: 6 }));

    render(<Harness />);
    await waitFor(() => screen.getByRole("button", { name: /^continuar$/i }));
    await userEvent.click(screen.getByRole("button", { name: /^continuar$/i }));

    await waitFor(() => expect(resumeSpy).toHaveBeenCalledWith({
      session_id: "demo-1",
      expected_revision: 5,
      request_id: "req-0",
    }));
    await waitFor(() => expect(screen.getByText(/en ejecución/i)).toBeInTheDocument());
  });

  it("explains that closing the tab does not pause the worker", async () => {
    vi.spyOn(api, "getDemoSession").mockResolvedValue(baseSession({ status: "running" }));
    render(<Harness />);
    await waitFor(() => screen.getByText(/cerrar esta pestaña no pausa la demostración/i));
  });

  it("reports a completed session and points to reviewing observable results", async () => {
    vi.spyOn(api, "getDemoSession").mockResolvedValue(
      baseSession({ status: "completed", cursor: 5, last_ingested_date: "2024-01-05" }),
    );
    render(<Harness />);
    await waitFor(() => screen.getByText(/sesión completada/i));
    expect(screen.getByRole("link", { name: /historial y observaciones/i })).toBeInTheDocument();
  });

  it("shows a connection error without claiming the demo is paused, and keeps the last known progress", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const getSpy = vi
        .spyOn(api, "getDemoSession")
        .mockResolvedValueOnce(baseSession({ status: "running", cursor: 2, simulated_date: "2024-01-03" }))
        .mockRejectedValueOnce(new TypeError("Failed to fetch"));

      render(<Harness />);
      await waitFor(() => screen.getByText(/2 de 5/));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      await waitFor(() => {
        expect(screen.getByText(/no se pudo consultar el estado/i)).toBeInTheDocument();
      });
      // El progreso confirmado previamente se conserva; no se afirma pausa.
      expect(screen.getByText(/2 de 5/)).toBeInTheDocument();
      expect(screen.queryByText(/^pausada$/i)).not.toBeInTheDocument();
      expect(getSpy).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it("refetches immediately when the tab becomes visible again", async () => {
    const getSpy = vi.spyOn(api, "getDemoSession").mockResolvedValue(baseSession({ status: "paused" }));
    render(<Harness />);
    await waitFor(() => expect(getSpy).toHaveBeenCalledTimes(1));

    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));

    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    await waitFor(() => expect(getSpy.mock.calls.length).toBeGreaterThanOrEqual(2));
  });
});
