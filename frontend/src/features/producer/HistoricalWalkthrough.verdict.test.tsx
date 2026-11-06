import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HistoricalWalkthrough } from "./HistoricalWalkthrough";
import * as historicalApi from "./historicalApi";
import type { EnsembleDetail, ForecastBatch } from "./forecastsApi";
import type { ReadingRow, ReadingsResult } from "./readingsApi";

afterEach(() => vi.restoreAllMocks());

const SHA = "a".repeat(64);
const ref = (h: 1 | 2 | 3, version: string | null) => ({
  model_version: version, horizon_days: h, contract_version: "producer_daily_h123_v1",
  trained_through: "2022-12-31", calibration_version: "cal-7", assessment_reference: "assess-9",
});

function ensemble(alert: boolean, version: string | null): EnsembleDetail {
  const families = ["logistic_regression", "random_forest", "hist_gradient_boosting_classifier"] as const;
  return {
    agreement_category: alert ? "alerta_por_unanimidad" : "sin_alerta_por_unanimidad",
    calibrated_through: "2023-01-31", combined_alert: alert, combined_probability: 0.4,
    components: families.map((family, i) => ({
      family, alert, calibrated_through: "2023-01-31", decision_threshold: 0.5, score: 0.2,
      model_reference: ref(1, version ? `${version}-${i}` : null),
    })),
    ensemble_identity_sha256: SHA, policy_version: "policy-v3", positive_votes: alert ? 3 : 0,
    weights: { logistic_regression: 0.4, random_forest: 0.3, hist_gradient_boosting_classifier: 0.3 },
  };
}

function batch(alert: boolean, version: string | null = "mv-1"): ForecastBatch {
  return {
    batch_id: "b", revision: 1, as_of_date: "2023-06-13", data_age_days: 0, server_today: "2023-06-13",
    provenance: "external_reanalysis", calendar_timezone: "UTC",
    slots: [
      {
        status: "available", forecast_id: "fc-1", sensor_id: "s", batch_id: "b", as_of_date: "2023-06-13",
        horizon_days: 1, target_date: "2023-06-14", contract_version: "producer_daily_h123_v1",
        issued_at: "2023-06-13T00:05:00Z", snapshot_id: "snap", alert, score: 0.4,
        score_kind: "ensemble_mean_of_calibrated_components", display_probability: null,
        probability_status: "not_qualified", probability_reason_code: null, decision_threshold: 0.5,
        event_threshold: { variable: "soil_moisture", value: 0.18, unit: "m3/m3", comparison: "lt" },
        model_reference: ref(1, version),
        review: { status: "pending", revision: 0, review_open_at: "2023-06-14T00:00:00Z", reviewable: true, blocked_reason: null, latest_review: null, training_eligibility: "no_review", applied_review_references: [] },
        ensemble: ensemble(alert, version),
      },
      { horizon_days: 2, target_date: "2023-06-15", status: "unavailable", reason_code: "model_not_available" },
      { horizon_days: 3, target_date: "2023-06-16", status: "unavailable", reason_code: "model_not_available" },
    ],
  };
}

const row = (date: string, soil: number | null): ReadingRow => ({
  date, soil_moisture: soil, relative_humidity: null, solar_radiation: null, temperature: null,
  precipitation: null, wind_speed: null, et0: null, origin: "external_reanalysis", quality_flags: [],
  imputed_variables: [], unverified_variables: [],
});

function readings(rows: ReadingRow[], end = "2023-06-13"): ReadingsResult {
  return {
    sensor_id: "s", calendar_timezone: "UTC", server_today: end, snapshot_id: null,
    window: { start_date: "2023-06-08", end_date: end, expected_days: 6 }, status: "ready", rows,
    missing_dates: [],
    variable_coverage: [{ variable: "soil_moisture", observed_days: rows.length, missing_days: 0, imputed_days: 0, unverified_days: 0 }],
    units: { soil_moisture: "m3/m3" }, last_reading_date: end, data_age_days: 0, provenance: "external_reanalysis",
  };
}
const PAST = ["2023-06-11", "2023-06-12", "2023-06-13"].map((d) => row(d, 0.3));

function setup(b: ForecastBatch, rows: ReadingRow[] = PAST, props: Partial<Parameters<typeof HistoricalWalkthrough>[0]> = {}) {
  vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(b);
  vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue(readings(rows));
  return render(<HistoricalWalkthrough sensorId="s" defense {...props} />);
}

const slider = () => screen.getByRole("slider", { name: /reloj del recorrido/i });
const openTab = async (name: RegExp) => userEvent.click(await screen.findByRole("tab", { name }));

describe("HistoricalWalkthrough — veredicto, jerarquía, trazabilidad, defensa en profundidad", () => {
  it("shows a readable alert verdict with the model vote and target date, hiding reality before the clock reaches it", async () => {
    setup(batch(true));
    const strip = await screen.findByRole("group", { name: /pronóstico por horizonte/i });
    const cell = within(strip).getAllByRole("button")[0];
    expect(cell).toHaveTextContent(/alerta/i);
    expect(cell).not.toHaveTextContent(/sin alerta/i);
    expect(cell).toHaveTextContent("Los 3 modelos coinciden en la alerta");
    expect(cell).toHaveTextContent(/14 de jun de 2023/i);
    await userEvent.click(cell);
    const panel = await screen.findByRole("region", { name: /tu revisión · \+1/i });
    expect(panel).toHaveTextContent(/todavía no se puede revisar/i);
    expect(panel).not.toHaveTextContent(/dato real revelado/i);
  });

  it("shows the no-alert verdict and reveals reality only once the clock reaches the target date", async () => {
    setup(batch(false), [...PAST, row("2023-06-14", 0.2)]);
    const strip = await screen.findByRole("group", { name: /pronóstico por horizonte/i });
    const cell = within(strip).getAllByRole("button")[0];
    expect(cell).toHaveTextContent(/sin alerta/i);
    expect(cell).toHaveTextContent("Los 3 modelos coinciden en que no hay alerta");
    fireEvent.change(slider(), { target: { value: "1" } });
    const panel = await screen.findByRole("region", { name: /tu revisión · \+1/i });
    await waitFor(() => expect(panel).toHaveTextContent(/dato real revelado/i));
    expect(panel).not.toHaveTextContent(/todavía no se puede revisar/i);
  });

  it("limits the clock slider to the revealable days of the emission", async () => {
    setup(batch(true), PAST, { availableDates: ["2023-06-13"], revealMax: "2023-06-14" });
    await screen.findByRole("group", { name: /pronóstico por horizonte/i });
    expect(slider()).toHaveAttribute("max", "1");
    fireEvent.change(slider(), { target: { value: "1" } });
    await waitFor(() => expect(slider()).toHaveAttribute("aria-valuetext", expect.stringMatching(/\+1 día.*14 de jun/i)));
    fireEvent.change(slider(), { target: { value: "9" } });
    expect(Number((slider() as HTMLInputElement).value)).toBeLessThanOrEqual(1);
  });

  it("shows the effective reveal date in the clock field from the start (classic mode)", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batch(true));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue(readings(PAST));
    render(<HistoricalWalkthrough sensorId="s" />);
    fireEvent.change(screen.getByLabelText(/emisión seleccionada/i), { target: { value: "2023-06-13" } });
    expect(await screen.findByLabelText(/recorrido hasta/i)).toHaveValue("2023-06-13");
  });

  it("keeps a half-edited (empty) clock field empty while editing instead of snapping back (classic mode)", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batch(true));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue(readings(PAST));
    render(<HistoricalWalkthrough sensorId="s" />);
    fireEvent.change(screen.getByLabelText(/emisión seleccionada/i), { target: { value: "2023-06-13" } });
    const clock = await screen.findByLabelText(/recorrido hasta/i);
    fireEvent.change(clock, { target: { value: "2023-06-15" } });
    expect(clock).toHaveValue("2023-06-15");
    fireEvent.change(clock, { target: { value: "" } });
    expect(clock).toHaveValue("");
    fireEvent.change(clock, { target: { value: "2023-06-14" } });
    await waitFor(() => expect(screen.getByLabelText(/recorrido hasta/i)).toHaveValue("2023-06-14"));
  });

  it("does not revive an old empty draft after the clock goes A -> B -> A (classic mode)", async () => {
    vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockResolvedValue(batch(true));
    vi.spyOn(historicalApi, "getHistoricalReadings").mockResolvedValue(readings(PAST));
    render(<HistoricalWalkthrough sensorId="s" />);
    fireEvent.change(screen.getByLabelText(/emisión seleccionada/i), { target: { value: "2023-06-13" } });
    const clock = await screen.findByLabelText(/recorrido hasta/i);
    fireEvent.change(clock, { target: { value: "" } });
    expect(clock).toHaveValue("");
    fireEvent.change(clock, { target: { value: "2023-06-14" } });
    await waitFor(() => expect(screen.getByLabelText(/recorrido hasta/i)).toHaveValue("2023-06-14"));
    fireEvent.change(screen.getByLabelText(/recorrido hasta/i), { target: { value: "2023-06-13" } });
    await waitFor(() => expect(screen.getByLabelText(/recorrido hasta/i)).toHaveValue("2023-06-13"));
  });

  it("traces the displayed prediction and declares unavailable lineage explicitly", async () => {
    setup(batch(true));
    await openTab(/trazabilidad/i);
    const trace = await screen.findByRole("region", { name: /trazabilidad de la predicción/i });
    expect(trace).toHaveTextContent("Versión del modelo: mv-1");
    for (const text of ["2022-12-31", "cal-7", "2023-01-31", "assess-9", "policy-v3", SHA, "mv-1-0", "mv-1-2", "0.4"]) {
      expect(trace).toHaveTextContent(text);
    }
    expect(trace).toHaveTextContent(/emisión.*13 de jun de 2023/is);
    expect(trace).toHaveTextContent(/Datos externos/);
    for (const label of ["SHA-256 del dataset", "Commit", "Semilla", "Corridas de MLflow", "Particiones", "Linaje de recalibración"]) {
      expect(within(trace).getByText(new RegExp(`${label}.*no disponible`, "is"))).toBeInTheDocument();
    }
  });

  it("says the model version is unavailable when the payload carries null, and follows the site's own source", async () => {
    setup(batch(true, null), PAST, { sourceSummary: { label: "Datos del sitio", detail: "Fuente propia de Melchor Romero" } });
    await openTab(/trazabilidad/i);
    const trace = await screen.findByRole("region", { name: /trazabilidad de la predicción/i });
    expect(trace).toHaveTextContent("Versión del modelo: no disponible");
    expect(trace).toHaveTextContent("Fuente propia de Melchor Romero");
    expect(trace).not.toHaveTextContent(/Pergamino|ERA5/);
    expect(trace).not.toHaveTextContent(/sonda/i);
  });

  it("drops client-side any observation row dated after the revealed clock", async () => {
    setup(batch(true), [...PAST, row("2023-06-14", 0.111)]);
    await screen.findByRole("group", { name: /pronóstico por horizonte/i });
    await openTab(/observaciones/i);
    await screen.findByRole("table");
    const bodyRows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(bodyRows).toHaveLength(3);
  });
});
