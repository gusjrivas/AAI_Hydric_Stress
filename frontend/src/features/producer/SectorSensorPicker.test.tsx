import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SectorSensorPicker } from "./SectorSensorPicker";
import * as api from "./catalogApi";
import { ProducerV2UnavailableError } from "./catalogApi";

const sectorNorte: api.Sector = {
  sector_id: "norte",
  display_name: "Huerta norte",
  crop: "Tomate",
  primary_sensor_id: "sensor-a",
  revision: 1,
  created_at: "2026-01-01T00:00:00Z",
};
const sectorSur: api.Sector = {
  sector_id: "sur",
  display_name: "Huerta sur",
  crop: "Lechuga",
  primary_sensor_id: null,
  revision: 1,
  created_at: "2026-01-01T00:00:00Z",
};

const sensorA: api.SensorSummary = {
  sensor_id: "sensor-a",
  display_name: "Sensor A",
  sector_id: "norte",
  source_kind: "real",
  revision: 1,
  created_at: "2026-01-01T00:00:00Z",
  registered: true,
};
const sensorB: api.SensorSummary = {
  sensor_id: "sensor-b",
  display_name: "Sensor B",
  sector_id: "sur",
  source_kind: "synthetic",
  revision: 1,
  created_at: "2026-01-01T00:00:00Z",
  registered: true,
};

describe("SectorSensorPicker", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("lists sectors and auto-selects the sector's primary sensor", async () => {
    vi.spyOn(api, "listSectors").mockResolvedValue({ items: [sectorNorte, sectorSur], next_cursor: null });
    vi.spyOn(api, "listSensors").mockResolvedValue({ items: [sensorA], next_cursor: null });
    const onSelect = vi.fn();
    render(<SectorSensorPicker onSelect={onSelect} />);

    await userEvent.selectOptions(await screen.findByLabelText("Tu sector"), "Huerta norte · Tomate");
    await waitFor(() => expect(onSelect).toHaveBeenLastCalledWith(sensorA));
    expect(screen.getByLabelText("Punto de medición")).toHaveValue("sensor-a");
  });

  it("reloads sensors when the sector changes and marks synthetic sensors", async () => {
    vi.spyOn(api, "listSectors").mockResolvedValue({ items: [sectorNorte, sectorSur], next_cursor: null });
    const listSensorsSpy = vi
      .spyOn(api, "listSensors")
      .mockImplementation((sectorId) =>
        Promise.resolve({ items: sectorId === "sur" ? [sensorB] : [sensorA], next_cursor: null }),
      );
    render(<SectorSensorPicker onSelect={vi.fn()} />);

    await userEvent.selectOptions(await screen.findByLabelText("Tu sector"), "Huerta sur · Lechuga");
    await waitFor(() => expect(listSensorsSpy).toHaveBeenLastCalledWith("sur"));
    expect(await screen.findByText(/Sensor B · Simulado/)).toBeInTheDocument();
  });

  it("discards a sensor response from a sector that is no longer selected", async () => {
    vi.spyOn(api, "listSectors").mockResolvedValue({ items: [sectorNorte, sectorSur], next_cursor: null });
    let resolveNorte!: (value: api.SensorListResult) => void;
    vi.spyOn(api, "listSensors").mockImplementation((sectorId) => {
      if (sectorId === "norte") return new Promise((resolve) => { resolveNorte = resolve; });
      return Promise.resolve({ items: [sensorB], next_cursor: null });
    });
    const onSelect = vi.fn();
    render(<SectorSensorPicker onSelect={onSelect} />);

    await userEvent.selectOptions(await screen.findByLabelText("Tu sector"), "Huerta norte · Tomate");
    await userEvent.selectOptions(screen.getByLabelText("Tu sector"), "Huerta sur · Lechuga");
    await waitFor(() => expect(onSelect).toHaveBeenLastCalledWith(sensorB));

    resolveNorte({ items: [sensorA], next_cursor: null });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(onSelect).toHaveBeenLastCalledWith(sensorB);
  });

  it("distinguishes an unavailable v2 catalog from an empty one", async () => {
    vi.spyOn(api, "listSectors").mockRejectedValue(new ProducerV2UnavailableError());
    render(<SectorSensorPicker onSelect={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/todavía no está disponible/i);
  });
});
