import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { FeedbackRow } from "../forecast/api";
import type { QualityReport } from "../quality/api";
import { LabStage } from "./LabStage";
import { generateWaterBalanceReading, injectRangeAnomaly, mulberry32 } from "./readingGenerator";
import type { LabReadingValues } from "./readingGenerator";
import { addDaysUtc } from "./labSensor";
import { LAB_DRY_DAYS, LAB_GAP_DAYS, LAB_HISTORY_DAYS } from "./useSensorLabScenarios";
import type { LabPhase, LabSeriesPoint } from "./useSensorLabScenarios";

const START = "2026-06-29";

/** Lecturas como las que dejaría la sesión al llegar a `upTo`. */
function sessionReadings(upTo: "A" | "B" | "D" | "E"): LabSeriesPoint[] {
  const rand = mulberry32(42);
  const points: LabSeriesPoint[] = [];
  let previous: LabReadingValues | null = null;
  let day = 0;
  const push = (date: string, values: LabReadingValues, kind: LabSeriesPoint["kind"]) => {
    points.push({ date, values, kind });
    previous = values;
  };
  for (let i = 0; i < LAB_HISTORY_DAYS; i += 1, day += 1) {
    push(addDaysUtc(START, i), generateWaterBalanceReading(previous, rand, day), "normal");
  }
  if (upTo === "A") return points;
  push(addDaysUtc(START, LAB_HISTORY_DAYS), injectRangeAnomaly(generateWaterBalanceReading(previous, rand, day++)), "anomaly");
  if (upTo === "B") return points;
  for (let i = 1; i <= LAB_GAP_DAYS; i += 1, day += 1) {
    push(addDaysUtc(START, LAB_HISTORY_DAYS + i), generateWaterBalanceReading(previous, rand, day), "normal");
  }
  if (upTo === "D") return points;
  for (let i = 1; i <= LAB_DRY_DAYS; i += 1, day += 1) {
    push(addDaysUtc(START, LAB_HISTORY_DAYS + LAB_GAP_DAYS + i), generateWaterBalanceReading(previous, rand, day, { dry: true }), "dry");
  }
  return points;
}

function quality(overrides: Partial<QualityReport> = {}): QualityReport {
  return {
    sensor_id: "lab-x",
    total_rows: LAB_HISTORY_DAYS,
    period_start: START,
    period_end: addDaysUtc(START, LAB_HISTORY_DAYS - 1),
    missing_pct: {},
    duplicate_timestamps: [],
    out_of_range: {},
    anomalies_detected: 0,
    anomaly_method: "isolation_forest",
    anomaly_contamination: 0.05,
    anomaly_columns: [],
    is_diagnostic_only: true,
    note: "",
    ...overrides,
  };
}

function row(fecha: string, alerta: 0 | 1, prob: number): FeedbackRow {
  return { fecha, alerta_generada: alerta, estado_validacion: "pendiente", etiqueta_corregida: null, observacion: null, y_proba: prob, fecha_objetivo: addDaysUtc(fecha, 3) };
}

const dateOf = (offset: number) => addDaysUtc(START, offset);

function stage(phase: LabPhase, upTo: "A" | "B" | "D" | "E" | null, extra: { rows?: FeedbackRow[]; quality?: QualityReport | null } = {}) {
  return render(
    <LabStage phase={phase} readings={upTo ? sessionReadings(upTo) : []} forecastRows={extra.rows ?? []} quality={extra.quality ?? null} />,
  );
}

describe("LabStage", () => {
  it("invites to start when nothing has run", () => {
    stage("idle", null);
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/todavía no se ejecutó ningún paso/i);
    expect(screen.queryByTestId("forecast-marker")).not.toBeInTheDocument();
  });

  it("draws the soil moisture history and the physical temperature range after step A", () => {
    stage("normal", "A", { quality: quality() });
    expect(screen.getByRole("img", { name: /humedad del suelo/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /temperatura/i })).toBeInTheDocument();
    expect(screen.getByText(/rango físico esperado \(-10 a 50 °C\)/)).toBeInTheDocument();
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/120 lecturas/);
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/0 fechas repetidas/);
  });

  it("marks the anomalous reading and reports whether quality flagged it, from the real report", () => {
    const anomalyDate = dateOf(LAB_HISTORY_DAYS);
    const { unmount } = stage("anomaly", "B", {
      quality: quality({ total_rows: 121, out_of_range: { temperature: [`${anomalyDate}T00:00:00`] } }),
      rows: [row(anomalyDate, 0, 0.05)],
    });
    expect(screen.getByTestId("anomaly-marker")).toBeInTheDocument();
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/85 °C/);
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/marca como fuera de rango/i);
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/no es una alerta de estrés hídrico/i);
    unmount();

    stage("anomaly", "B", { quality: quality({ total_rows: 121, out_of_range: {} }) });
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/no la marcó/i);
  });

  it("shows the interruption as a gap with no new forecast", () => {
    stage("interrupted", "B", { quality: quality({ total_rows: 121 }), rows: [row(dateOf(LAB_HISTORY_DAYS), 0, 0.05)] });
    expect(screen.getByTestId("gap-band")).toBeInTheDocument();
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(new RegExp(`${LAB_GAP_DAYS} días`));
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/no se pide un pronóstico nuevo/i);
  });

  it("describes the real verdict of the last forecast: without alert after recovery", () => {
    const last = dateOf(LAB_HISTORY_DAYS + LAB_GAP_DAYS);
    stage("recovered", "D", { quality: quality({ total_rows: 125 }), rows: [row(dateOf(LAB_HISTORY_DAYS), 0, 0.05), row(last, 0, 0.01)] });
    expect(screen.queryByTestId("gap-band")).not.toBeInTheDocument();
    const tile = screen.getByTestId("forecast-tile");
    expect(within(tile).getByText(/sin alerta/i)).toBeInTheDocument();
    expect(within(tile).getByText(/0,01/)).toBeInTheDocument();
    expect(screen.getAllByTestId("forecast-marker")).toHaveLength(2);
  });

  it("states an ALERT after the drought only when the backend issued one", () => {
    const last = dateOf(LAB_HISTORY_DAYS + LAB_GAP_DAYS + LAB_DRY_DAYS);
    const { unmount } = stage("drought", "E", { quality: quality({ total_rows: 139 }), rows: [row(dateOf(LAB_HISTORY_DAYS), 0, 0.05), row(last, 1, 0.8)] });
    expect(screen.getByTestId("dry-band")).toBeInTheDocument();
    expect(within(screen.getByTestId("forecast-tile")).getByText(/alerta · prob/i)).toBeInTheDocument();
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/ALERTA/);
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/no la confirma/i);
    expect(screen.getByTestId("alert-marker")).toBeInTheDocument();
    unmount();

    // Si el backend no alertó, la escena no lo presenta como alerta.
    stage("drought", "E", { quality: quality({ total_rows: 139 }), rows: [row(last, 0, 0.3)] });
    expect(screen.queryByTestId("alert-marker")).not.toBeInTheDocument();
    expect(screen.getByTestId("lab-caption")).not.toHaveTextContent(/ALERTA/);
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/no emitió alerta/i);
  });

  it("lists every forecast under the chart with its step letter and the backend verdict, so labels never overlap", () => {
    const anomalyDate = dateOf(LAB_HISTORY_DAYS);
    const recovered = dateOf(LAB_HISTORY_DAYS + LAB_GAP_DAYS);
    const last = dateOf(LAB_HISTORY_DAYS + LAB_GAP_DAYS + LAB_DRY_DAYS);
    stage("drought", "E", {
      quality: quality({ total_rows: 139 }),
      rows: [row(dateOf(LAB_HISTORY_DAYS - 1), 0, 0.02), row(anomalyDate, 0, 0.05), row(recovered, 0, 0.01), row(last, 1, 0.8)],
    });
    const legend = screen.getByRole("list", { name: /pronósticos emitidos/i });
    const items = within(legend).getAllByRole("listitem").map((item) => item.textContent);
    expect(items).toEqual([
      expect.stringMatching(/^A · sin alerta · prob\. 0,02/),
      expect.stringMatching(/^B · sin alerta · prob\. 0,05/),
      expect.stringMatching(/^D · sin alerta · prob\. 0,01/),
      expect.stringMatching(/^E · ALERTA · prob\. 0,80/),
    ]);
    // Los rombos del gráfico llevan solo la letra del paso; el detalle está en la leyenda.
    expect(screen.queryByText(/sin alerta · prob\./, { selector: "svg text" })).not.toBeInTheDocument();
  });

  it("lets the charts shrink so a wide chart scrolls inside its box instead of widening the page (CSS)", () => {
    const css = readFileSync(resolve(__dirname, "LabStage.css"), "utf-8");
    const stage = css.match(/\.ls-stage\s*\{([^}]*)\}/);
    expect(stage, "regla .ls-stage").not.toBeNull();
    expect(stage![1]).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    const chart = css.match(/\.ls-chart\s*\{([^}]*)\}/);
    expect(chart![1]).toMatch(/min-width:\s*0/);
    expect(css).toMatch(/\.ls-scroll\s*\{[^}]*overflow-x:\s*auto/);
  });

  it("keeps the synthetic label and never claims scientific evidence", () => {
    stage("drought", "E", { quality: quality({ total_rows: 139 }), rows: [row(dateOf(LAB_HISTORY_DAYS + LAB_GAP_DAYS + LAB_DRY_DAYS), 1, 0.8)] });
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/datos sintéticos/i);
    expect(screen.getByTestId("lab-caption")).toHaveTextContent(/no es evidencia científica/i);
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("counts the values quality flagged out of range", () => {
    stage("anomaly", "B", { quality: quality({ total_rows: 121, out_of_range: { temperature: ["2026-10-27T00:00:00"] } }) });
    const tile = screen.getByTestId("quality-tile");
    expect(within(tile).getByText(/1 valor marcado/i)).toBeInTheDocument();
    expect(within(tile).getByText(/121 filas/)).toBeInTheDocument();
  });
});
