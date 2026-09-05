import { afterEach, expect, it, vi } from "vitest";
import { confirmAlert, listFeedback, recalibrate, rejectAlert, runForecast } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("routes every operation to the selected sensor", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
  vi.stubGlobal("fetch", fetchMock);
  await runForecast("sensor-b");
  await listFeedback("sensor-b");
  await confirmAlert("sensor-b", "2024-10-31");
  await rejectAlert("sensor-b", "2024-10-31", 1, "Estrés observado");
  await recalibrate("sensor-b");
  expect(fetchMock.mock.calls.map((call) => new URL(call[0]).pathname)).toEqual([
    "/forecast/sensor-b/run", "/feedback/sensor-b", "/feedback/sensor-b/2024-10-31/confirm",
    "/feedback/sensor-b/2024-10-31/reject", "/recalibrate/sensor-b",
  ]);
  expect(JSON.parse(fetchMock.mock.calls[3][1].body).etiqueta_corregida).toBe(1);
});
