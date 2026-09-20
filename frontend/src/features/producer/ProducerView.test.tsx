import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProducerView } from "./ProducerView";
import * as catalogApi from "./catalogApi";
import * as readingsApi from "./readingsApi";

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

  it("shows a synthetic-data tag and states forecasts are not integrated yet", async () => {
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

    render(<ProducerView />);

    expect(await screen.findByText("Datos simulados")).toBeInTheDocument();
    expect(screen.getByText(/pronósticos del catálogo v2 todavía no están integrados/i)).toBeInTheDocument();
  });

  it("prompts to pick a sensor before showing history", () => {
    vi.spyOn(catalogApi, "listSectors").mockReturnValue(new Promise(() => {}));
    render(<ProducerView />);
    expect(screen.getByText(/elegí un punto de medición para ver su historial/i)).toBeInTheDocument();
  });
});
