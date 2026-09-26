import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EmissionPanel } from "./EmissionPanel";
import * as api from "./forecastsApi";
import type { ForecastBatch } from "./forecastsApi";

const unavailable: ForecastBatch = {
  batch_id: "b1", revision: 1, as_of_date: "2024-08-27", data_age_days: 700, server_today: "2026-07-28",
  provenance: "synthetic", calendar_timezone: "UTC",
  slots: [1, 2, 3].map((h) => ({ horizon_days: h as 1 | 2 | 3, target_date: `2024-08-${27 + h}`, status: "unavailable", reason_code: "model_not_available" })),
};

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("EmissionPanel", () => {
  it("consults automatically on mount and explains missing predictions and old readings", async () => {
    const emit = vi.spyOn(api, "emitForecasts").mockResolvedValue(unavailable);
    const refreshed = vi.fn();
    render(<EmissionPanel sensorId="sensor-a" onChanged={refreshed} />);
    await waitFor(() => expect(emit).toHaveBeenCalledOnce());
    expect(await screen.findAllByText("Sin pronóstico disponible")).toHaveLength(3);
    expect(screen.getByText(/700 días de antigüedad/)).toBeInTheDocument();
    expect(screen.queryByText(/0 %/)).not.toBeInTheDocument();
    expect(refreshed).toHaveBeenCalledOnce();
  });

  it("shows the insufficient-information notice when every horizon is unavailable", async () => {
    vi.spyOn(api, "emitForecasts").mockResolvedValue(unavailable);
    render(<EmissionPanel sensorId="sensor-a" onChanged={() => {}} />);
    expect(await screen.findByText(/No hay información suficiente/)).toBeInTheDocument();
  });

  it("reuses an uncertain request key, then uses a new one after a manual retry", async () => {
    const emit = vi.spyOn(api, "emitForecasts")
      .mockRejectedValueOnce(new Error("Conexión interrumpida"))
      .mockResolvedValue(unavailable);
    render(<EmissionPanel sensorId="sensor-a" onChanged={() => {}} />);
    await screen.findByRole("alert");
    await userEvent.click(screen.getByRole("button", { name: "Reintentar consulta" }));
    await screen.findAllByText("Sin pronóstico disponible");
    expect(emit.mock.calls[1][1]).toBe(emit.mock.calls[0][1]);
    await userEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(emit).toHaveBeenCalledTimes(3));
    expect(emit.mock.calls[2][1]).not.toBe(emit.mock.calls[0][1]);
  });

  it("disables duplicate consultation and ignores results from a previously selected sensor", async () => {
    const resolvers: Array<(result: ForecastBatch) => void> = [];
    vi.spyOn(api, "emitForecasts").mockImplementation(
      () => new Promise((resolve) => { resolvers.push(resolve); }),
    );
    const refreshed = vi.fn();
    const view = render(<EmissionPanel key="a" sensorId="sensor-a" onChanged={refreshed} />);
    await waitFor(() => expect(screen.getByRole("button")).toBeDisabled());
    view.rerender(<EmissionPanel key="b" sensorId="sensor-b" onChanged={refreshed} />);
    await waitFor(() => expect(resolvers).toHaveLength(2));
    // resolvers[0] belongs to the unmounted sensor-a instance: its result
    // must never reach the screen now showing sensor-b.
    await act(async () => { resolvers[0](unavailable); });
    expect(screen.queryByText(/700 días/)).not.toBeInTheDocument();
    expect(refreshed).not.toHaveBeenCalled();
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
