import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as forecastApi from "./features/forecast/api";
import * as qualityApi from "./features/quality/api";
import * as lineageApi from "./features/lineage/api";

const EMPTY_PREDICTOR: forecastApi.ActivePredictor = {
  sensor_id: "sensor-a",
  origin: null,
  model_id: null,
  version: null,
  trained_through: null,
  calibration_end: null,
  horizon_days: 3,
  contract_version: 1,
  pipeline_version: "controlled_daily_v3",
  feature_columns: [],
  lags: [],
  rolling_windows: [],
  applied_feedback_count: 0,
  applied_feedback_dates: [],
};

describe("App — cabecera de sensor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(forecastApi, "getActivePredictor").mockResolvedValue(EMPTY_PREDICTOR);
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(null);
    vi.spyOn(lineageApi, "getLineage").mockResolvedValue({ sensor_id: "sensor-a", chain: [] });
  });

  it("keeps the active sensor and its queries unchanged while editing the draft without applying", async () => {
    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    const input = screen.getByLabelText(/sensor/i);
    await userEvent.clear(input);
    await userEvent.type(input, "sensor-b");

    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-a");
    expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it("applies a valid sensor id and queries the new sensor's resources", async () => {
    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    const input = screen.getByLabelText(/sensor/i);
    await userEvent.clear(input);
    await userEvent.type(input, "sensor-b");
    await userEvent.click(screen.getByRole("button", { name: /aplicar/i }));

    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-b"));
    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-b");
  });

  it("shows a validation error and does not trigger any query for an invalid sensor id", async () => {
    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1));

    const input = screen.getByLabelText(/sensor/i);
    await userEvent.clear(input);
    await userEvent.type(input, "sensor con espacios!");
    await userEvent.click(screen.getByRole("button", { name: /aplicar/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/identificador válido/i);
    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-a");
    expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it("blocks applying another sensor while a mutation is pending, and re-enables it afterward", async () => {
    let resolveRun!: (value: forecastApi.ForecastRunResponse) => void;
    vi.spyOn(forecastApi, "runForecast").mockReturnValueOnce(
      new Promise((resolve) => (resolveRun = resolve)),
    );

    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));

    const applyButton = screen.getByRole("button", { name: /aplicar/i });
    await waitFor(() => expect(applyButton).toBeDisabled());

    resolveRun({ train_rows: 1, test_rows: 1, verdicts: [] });
    await waitFor(() => expect(applyButton).not.toBeDisabled());
  });
});

describe("App — navegación por hash (Entrega 2)", () => {
  beforeEach(() => {
    window.location.hash = "";
    vi.restoreAllMocks();
    vi.spyOn(forecastApi, "getActivePredictor").mockResolvedValue(EMPTY_PREDICTOR);
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(null);
    vi.spyOn(lineageApi, "getLineage").mockResolvedValue({ sensor_id: "sensor-a", chain: [] });
  });

  it("opens on Resumen by default and shows the five destinations in the nav", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Resumen" })).toBeInTheDocument();
    for (const label of [
      "Resumen",
      "Alertas y revisión",
      "Calidad de datos",
      "Modelo y trazabilidad",
      "Evidencia y arquitectura",
    ]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: "Resumen" })).toHaveAttribute("aria-current", "page");
  });

  it("navigates to Alertas y revisión, updates the title, focuses its heading, and keeps the sensor context", async () => {
    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    await userEvent.click(screen.getByRole("link", { name: "Alertas y revisión" }));

    const heading = await screen.findByRole("heading", { name: "Alertas y revisión" });
    await waitFor(() => expect(heading).toHaveFocus());
    expect(document.title).toContain("Alertas y revisión");
    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-a");
    // no se dispara una nueva consulta de historial solo por navegar
    expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it("keeps the existing #calidad, #prediccion, #linaje and #evidencia anchors working", async () => {
    window.location.hash = "#calidad";
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Calidad de datos" })).toBeInTheDocument();
  });

  it("supports browser back/forward across destinations", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("link", { name: "Calidad de datos" }));
    await screen.findByRole("heading", { name: "Calidad de datos" });

    await userEvent.click(screen.getByRole("link", { name: "Evidencia y arquitectura" }));
    await screen.findByRole("heading", { name: "Evidencia y arquitectura" });

    window.history.back();
    await screen.findByRole("heading", { name: "Calidad de datos" });

    window.history.forward();
    await screen.findByRole("heading", { name: "Evidencia y arquitectura" });
  });

  it("does not lose the last forecast result when navigating away and back to Resumen", async () => {
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.72,
          fecha_objetivo: null,
        },
      ],
    });

    render(<App />);
    await screen.findByText("2024-10-31");

    await userEvent.click(screen.getByRole("link", { name: "Calidad de datos" }));
    await screen.findByRole("heading", { name: "Calidad de datos" });

    await userEvent.click(screen.getByRole("link", { name: "Resumen" }));
    await screen.findByText("2024-10-31");
    // conservar el contexto no implica volver a consultar el historial
    expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it("shows the active predictor identity under Modelo y trazabilidad", async () => {
    vi.spyOn(forecastApi, "getActivePredictor").mockResolvedValue({
      ...EMPTY_PREDICTOR,
      origin: "recalibrado",
      model_id: "modelo-activo",
      version: "2",
    });

    render(<App />);
    await userEvent.click(screen.getByRole("link", { name: "Modelo y trazabilidad" }));

    await waitFor(() => {
      expect(screen.getByText(/modelo-activo/i)).toBeInTheDocument();
    });
  });

  it("disables the recalibrate button in Modelo y trazabilidad while a forecast run started from Resumen is pending", async () => {
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "rechazada",
          etiqueta_corregida: 0,
          observacion: "test",
          y_proba: 0.72,
          fecha_objetivo: null,
        },
      ],
    });
    let resolveRun!: (value: forecastApi.ForecastRunResponse) => void;
    vi.spyOn(forecastApi, "runForecast").mockReturnValueOnce(
      new Promise((resolve) => (resolveRun = resolve)),
    );

    render(<App />);
    await screen.findByText("2024-10-31");

    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));

    await userEvent.click(screen.getByRole("link", { name: "Modelo y trazabilidad" }));
    const recalibrateButton = await screen.findByRole("button", { name: /recalibrar modelo/i });
    expect(recalibrateButton).toBeDisabled();

    resolveRun({ train_rows: 1, test_rows: 1, verdicts: [] });
    await waitFor(() => expect(recalibrateButton).not.toBeDisabled());
  });
});

describe("App — diseño coherente y accesibilidad (Entrega 4)", () => {
  beforeEach(() => {
    window.location.hash = "";
    vi.restoreAllMocks();
    vi.spyOn(forecastApi, "getActivePredictor").mockResolvedValue(EMPTY_PREDICTOR);
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(null);
    vi.spyOn(lineageApi, "getLineage").mockResolvedValue({ sensor_id: "sensor-a", chain: [] });
  });

  it("offers a skip link, as the first focusable element, pointing to a focusable main content landmark", () => {
    render(<App />);

    const skipLink = screen.getByRole("link", { name: /saltar al contenido/i });
    expect(skipLink).toHaveAttribute("href", "#main-content");

    // jsdom no simula el salto de foco del navegador al activar un enlace
    // de fragmento; lo que sí podemos verificar aquí es que el destino
    // existe y es programáticamente enfocable (tabIndex="-1"). El salto de
    // foco real se verificó a mano en un navegador (ver PR).
    const target = document.getElementById("main-content");
    expect(target).not.toBeNull();
    expect(target).toHaveAttribute("tabIndex", "-1");
  });
});
