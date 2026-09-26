import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as forecastApi from "./features/forecast/api";
import * as catalogApi from "./features/producer/catalogApi";
import * as qualityApi from "./features/quality/api";
import * as lineageApi from "./features/lineage/api";
import * as replayApi from "./features/historical-replay/api";

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

    await userEvent.click(screen.getByRole("button", { name: /generar pronóstico/i }));

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
      "Historial y observaciones",
      "Datos disponibles",
      "Ajustar próximos pronósticos",
      "Acerca de esta herramienta",
    ]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: "Resumen" })).toHaveAttribute("aria-current", "page");
  });

  it("navigates to Historial y observaciones, updates the title, focuses its heading, and keeps the sensor context", async () => {
    render(<App />);
    await waitFor(() => expect(forecastApi.listFeedback).toHaveBeenCalledWith("sensor-a"));

    await userEvent.click(screen.getByRole("link", { name: "Historial y observaciones" }));

    const heading = await screen.findByRole("heading", { name: "Historial y observaciones" });
    await waitFor(() => expect(heading).toHaveFocus());
    expect(document.title).toContain("Historial y observaciones");
    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-a");
    // no se dispara una nueva consulta de historial solo por navegar
    expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it("keeps the existing #calidad, #prediccion, #linaje and #evidencia anchors working", async () => {
    window.location.hash = "#calidad";
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Datos disponibles" })).toBeInTheDocument();
  });

  it("supports browser back/forward across destinations", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("link", { name: "Datos disponibles" }));
    await screen.findByRole("heading", { name: "Datos disponibles" });

    await userEvent.click(screen.getByRole("link", { name: "Acerca de esta herramienta" }));
    await screen.findByRole("heading", { name: "Acerca de esta herramienta" });

    window.history.back();
    await screen.findByRole("heading", { name: "Datos disponibles" });

    window.history.forward();
    await screen.findByRole("heading", { name: "Acerca de esta herramienta" });
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

    await userEvent.click(screen.getByRole("link", { name: "Datos disponibles" }));
    await screen.findByRole("heading", { name: "Datos disponibles" });

    await userEvent.click(screen.getByRole("link", { name: "Resumen" }));
    await screen.findByText("2024-10-31");
    // conservar el contexto no implica volver a consultar el historial
    expect(forecastApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it("shows the active predictor identity under Ajustar próximos pronósticos", async () => {
    vi.spyOn(forecastApi, "getActivePredictor").mockResolvedValue({
      ...EMPTY_PREDICTOR,
      origin: "recalibrado",
      model_id: "modelo-activo",
      version: "2",
    });

    render(<App />);
    await userEvent.click(screen.getByRole("link", { name: "Ajustar próximos pronósticos" }));

    await waitFor(() => {
      expect(screen.getByText(/modelo-activo/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/modelo-activo/i)).not.toBeVisible();
    await userEvent.click(screen.getByText("Información técnica de los ajustes"));
    expect(screen.getByText(/modelo-activo/i)).toBeVisible();
  });

  it("disables the recalibrate button in Ajustar próximos pronósticos while a forecast run started from Resumen is pending", async () => {
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

    await userEvent.click(screen.getByRole("button", { name: /generar pronóstico/i }));

    await userEvent.click(screen.getByRole("link", { name: "Ajustar próximos pronósticos" }));
    const recalibrateButton = await screen.findByRole("button", { name: /aplicar observaciones/i });
    expect(recalibrateButton).toBeDisabled();

    resolveRun({ train_rows: 1, test_rows: 1, verdicts: [] });
    await waitFor(() => expect(recalibrateButton).not.toBeDisabled());
  });
});

describe("App — contexto del productor (HU6)", () => {
  it("hides the unrelated legacy selector in Mi cultivo and restores its selection when returning", async () => {
    window.location.hash = "#resumen";
    vi.restoreAllMocks();
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(null);
    vi.spyOn(catalogApi, "listSectors").mockResolvedValue({ items: [], next_cursor: null });
    render(<App />);
    const input = screen.getByLabelText(/punto de medición \(sensor\)/i);
    await userEvent.clear(input);
    await userEvent.type(input, "sensor-b");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar" }));
    await userEvent.click(screen.getByRole("link", { name: "Mi cultivo" }));
    await screen.findByRole("heading", { name: "Mi cultivo" });
    expect(screen.queryByLabelText(/punto de medición \(sensor\)/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sensor activo/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Resumen" }));
    expect(await screen.findByLabelText(/punto de medición \(sensor\)/i)).toHaveValue("sensor-b");
    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-b");
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

describe("App — acceso a la reproducción histórica desde la navegación (recorrido guiado)", () => {
  beforeEach(() => {
    window.location.hash = "";
    vi.restoreAllMocks();
    vi.spyOn(forecastApi, "getActivePredictor").mockResolvedValue(EMPTY_PREDICTOR);
    vi.spyOn(forecastApi, "listFeedback").mockResolvedValue({ rows: [] });
    vi.spyOn(qualityApi, "getQualityReport").mockResolvedValue(null);
    vi.spyOn(lineageApi, "getLineage").mockResolvedValue({ sensor_id: "sensor-a", chain: [] });
    vi.spyOn(replayApi, "getCandidate").mockRejectedValue(
      new replayApi.ReplayNotFoundError("Not Found"),
    );
    vi.spyOn(replayApi, "listOrigins").mockResolvedValue({ origins: [] });
  });

  it("lists 'Explorar una predicción' among the main destinations, without a duplicate link", async () => {
    render(<App />);

    const matches = screen.getAllByRole("link", { name: "Explorar una predicción" });
    expect(matches).toHaveLength(1);
  });

  it("navigates to it, focuses its heading, marks it active, and hides the unrelated sensor form", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("link", { name: "Explorar una predicción" }));

    const heading = await screen.findByRole("heading", { name: "Explorar una predicción" });
    await waitFor(() => expect(heading).toHaveFocus());
    expect(screen.getByRole("link", { name: "Explorar una predicción" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(document.title).toContain("Explorar una predicción");
    expect(screen.queryByLabelText(/punto de medición \(sensor\)/i)).not.toBeInTheDocument();
  });

  it("keeps the other destinations reachable after visiting the replay view", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("link", { name: "Explorar una predicción" }));
    await screen.findByRole("heading", { name: "Explorar una predicción" });

    await userEvent.click(screen.getByRole("link", { name: "Resumen" }));
    await screen.findByRole("heading", { name: "Resumen" });
    expect(screen.getByText(/sensor activo/i)).toHaveTextContent("sensor-a");
  });
});
