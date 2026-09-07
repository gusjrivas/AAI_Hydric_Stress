import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QualityPanel } from "./QualityPanel";
import * as api from "./api";

describe("QualityPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state before the report resolves", () => {
    vi.spyOn(api, "getQualityReport").mockReturnValue(new Promise(() => {}));

    render(<QualityPanel sensorId="sensor-a" />);

    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
  });

  it("renders the quality report once it resolves", async () => {
    vi.spyOn(api, "getQualityReport").mockResolvedValue({
      sensor_id: "sensor-a",
      total_rows: 366,
      period_start: "2024-01-01",
      period_end: "2024-12-31",
      missing_pct: { soil_moisture: 24.04, temperature: 0 },
      duplicate_timestamps: [],
      out_of_range: {},
      anomalies_detected: 19,
      anomaly_method: "isolation_forest",
      anomaly_contamination: 0.05,
      anomaly_columns: ["soil_moisture", "solar_radiation", "relative_humidity"],
      is_diagnostic_only: true,
      note: "Diagnóstico exploratorio, separado del predictor operativo (include_anomaly_detection=False).",
    });

    render(<QualityPanel sensorId="sensor-a" />);

    await waitFor(() => screen.getByText(/366 registros/i));
    expect(screen.getByText("19")).toBeInTheDocument();
    expect(screen.getByText(/evento real/i)).toBeInTheDocument();
  });

  it("shows an empty state when the sensor has no dataset ingested yet", async () => {
    vi.spyOn(api, "getQualityReport").mockResolvedValue(null);

    render(<QualityPanel sensorId="sensor-nuevo" />);

    await waitFor(() => screen.getByText(/todavía no hay datos ingeridos/i));
  });

  it("shows an alert on error", async () => {
    vi.spyOn(api, "getQualityReport").mockRejectedValue(new Error("fallo de red"));

    render(<QualityPanel sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/fallo de red/i);
    });
  });
});
