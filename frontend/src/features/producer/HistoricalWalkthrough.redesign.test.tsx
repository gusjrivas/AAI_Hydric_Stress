import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HistoricalWalkthrough } from "./HistoricalWalkthrough";
import * as historicalApi from "./historicalApi";
import type { ForecastBatch } from "./forecastsApi";
import type { ReadingRow, ReadingsResult } from "./readingsApi";

afterEach(() => vi.restoreAllMocks());

const unavailableBatch = (asOf: string): ForecastBatch => ({
  batch_id: `batch-${asOf}`,
  revision: 1,
  as_of_date: asOf,
  data_age_days: 0,
  server_today: asOf,
  provenance: "external_reanalysis",
  calendar_timezone: "UTC",
  slots: [1, 2, 3].map((h) => ({
    horizon_days: h as 1 | 2 | 3,
    target_date: `2023-06-${13 + h}`,
    status: "unavailable" as const,
    reason_code: "model_not_available",
  })),
});

function row(date: string, soil: number | null, imputed = false): ReadingRow {
  return {
    date, soil_moisture: soil, relative_humidity: null, solar_radiation: null, temperature: null,
    precipitation: null, wind_speed: null, et0: null, origin: "external_reanalysis", quality_flags: [],
    imputed_variables: imputed ? ["soil_moisture"] : [], unverified_variables: [],
  };
}

const readings = (end: string): ReadingsResult => ({
  sensor_id: "pergamino-ensemble-demo", calendar_timezone: "UTC", server_today: end, snapshot_id: null,
  window: { start_date: "2023-06-08", end_date: end, expected_days: 6 }, status: "ready",
  rows: [row("2023-06-08", 0.34), row("2023-06-09", 0.33), row("2023-06-10", null), row("2023-06-11", 0.32, true), row("2023-06-12", 0.31), row("2023-06-13", 0.3)],
  missing_dates: ["2023-06-10"],
  variable_coverage: [{ variable: "soil_moisture", observed_days: 4, missing_days: 1, imputed_days: 1, unverified_days: 0 }],
  units: { soil_moisture: "m3/m3" }, last_reading_date: end, data_age_days: 0, provenance: "external_reanalysis",
});

describe("HistoricalWalkthrough — rediseño", () => {
  it("labels the source in one chip and keeps the soil-moisture counts in one line", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(unavailableBatch("2023-06-13"));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue(readings("2023-06-13"));
    render(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    expect(screen.getByText("Datos externos · ERA5-Land / NASA POWER (reanálisis)")).toBeInTheDocument();
    await waitFor(() => expect(document.querySelector(".historical-quality-line")).toHaveTextContent(/4 con dato.*1 imputado.*0 sin verificar.*1 sin dato/i));
    await userEvent.click(screen.getByRole("tab", { name: /datos y calidad/i }));
    expect(await screen.findByRole("group", { name: /cobertura de la humedad del suelo/i })).toHaveTextContent(/4 con dato.*1 imputado.*0 sin verificar.*1 sin dato/i);
  });

  it("advances and rewinds the clock within the allowed range", async () => {
    const batch = vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(unavailableBatch("2023-06-13"));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue(readings("2023-06-13"));
    render(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    const clock = await screen.findByRole("slider", { name: /reloj del recorrido/i });
    expect(clock).toHaveValue("0");
    fireEvent.change(clock, { target: { value: "1" } });
    await waitFor(() => expect(batch).toHaveBeenLastCalledWith("pergamino-ensemble-demo", "2023-06-13", "2023-06-14"));
    fireEvent.change(screen.getByRole("slider", { name: /reloj del recorrido/i }), { target: { value: "0" } });
    await waitFor(() => expect(batch).toHaveBeenLastCalledWith("pergamino-ensemble-demo", "2023-06-13", undefined));
  });

  it("draws the moisture chart from revealed readings and keeps the table as the accessible alternative", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(unavailableBatch("2023-06-13"));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue(readings("2023-06-13"));
    render(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    expect(await screen.findByRole("img", { name: /4 observados, 1 imputados, 0 de procedencia no verificada y 1 sin dato/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: /observaciones/i }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText(/sin observación en la fuente/i)).toBeInTheDocument();
  });

  it("keeps heading levels contiguous: the headline is the h2 in defense mode, h3 elsewhere", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(unavailableBatch("2023-06-13"));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue(readings("2023-06-13"));
    const { unmount } = render(<HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />);
    expect(await screen.findByRole("heading", { level: 2, name: /13 de jun de 2023/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
    unmount();
    render(<HistoricalWalkthrough sensorId="sensor-a" />);
    expect(screen.getByRole("heading", { name: "Recorrido histórico", level: 3 })).toBeInTheDocument();
  });
});
