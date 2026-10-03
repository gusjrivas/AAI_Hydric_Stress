import type { QualityReport } from "./api";

/** Informe de calidad de un punto que SÍ tiene mediciones (el pipeline de herramientas lo exige para pronosticar). */
export function readyQuality(sensorId = "sensor-a"): QualityReport {
  return {
    sensor_id: sensorId,
    total_rows: 120,
    period_start: "2024-01-01",
    period_end: "2024-04-29",
    missing_pct: {},
    duplicate_timestamps: [],
    out_of_range: {},
    anomalies_detected: 0,
    anomaly_method: "isolation_forest",
    anomaly_contamination: 0.01,
    anomaly_columns: [],
    is_diagnostic_only: true,
    note: "",
  };
}
