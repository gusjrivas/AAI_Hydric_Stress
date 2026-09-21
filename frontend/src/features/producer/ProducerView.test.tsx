import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProducerView } from "./ProducerView";
import * as catalogApi from "./catalogApi";
import * as readingsApi from "./readingsApi";
import * as forecastsApi from "./forecastsApi";

const sector: catalogApi.Sector = {
  sector_id: "norte",
  display_name: "Huerta norte",
  crop: "Tomate",
  primary_sensor_id: "sensor-a",
  revision: 1,
  created_at: "2026-01-01T00:00:00Z",
};
const sensor: catalogApi.SensorSummary = {
  sensor_id: "sensor-a",
  display_name: "Sensor A",
  sector_id: "norte",
  source_kind: "synthetic",
  revision: 1,
  created_at: "2026-01-01T00:00:00Z",
  registered: true,
};

describe("ProducerView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows a synthetic-data tag and the honest empty state for forecasts", async () => {
    vi.spyOn(catalogApi, "listSectors").mockResolvedValue({ items: [sector], next_cursor: null });
    vi.spyOn(catalogApi, "listSensors").mockResolvedValue({ items: [sensor], next_cursor: null });
    vi.spyOn(readingsApi, "getSensorReadings").mockResolvedValue({
      sensor_id: "sensor-a",
      calendar_timezone: "UTC",
      server_today: "2026-01-05",
      snapshot_id: null,
      window: { start_date: "2026-01-01", end_date: "2026-01-01", expected_days: 1 },
      status: "no_readings",
      rows: [],
      missing_dates: [],
      variable_coverage: [],
      units: {},
      last_reading_date: null,
      data_age_days: null,
      provenance: "unknown",
    });
    vi.spyOn(forecastsApi, "listForecasts").mockResolvedValue({
      items: [],
      next_cursor: null,
      pending_total: 0,
      reviewable_pending_total: 0,
    });

    render(<ProducerView />);

    expect(await screen.findByText("Datos simulados")).toBeInTheDocument();
    expect(await screen.findByText(/todavía no hay pronósticos disponibles/i)).toBeInTheDocument();
    expect(screen.getByText(/no tenés pronósticos pendientes de revisar/i)).toBeInTheDocument();
  });

  it("prompts to pick a sensor before showing history", () => {
    vi.spyOn(catalogApi, "listSectors").mockReturnValue(new Promise(() => {}));
    render(<ProducerView />);
    expect(screen.getByText(/elegí un punto de medición para ver su historial/i)).toBeInTheDocument();
  });
});
