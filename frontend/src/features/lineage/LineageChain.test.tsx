import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { LineageChain } from "./LineageChain";
import * as api from "./api";
import type { LineageResponse } from "./api";

describe("LineageChain", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an empty state when the sensor was never recalibrated", async () => {
    vi.spyOn(api, "getLineage").mockResolvedValue({ sensor_id: "sensor-a", chain: [] });

    render(<LineageChain sensorId="sensor-a" />);

    await waitFor(() => screen.getByText(/todavía no tiene ninguna recalibración registrada/i));
  });

  it("renders the A -> feedback -> B chain in order, distinguishing lineage_version", async () => {
    vi.spyOn(api, "getLineage").mockResolvedValue({
      sensor_id: "sensor-a",
      chain: [
        {
          recalibration_id: "r1",
          source_model_id: "modelo-origen-aaaa",
          successor_model_id: "modelo-sucesor-bbbb",
          feedback_references: [
            {
              sensor_id: "sensor-a",
              fecha: "2024-10-31",
              model_version: "modelo-origen-aaaa",
              target_timestamp: "2024-11-03",
            },
          ],
          recalibrated_at: "2026-09-06T10:00:00",
          source_trained_through: "2024-10-30",
          successor_trained_through: "2024-10-31",
          lineage_version: 2,
          dataset_sha256: "a".repeat(64),
          mlflow_model_version: "1",
        },
      ],
    });

    render(<LineageChain sensorId="sensor-a" />);

    await waitFor(() => screen.getByText(/trazabilidad/i));
    expect(screen.getByText("V2")).toBeInTheDocument();
    expect(screen.getByText(/feedback \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/mejora automática del desempeño/i)).toBeInTheDocument();
  });

  it("shows a v1 badge and 'no disponible' when dataset_sha256 is absent", async () => {
    vi.spyOn(api, "getLineage").mockResolvedValue({
      sensor_id: "sensor-a",
      chain: [
        {
          recalibration_id: "r1",
          source_model_id: "modelo-origen-aaaa",
          successor_model_id: "modelo-sucesor-bbbb",
          feedback_references: [
            {
              sensor_id: "sensor-a",
              fecha: "2024-10-31",
              model_version: "modelo-origen-aaaa",
              target_timestamp: "2024-11-03",
            },
          ],
          recalibrated_at: "2026-09-06T10:00:00",
          source_trained_through: "2024-10-30",
          successor_trained_through: "2024-10-31",
          lineage_version: 1,
          dataset_sha256: null,
          mlflow_model_version: "1",
        },
      ],
    });

    render(<LineageChain sensorId="sensor-a" />);

    await waitFor(() => screen.getByText("V1"));
    expect(screen.getByText(/no disponible \(lineage_version 1\)/i)).toBeInTheDocument();
  });

  it("shows an integrity error explicitly instead of hiding it or showing a partial chain", async () => {
    vi.spyOn(api, "getLineage").mockRejectedValue(new Error("linaje corrupto"));

    render(<LineageChain sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/error de integridad de linaje/i);
    });
  });

  it("shows loading again and never the previous sensor's chain when sensorId changes", async () => {
    const entryA = {
      recalibration_id: "r1",
      source_model_id: "modelo-origen-aaaa",
      successor_model_id: "modelo-sucesor-bbbb",
      feedback_references: [],
      recalibrated_at: "2026-09-06T10:00:00",
      source_trained_through: "2024-10-30",
      successor_trained_through: "2024-10-31",
      lineage_version: 2,
      dataset_sha256: "a".repeat(64),
      mlflow_model_version: "1",
    };
    const spy = vi.spyOn(api, "getLineage");
    spy.mockResolvedValueOnce({ sensor_id: "sensor-a", chain: [entryA] });

    const { rerender } = render(<LineageChain sensorId="sensor-a" />);
    await waitFor(() => screen.getByText("V2"));

    let resolveSensorB!: (value: LineageResponse) => void;
    spy.mockReturnValueOnce(new Promise<LineageResponse>((resolve) => (resolveSensorB = resolve)));

    rerender(<LineageChain sensorId="sensor-b" />);

    expect(screen.getByRole("status")).toHaveTextContent(/reconstruyendo/i);
    expect(screen.queryByText("V2")).not.toBeInTheDocument();

    resolveSensorB({ sensor_id: "sensor-b", chain: [] });
    await waitFor(() => screen.getByText(/todavía no tiene ninguna recalibración registrada/i));
  });

  it("refetches without showing stale data when refreshToken changes", async () => {
    const spy = vi.spyOn(api, "getLineage");
    spy.mockResolvedValueOnce({ sensor_id: "sensor-a", chain: [] });

    const { rerender } = render(<LineageChain sensorId="sensor-a" refreshToken={0} />);
    await waitFor(() => screen.getByText(/todavía no tiene ninguna recalibración registrada/i));

    let resolveRefetch!: (value: LineageResponse) => void;
    spy.mockReturnValueOnce(new Promise<LineageResponse>((resolve) => (resolveRefetch = resolve)));

    rerender(<LineageChain sensorId="sensor-a" refreshToken={1} />);

    expect(screen.getByRole("status")).toHaveTextContent(/reconstruyendo/i);

    resolveRefetch({
      sensor_id: "sensor-a",
      chain: [
        {
          recalibration_id: "r2",
          source_model_id: "modelo-origen-cccc",
          successor_model_id: "modelo-sucesor-dddd",
          feedback_references: [],
          recalibrated_at: "2026-09-06T11:00:00",
          source_trained_through: "2024-11-01",
          successor_trained_through: "2024-11-02",
          lineage_version: 2,
          dataset_sha256: "b".repeat(64),
          mlflow_model_version: "2",
        },
      ],
    });

    await waitFor(() => screen.getByText("V2"));
  });
});
