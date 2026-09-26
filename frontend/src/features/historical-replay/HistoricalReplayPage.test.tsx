import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HistoricalReplayPage } from "./HistoricalReplayPage";
import * as api from "./api";
import { ReplayNotFoundError } from "./api";

const CANDIDATE: api.ReplayCandidateInfo = {
  experiment_id: "4",
  run_id: "1157696b7bb941e394c5af530c762b07",
  config_name: "base",
  seed: 4,
  horizon_days: 3,
  periodo_inicio: "2024-10-19",
  periodo_fin: "2024-12-31",
  disclaimers: {
    reproduccion_retrospectiva: true,
    proxy_estadistico_relativo: true,
    utilidad_agronomica_demostrada: false,
  },
  limitaciones: ["Calibración no acreditada para este run."],
  evidencia: {
    package_id: "base-seed4-1157696b7b-v2",
    dataset_name: "melchor_romero_2024_consolidado",
    commit_sha: "2a40ee68c52d2eb5e2040a36b1029f756f9c048a",
    split_date: "2024-10-19",
    training_max_date: "2024-10-15",
    day_convention: "UTC_naive_midnight",
    issuance_assumption: "Supuesto de disponibilidad diaria documentado.",
  },
  regla_etiqueta: {
    variable: "soil_moisture",
    unidad: "m3/m3",
    operador: "less_than",
    umbral: 0.31678178906440735,
    percentil: 20.0,
  },
};

const ORIGINS = ["2024-10-19", "2024-10-20"];

function clockValue(): HTMLElement {
  return screen.getByTestId("hr-clock-value");
}

function baseMocks() {
  vi.spyOn(api, "getCandidate").mockResolvedValue(CANDIDATE);
  vi.spyOn(api, "listOrigins").mockResolvedValue({
    origins: ORIGINS.map((o) => ({ timestamp_origen: o })),
  });
  vi.spyOn(api, "getHistory").mockResolvedValue({ simulated_date: "2024-10-19", rows: [] });
  vi.spyOn(api, "getFeedback").mockResolvedValue({ timestamp_origen: "2024-10-19", feedback: [] });
}

function predictionAt(overrides: Partial<api.ReplayPredictionResponse> = {}): api.ReplayPredictionResponse {
  return {
    timestamp_origen: "2024-10-19",
    target_timestamp: "2024-10-22",
    experiment_id: "4",
    run_id: "1157696b7bb941e394c5af530c762b07",
    config_name: "base",
    seed: 4,
    horizon_days: 3,
    disclaimers: CANDIDATE.disclaimers,
    y_pred: 0,
    ...overrides,
  };
}

describe("HistoricalReplayPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an unavailable message when the backend feature is disabled", async () => {
    vi.spyOn(api, "getCandidate").mockRejectedValue(new ReplayNotFoundError("Not Found"));
    vi.spyOn(api, "listOrigins").mockResolvedValue({ origins: [] });

    render(<HistoricalReplayPage />);

    await waitFor(() => screen.getByText(/no está habilitada/i));
  });

  it("selects the first available origin and shows the prediction without future fields", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(predictionAt());

    render(<HistoricalReplayPage />);

    await waitFor(() => screen.getByText(/no se anticipó humedad por debajo del umbral/i));
    expect(screen.queryByRole("heading", { name: /^Resultado$/i })).toBeInTheDocument();
    expect(screen.getByText(/Resultado todavía oculto/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Feedback de demostración/i })).not.toBeInTheDocument();
  });

  it("reveals the observation and the feedback form exactly at the target date (scenario 2)", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockImplementation(async (_origin, simulatedDate) => {
      const base = predictionAt();
      if (simulatedDate < "2024-10-22") return base;
      return {
        ...base,
        target_observed: true,
        y_true: 1,
        coincide: false,
        medicion_original: { estado: "medida", valor: 0.28 },
      };
    });

    render(<HistoricalReplayPage />);
    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-19"));

    fireEvent.click(screen.getByRole("button", { name: /ver qué ocurrió/i }));

    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-22"));
    await waitFor(() => screen.getByText("Omisión de alerta"));
    await waitFor(() => screen.getByRole("heading", { name: /Feedback de demostración/i }));
  });

  it("advancing day-by-day to the target also reveals the correct result", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockImplementation(async (_origin, simulatedDate) => {
      const base = predictionAt();
      if (simulatedDate < "2024-10-22") return base;
      return {
        ...base,
        target_observed: true,
        y_true: 0,
        coincide: true,
        medicion_original: { estado: "medida", valor: 0.4 },
      };
    });

    render(<HistoricalReplayPage />);
    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-19"));

    fireEvent.click(screen.getByRole("button", { name: /avanzar un día/i }));
    fireEvent.click(screen.getByRole("button", { name: /avanzar un día/i }));
    fireEvent.click(screen.getByRole("button", { name: /avanzar un día/i }));

    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-22"));
    await waitFor(() => screen.getByText("Ausencia de alerta correcta"));
  });

  it("retreating hides the result again without altering the prediction (scenario 3)", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockImplementation(async (_origin, simulatedDate) => {
      const base = predictionAt();
      if (simulatedDate < "2024-10-22") return base;
      return {
        ...base,
        target_observed: true,
        y_true: 1,
        coincide: false,
        medicion_original: { estado: "medida", valor: 0.28 },
      };
    });

    render(<HistoricalReplayPage />);
    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-19"));
    fireEvent.click(screen.getByRole("button", { name: /ver qué ocurrió/i }));
    await waitFor(() => screen.getByText("Omisión de alerta"));

    fireEvent.click(screen.getByRole("button", { name: /retroceder un día/i }));

    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-21"));
    expect(screen.queryByText("Omisión de alerta")).not.toBeInTheDocument();
    expect(screen.getByText(/Resultado todavía oculto/i)).toBeInTheDocument();
  });

  it('"Volver al inicio de este caso" resets the clock but keeps the selected origin (scenario 4)', async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(predictionAt());

    render(<HistoricalReplayPage />);
    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-19"));

    fireEvent.change(screen.getByLabelText(/Datos disponibles hasta/i), {
      target: { value: "2024-10-20" },
    });
    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-20"));

    fireEvent.click(screen.getByRole("button", { name: /avanzar un día/i }));
    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-21"));

    fireEvent.click(screen.getByRole("button", { name: /volver al inicio de este caso/i }));

    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-20"));
    expect(screen.getByLabelText(/Datos disponibles hasta/i)).toHaveValue("2024-10-20");
  });

  it("changing the origin resets the case, moves the clock to it, and hides the previous result", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(
      predictionAt({ target_observed: true, y_true: 1, coincide: false, medicion_original: { estado: "medida", valor: 0.28 } }),
    );

    render(<HistoricalReplayPage />);
    await waitFor(() => screen.getByText("Omisión de alerta"));

    fireEvent.change(screen.getByLabelText(/Datos disponibles hasta/i), {
      target: { value: "2024-10-20" },
    });

    // Se descarta de inmediato, sin depender de que la nueva consulta termine.
    expect(screen.queryByText("Omisión de alerta")).not.toBeInTheDocument();
    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-20"));
  });

  it("ignores a late response from a previous simulated date (scenario 5, A→B→A)", async () => {
    baseMocks();
    let resolveFirst: (value: api.ReplayPredictionResponse) => void = () => {};
    const firstPromise = new Promise<api.ReplayPredictionResponse>((resolve) => {
      resolveFirst = resolve;
    });
    const predictionSpy = vi
      .spyOn(api, "getPrediction")
      .mockImplementationOnce(() => firstPromise)
      .mockImplementation(async () => predictionAt());

    render(<HistoricalReplayPage />);
    await waitFor(() => expect(predictionSpy).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: /avanzar un día/i }));
    await waitFor(() => expect(predictionSpy).toHaveBeenCalledTimes(2));

    resolveFirst(predictionAt({ y_pred: 1 }));

    await waitFor(() => expect(clockValue()).toHaveTextContent("2024-10-20"));
    expect(screen.getByText(/no se anticipó humedad por debajo del umbral/i)).toBeInTheDocument();
  });

  it("keeps the correct state after out-of-order A→B→A navigation", async () => {
    baseMocks();
    const responses = new Map<string, () => void>();
    vi.spyOn(api, "getPrediction").mockImplementation(
      (origin) =>
        new Promise((resolve) => {
          responses.set(origin, () =>
            resolve(predictionAt({ timestamp_origen: origin, y_pred: origin === "2024-10-19" ? 0 : 1 })),
          );
        }),
    );

    render(<HistoricalReplayPage />);
    await waitFor(() => expect(responses.has("2024-10-19")).toBe(true));

    fireEvent.change(screen.getByLabelText(/Datos disponibles hasta/i), {
      target: { value: "2024-10-20" },
    });
    await waitFor(() => expect(responses.has("2024-10-20")).toBe(true));

    fireEvent.change(screen.getByLabelText(/Datos disponibles hasta/i), {
      target: { value: "2024-10-19" },
    });

    responses.get("2024-10-19")?.();
    await waitFor(() => screen.getByText(/no se anticipó humedad por debajo del umbral/i));
    responses.get("2024-10-20")?.();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.getByText(/no se anticipó humedad por debajo del umbral/i)).toBeInTheDocument();
  });

  it("does not let a feedback POST started for A populate B after navigating away (scenario 6)", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(
      predictionAt({ target_observed: true, y_true: 1, coincide: false, medicion_original: { estado: "medida", valor: 0.28 } }),
    );
    vi.spyOn(api, "getFeedback").mockResolvedValue({ timestamp_origen: "2024-10-19", feedback: [] });
    let resolvePost: (value: api.ReplayFeedbackEntry) => void = () => {};
    const postPromise = new Promise<api.ReplayFeedbackEntry>((resolve) => {
      resolvePost = resolve;
    });
    vi.spyOn(api, "createFeedback").mockReturnValue(postPromise);

    render(<HistoricalReplayPage />);
    await waitFor(() => screen.getByRole("button", { name: /Registrar feedback/i }));

    fireEvent.click(screen.getByRole("button", { name: /Registrar feedback/i }));

    fireEvent.change(screen.getByLabelText(/Datos disponibles hasta/i), {
      target: { value: "2024-10-20" },
    });

    resolvePost({
      timestamp_origen: "2024-10-19",
      estado_validacion: "confirmada",
      etiqueta_corregida: null,
      observacion: "Feedback de A tardío",
      registered_at: "2026-01-01T00:00:00Z",
      simulated_at: "2024-10-22",
    });

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByText(/Feedback de A tardío/)).not.toBeInTheDocument();
  });

  const CATEGORY_CASES: [string, 0 | 1, 0 | 1][] = [
    ["Alerta correcta", 1, 1],
    ["Falsa alerta", 1, 0],
    ["Omisión de alerta", 0, 1],
    ["Ausencia de alerta correcta", 0, 0],
  ];
  for (const [label, yPred, yTrue] of CATEGORY_CASES) {
    it(`shows the "${label}" outcome category (scenario 7)`, async () => {
      baseMocks();
      vi.spyOn(api, "getPrediction").mockResolvedValue(
        predictionAt({
          y_pred: yPred,
          target_observed: true,
          y_true: yTrue,
          coincide: yPred === yTrue,
          medicion_original: { estado: "medida", valor: 0.3 },
        }),
      );

      render(<HistoricalReplayPage />);

      await waitFor(() => screen.getByText(label));
    });
  }

  it("does not show a comparison when target_observed is false, and does not label it as no-alert (scenario 8a)", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(predictionAt({ target_observed: false }));

    render(<HistoricalReplayPage />);

    await waitFor(() => screen.getByText(/Observación no disponible/i));
    expect(screen.queryByText("Ausencia de alerta correcta")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Feedback de demostración/i })).not.toBeInTheDocument();
  });

  it("distinguishes a history fetch error from an empty history (scenario 8b)", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(predictionAt());
    vi.spyOn(api, "getHistory").mockRejectedValue(new Error("500"));

    render(<HistoricalReplayPage />);

    await waitFor(() => screen.getByText(/Error al consultar el historial/i));
    expect(screen.queryByText(/Todavía no hay historial disponible/i)).not.toBeInTheDocument();
  });

  it("distinguishes a feedback fetch error and does not silently enable the form (scenario 8c)", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(
      predictionAt({ target_observed: true, y_true: 1, coincide: false, medicion_original: { estado: "medida", valor: 0.28 } }),
    );
    vi.spyOn(api, "getFeedback").mockRejectedValue(new Error("500"));

    render(<HistoricalReplayPage />);

    await waitFor(() => screen.getByText(/No se pudo consultar el feedback existente/i));
    expect(screen.queryByRole("button", { name: /Registrar feedback/i })).not.toBeInTheDocument();
  });

  it("shows the signed distance to threshold with unit and denomination, not 'model error' (scenario 9)", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(
      predictionAt({
        target_observed: true,
        y_true: 1,
        coincide: false,
        medicion_original: { estado: "medida", valor: 0.28 },
      }),
    );

    render(<HistoricalReplayPage />);

    // 0.28 - 0.31678178906440735 ≈ -0.037
    await waitFor(() => screen.getByText(/-0\.037 m3\/m3 \(por debajo del umbral\)/));
    expect(screen.queryByText(/error del modelo/i)).not.toBeInTheDocument();
  });

  it("does not compute a distance to threshold without a valid revealed measurement", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(
      predictionAt({
        target_observed: true,
        y_true: 1,
        coincide: false,
        medicion_original: { estado: "sin_dato_en_fuente", valor: null },
      }),
    );

    render(<HistoricalReplayPage />);

    await waitFor(() => screen.getByText("No calculable sin medición válida"));
  });

  it("still shows real data under StrictMode's dev mount→cleanup→mount double-invoke", async () => {
    baseMocks();
    vi.spyOn(api, "getPrediction").mockResolvedValue(predictionAt());

    render(
      <StrictMode>
        <HistoricalReplayPage />
      </StrictMode>,
    );

    await waitFor(() => screen.getByText(/no se anticipó humedad por debajo del umbral/i));
  });
});
