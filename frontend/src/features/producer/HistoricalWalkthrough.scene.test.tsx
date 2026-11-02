import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HistoricalWalkthrough } from "./HistoricalWalkthrough";
import * as historicalApi from "./historicalApi";
import type { Forecast, ForecastBatch, ForecastReview } from "./forecastsApi";
import type { ReadingRow, ReadingsResult } from "./readingsApi";

afterEach(() => vi.restoreAllMocks());

const SENSOR = "pergamino-ensemble-demo";
const FAMILIES = ["logistic_regression", "random_forest", "hist_gradient_boosting_classifier"] as const;
const CATEGORIES = {
  0: "sin_alerta_por_unanimidad", 1: "sin_alerta_por_mayoria_con_discrepancia",
  2: "posible_alerta_acuerdo_parcial", 3: "alerta_por_unanimidad",
} as const;
const REFERENCE = {
  model_version: "v1", horizon_days: 1 as const, contract_version: "producer_daily_h123_v1",
  trained_through: "2023-06-01", calibration_version: "cal-1", assessment_reference: "assessment-1",
};

function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

/** `votes[h-1]` modelos con alerta en el horizonte h; la alerta combinada se declara aparte. */
function batchFor(emission: string, reveal: string, alerts: boolean[], votes: Array<0 | 1 | 2 | 3>, reviewed: Record<number, "confirmed" | "rejected"> = {}): ForecastBatch {
  return {
    batch_id: `batch-${emission}`, revision: 1, as_of_date: emission, data_age_days: 0, server_today: emission,
    provenance: "external_reanalysis", calendar_timezone: "UTC",
    slots: [1, 2, 3].map((h) => {
      const target = addDays(emission, h);
      const status = reviewed[h];
      const review: ForecastReview = {
        status: status ?? "pending", revision: status ? 1 : 0, review_open_at: `${target}T00:00:00Z`,
        reviewable: target <= reveal, blocked_reason: target <= reveal ? null : "review_not_open",
        latest_review: status ? ({ action: status === "confirmed" ? "confirm" : "reject", comment: null, reviewed_at: `${target}T10:00:00Z` } as ForecastReview["latest_review"]) : null,
        training_eligibility: "no_review", applied_review_references: [],
      };
      const forecast: Forecast = {
        forecast_id: `fc-${emission}-${h}`, sensor_id: SENSOR, batch_id: `batch-${emission}`, as_of_date: emission,
        horizon_days: h as 1 | 2 | 3, target_date: target, contract_version: "producer_daily_h123_v1",
        issued_at: `${emission}T00:05:00Z`, snapshot_id: "s", alert: alerts[h - 1], score: 0.61, score_kind: "calibrated_probability",
        display_probability: null, probability_status: "not_qualified", probability_reason_code: null, decision_threshold: 0.5,
        event_threshold: { variable: "soil_moisture", value: 0.255, unit: "m3/m3", comparison: "lt" },
        model_reference: REFERENCE, review,
        ensemble: {
          policy_version: "ensemble_agreement_v1", ensemble_identity_sha256: "abc",
          weights: { logistic_regression: 1 / 3, random_forest: 1 / 3, hist_gradient_boosting_classifier: 1 / 3 },
          components: FAMILIES.map((family, index) => ({
            family, model_reference: REFERENCE, calibrated_through: "2023-06-01", score: 0.4, decision_threshold: 0.5, alert: index < votes[h - 1],
          })),
          combined_probability: 0.6, combined_alert: alerts[h - 1], positive_votes: votes[h - 1],
          agreement_category: CATEGORIES[votes[h - 1]], calibrated_through: "2023-06-01",
        },
      };
      return { ...forecast, status: "available" as const };
    }),
  };
}

function row(date: string, soil: number | null, imputed = false): ReadingRow {
  return {
    date, soil_moisture: soil, relative_humidity: null, solar_radiation: null, temperature: null, precipitation: null,
    wind_speed: null, et0: null, origin: "external_reanalysis", quality_flags: [],
    imputed_variables: imputed ? ["soil_moisture"] : [], unverified_variables: [],
  };
}

function readingsUntil(end: string, imputedDate?: string): ReadingsResult {
  const rows: ReadingRow[] = [];
  for (let date = "2023-06-08"; date <= end; date = addDays(date, 1)) {
    rows.push(row(date, 0.3 - (rows.length * 0.01), date === imputedDate));
  }
  return {
    sensor_id: SENSOR, calendar_timezone: "UTC", server_today: end, snapshot_id: null,
    window: { start_date: "2023-06-08", end_date: end, expected_days: rows.length }, status: "ready", rows, missing_dates: [],
    variable_coverage: [{ variable: "soil_moisture", observed_days: rows.length, missing_days: 0, imputed_days: imputedDate ? 1 : 0, unverified_days: 0 }],
    units: { soil_moisture: "m3/m3" }, last_reading_date: end, data_age_days: 0, provenance: "external_reanalysis",
  };
}

function setup(options: { alerts?: boolean[]; votes?: Array<0 | 1 | 2 | 3>; imputedDate?: string } = {}) {
  const alerts = options.alerts ?? [false, false, false];
  const votes = options.votes ?? [0, 0, 1];
  const reviewed: Record<number, "confirmed" | "rejected"> = {};
  const batch = vi.spyOn(historicalApi, "getHistoricalForecastBatch").mockImplementation(async (_sensor, emission, reveal) =>
    batchFor(emission, reveal ?? emission, alerts, votes, reviewed));
  vi.spyOn(historicalApi, "getHistoricalReadings").mockImplementation(async (_sensor, end) => readingsUntil(end, options.imputedDate));
  const submit = vi.spyOn(historicalApi, "submitHistoricalReview").mockImplementation(async (_s, _reveal, forecastId, request) => {
    const h = Number(forecastId.slice(-1));
    reviewed[h] = request.action === "confirm" ? "confirmed" : "rejected";
    return {
      status: reviewed[h], revision: 1, review_open_at: "2023-06-14T00:00:00Z", reviewable: true, blocked_reason: null,
      latest_review: { action: request.action, comment: request.comment, reviewed_at: "2023-06-14T10:00:00Z" } as ForecastReview["latest_review"],
      training_eligibility: "no_review", applied_review_references: [],
    } satisfies ForecastReview;
  });
  render(<HistoricalWalkthrough sensorId={SENSOR} defense />);
  return { batch, submit };
}

const clock = () => screen.getByRole("slider", { name: /reloj del recorrido/i });

describe("HistoricalWalkthrough — escena de defensa", () => {
  it("opens with a headline that states the backend verdict, never a probability", async () => {
    setup();
    expect(await screen.findByRole("heading", { level: 2, name: /13 de jun de 2023.*según los modelos, sin alerta de humedad baja/i })).toBeInTheDocument();
    // El eje del gráfico muestra la humedad del suelo en %; no es una probabilidad de alerta.
    expect(document.body).not.toHaveTextContent(/probabilidad|posibilidad de alerta|score/i);
    expect(screen.getByRole("group", { name: /pronóstico por horizonte/i })).not.toHaveTextContent(/%/);
    expect(screen.getByRole("heading", { level: 2 })).not.toHaveTextContent(/%/);
  });

  it("counts the horizons with alert in the headline", async () => {
    setup({ alerts: [false, true, true], votes: [0, 3, 2] });
    expect(await screen.findByRole("heading", { level: 2, name: /según los modelos, alerta de humedad baja en 2 de 3 horizontes/i })).toBeInTheDocument();
  });

  it("keeps one origin label and leaves the past nature to the app-wide replay badge", async () => {
    setup();
    await screen.findByRole("heading", { level: 2, name: /según los modelos/i });
    expect(screen.queryByText(/reproducción de datos pasados/i)).not.toBeInTheDocument();
    expect(screen.getByText(/datos externos · era5-land \/ nasa power \(reanálisis\)/i)).toBeInTheDocument();
    expect(screen.queryByText(/elegí una emisión guardada y avanzá el reloj/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Datos que se ven")).not.toBeInTheDocument();
  });

  it("selects among the five prepared emissions with buttons and reloads the batch", async () => {
    const { batch } = setup();
    const group = await screen.findByRole("group", { name: /emisión \(cuándo se hizo el pronóstico\)/i });
    const buttons = within(group).getAllByRole("button");
    expect(buttons).toHaveLength(5);
    expect(buttons[0]).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(buttons[1]);
    await waitFor(() => expect(batch).toHaveBeenLastCalledWith(SENSOR, "2023-06-14", undefined));
    expect(buttons[1]).toHaveAttribute("aria-pressed", "true");
    expect(buttons[0]).toHaveAttribute("aria-pressed", "false");
  });

  it("moves the walkthrough clock with a slider limited to the revealable days", async () => {
    const { batch } = setup();
    await screen.findByRole("heading", { level: 2, name: /según los modelos/i });
    expect(clock()).toHaveAttribute("min", "0");
    expect(clock()).toHaveAttribute("max", "7");
    expect(clock()).toHaveAttribute("aria-valuetext", expect.stringMatching(/al emitir/i));
    fireEvent.change(clock(), { target: { value: "2" } });
    await waitFor(() => expect(batch).toHaveBeenLastCalledWith(SENSOR, "2023-06-13", "2023-06-15"));
    expect(clock()).toHaveAttribute("aria-valuetext", expect.stringMatching(/\+2 días.*15 de jun/i));
    fireEvent.change(clock(), { target: { value: "0" } });
    await waitFor(() => expect(batch).toHaveBeenLastCalledWith(SENSOR, "2023-06-13", undefined));
  });

  it("shows one verdict cell per horizon with icon, word and the model vote, without a score", async () => {
    setup({ alerts: [false, true, true], votes: [1, 3, 2] });
    const strip = await screen.findByRole("group", { name: /pronóstico por horizonte/i });
    const cells = within(strip).getAllByRole("button");
    expect(cells).toHaveLength(3);
    expect(cells[0]).toHaveTextContent(/sin alerta/i);
    expect(cells[0]).toHaveTextContent(/1 de 3 modelos indica alerta/i);
    expect(cells[1]).toHaveTextContent(/alerta/i);
    expect(cells[1]).toHaveTextContent(/los 3 modelos coinciden en la alerta/i);
    expect(cells[2]).toHaveTextContent(/2 de 3 modelos indican alerta/i);
    expect(strip).not.toHaveTextContent(/score|probabilidad|%/i);
  });

  it("blocks the review of a horizon whose data is not revealed yet and says how far to advance", async () => {
    setup();
    const strip = await screen.findByRole("group", { name: /pronóstico por horizonte/i });
    await userEvent.click(within(strip).getAllByRole("button")[0]);
    const panel = await screen.findByRole("region", { name: /tu revisión · \+1/i });
    expect(within(panel).getByText(/todavía no se puede revisar.*14 de jun de 2023/i)).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: /confirmar resultado/i })).not.toBeInTheDocument();
    expect(within(panel).getByText(/revisión de prueba técnica en modo histórico/i)).toBeInTheDocument();
  });

  it("shows the revealed real value with its provenance and never says the forecast was right or wrong", async () => {
    setup({ imputedDate: "2023-06-14" });
    await screen.findByRole("group", { name: /pronóstico por horizonte/i });
    fireEvent.change(clock(), { target: { value: "1" } });
    const panel = await screen.findByRole("region", { name: /tu revisión · \+1/i });
    expect(await within(panel).findByText(/dato real revelado/i)).toHaveTextContent(/valor imputado/i);
    expect(document.body).not.toHaveTextContent(/acertó|no acertó|coincide con el dato|el pronóstico falló/i);
  });

  it.each([
    ["una ausencia de alerta", [false, false, false], [0, 0, 0] as Array<0 | 1 | 2 | 3>, "confirm", /confirmar resultado/i, "confirmada"],
    ["una alerta", [true, true, true], [3, 3, 3] as Array<0 | 1 | 2 | 3>, "reject", /rechazar resultado/i, "rechazada"],
  ] as const)("lets the person review %s once the data is revealed", async (_label, alerts, votes, action, buttonName, statusText) => {
    const { submit } = setup({ alerts: [...alerts], votes: [...votes] });
    await screen.findByRole("group", { name: /pronóstico por horizonte/i });
    fireEvent.change(clock(), { target: { value: "1" } });
    const panel = await screen.findByRole("region", { name: /tu revisión · \+1/i });
    await userEvent.click(await within(panel).findByRole("button", { name: buttonName }));
    await userEvent.type(within(panel).getByLabelText(/comentario/i), "visto en campo");
    await userEvent.click(within(panel).getByRole("button", { name: /guardar/i }));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(submit).toHaveBeenCalledWith(SENSOR, "2023-06-14", "fc-2023-06-13-1", expect.objectContaining({ action, comment: "visto en campo" }));
    const strip = screen.getByRole("group", { name: /pronóstico por horizonte/i });
    await waitFor(() => expect(within(strip).getAllByRole("button")[0]).toHaveTextContent(new RegExp(`revisión: ${statusText}`, "i")));
  });

  it("states what an alert means using the protocol threshold delivered by the backend", async () => {
    setup();
    expect(await screen.findByText(/humedad del suelo quede por debajo de 25\.5 %.*umbral del protocolo/i)).toBeInTheDocument();
  });

  it("keeps the decision-support notice visible", async () => {
    setup();
    await screen.findByRole("heading", { level: 2, name: /según los modelos/i });
    expect(screen.getByText(/apoyo a la decisión, no automatización del riego/i)).toBeInTheDocument();
    expect(screen.getByText(/«sin alerta» no garantiza ausencia de estrés/i)).toBeInTheDocument();
  });

  it("moves the details into tabs, with the quality counts one click away and keyboard navigation", async () => {
    setup();
    await screen.findByRole("heading", { level: 2, name: /según los modelos/i });
    const tabs = screen.getByRole("tablist", { name: /detalles/i });
    const [howTo, quality, trace, observations] = within(tabs).getAllByRole("tab");
    expect(howTo).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent(/no es una explicación de causas/i);
    await userEvent.click(quality);
    expect(screen.getByRole("tabpanel")).toHaveTextContent(/humedad del suelo en la ventana/i);
    quality.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(trace).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowRight}");
    expect(observations).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});
