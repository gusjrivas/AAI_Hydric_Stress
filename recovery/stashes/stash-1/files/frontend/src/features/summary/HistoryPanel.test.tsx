import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HistoryPanel } from "./HistoryPanel";
import * as api from "./historyApi";

const history: api.MeasurementHistory = {
  sensor_id: "demo-a", period_start: "2024-01-01", period_end: "2024-01-03",
  rows: [
    { fecha: "2024-01-01", soil_moisture: 0.3, temperature: 20, precipitation: 0, origen: "sintetico" },
    { fecha: "2024-01-02", soil_moisture: null, temperature: 21, precipitation: 0, origen: "sintetico" },
    { fecha: "2024-01-03", soil_moisture: 0.2, temperature: 22, precipitation: 2, origen: "sintetico" },
  ],
};

describe("HistoryPanel", () => {
  beforeEach(() => vi.restoreAllMocks());
  it("shows synthetic provenance, units and a table without joining missing observations", async () => {
    vi.spyOn(api, "getMeasurementHistory").mockResolvedValue(history);
    const { container } = render(<HistoryPanel sensorId="demo-a" refreshToken={0} />);
    await screen.findByText(/solo para demostración/i);
    expect(screen.getAllByText("20.0 %")[0]).toBeVisible();
    expect(container.querySelectorAll("svg circle")).toHaveLength(2);
    expect(container.querySelectorAll('svg line[stroke-width="3"]')).toHaveLength(0);
    await userEvent.click(screen.getByText(/ver mediciones por fecha/i));
    expect(screen.getByRole("table")).toBeVisible();
    expect(screen.getByText("Sin medición")).toBeVisible();
  });
  it("changes the calendar window and reloads on demo progress", async () => {
    const spy = vi.spyOn(api, "getMeasurementHistory").mockResolvedValue(history);
    const { rerender } = render(<HistoryPanel sensorId="demo-a" refreshToken={0} />);
    await screen.findByText(/solo para demostración/i);
    await userEvent.selectOptions(screen.getByRole("combobox"), "7");
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith("demo-a", 7));
    const count = spy.mock.calls.length;
    rerender(<HistoryPanel sensorId="demo-a" refreshToken={1} />);
    await waitFor(() => expect(spy.mock.calls.length).toBe(count + 1));
  });
  it("discards an obsolete sensor response", async () => {
    let resolve!: (data: api.MeasurementHistory) => void;
    vi.spyOn(api, "getMeasurementHistory").mockReturnValueOnce(new Promise((r) => { resolve = r; })).mockResolvedValueOnce(null);
    const { rerender } = render(<HistoryPanel sensorId="demo-a" refreshToken={0} />);
    rerender(<HistoryPanel sensorId="other" refreshToken={0} />);
    await screen.findByText(/todavía no hay mediciones/i);
    resolve(history);
    await waitFor(() => expect(screen.queryByText(/solo para demostración/i)).not.toBeInTheDocument());
  });
  it("distinguishes a failure from an empty history and retries", async () => {
    vi.spyOn(api, "getMeasurementHistory").mockRejectedValueOnce(new Error("Sin conexión")).mockResolvedValue(null);
    render(<HistoryPanel sensorId="demo-a" refreshToken={0} />);
    await screen.findByRole("alert");
    expect(screen.queryByText(/todavía no hay mediciones/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reintentar mediciones" }));
    await screen.findByText(/todavía no hay mediciones/i);
  });
});
