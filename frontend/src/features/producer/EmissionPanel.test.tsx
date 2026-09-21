import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EmissionPanel } from "./EmissionPanel";
import * as api from "./forecastsApi";
import type { ForecastBatch } from "./forecastsApi";

const unavailable: ForecastBatch = {
  batch_id: "b1", revision: 1, as_of_date: "2024-08-27", data_age_days: 700, server_today: "2026-07-28",
  slots: [1, 2, 3].map((h) => ({ horizon_days: h as 1 | 2 | 3, target_date: `2024-08-${27 + h}`, status: "unavailable", reason_code: "model_not_available" })),
};

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("EmissionPanel", () => {
  it("only emits on request and explains missing predictions and old readings", async () => {
    const emit = vi.spyOn(api, "emitForecasts").mockResolvedValue(unavailable);
    const refreshed = vi.fn();
    render(<EmissionPanel sensorId="sensor-a" onChanged={refreshed} />);
    expect(emit).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Consultar próximos tres días" }));
    expect(await screen.findAllByText("Sin pronóstico disponible")).toHaveLength(3);
    expect(screen.getByText(/700 días de antigüedad/)).toBeInTheDocument();
    expect(screen.queryByText(/0 %/)).not.toBeInTheDocument();
    expect(refreshed).toHaveBeenCalledOnce();
  });

  it("reuses an uncertain request key, then uses a new one after success", async () => {
    const emit = vi.spyOn(api, "emitForecasts")
      .mockRejectedValueOnce(new Error("Conexión interrumpida"))
      .mockResolvedValue(unavailable);
    render(<EmissionPanel sensorId="sensor-a" onChanged={() => {}} />);
    await userEvent.click(screen.getByRole("button"));
    await screen.findByRole("alert");
    await userEvent.click(screen.getByRole("button", { name: "Reintentar consulta" }));
    await screen.findAllByText("Sin pronóstico disponible");
    expect(emit.mock.calls[1][1]).toBe(emit.mock.calls[0][1]);
    await userEvent.click(screen.getByRole("button"));
    await waitFor(() => expect(emit).toHaveBeenCalledTimes(3));
    expect(emit.mock.calls[2][1]).not.toBe(emit.mock.calls[0][1]);
  });

  it("disables duplicate clicks and ignores results from a previously selected sensor", async () => {
    let finish!: (result: ForecastBatch) => void;
    vi.spyOn(api, "emitForecasts").mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const refreshed = vi.fn();
    const view = render(<EmissionPanel key="a" sensorId="sensor-a" onChanged={refreshed} />);
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toBeDisabled();
    view.rerender(<EmissionPanel key="b" sensorId="sensor-b" onChanged={refreshed} />);
    await act(async () => { finish(unavailable); });
    expect(screen.queryByText(/700 días/)).not.toBeInTheDocument();
    expect(refreshed).not.toHaveBeenCalled();
    expect(screen.getByRole("button")).toBeEnabled();
  });
});

it("POSTs an empty body with the request identity to the selected sensor", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(unavailable), { status: 201 }));
  vi.stubGlobal("fetch", fetch);
  expect(await api.emitForecasts("sensor-a", "request-1")).toEqual(unavailable);
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v2/sensors/sensor-a/forecasts"), {
    method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": "request-1" }, body: "{}",
  });
});
