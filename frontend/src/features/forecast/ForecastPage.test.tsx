import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ForecastPage } from "./ForecastPage";
import { useForecastWorkspace } from "./useForecastWorkspace";
import * as api from "./api";
import { HttpError } from "./api";
import * as lineageApi from "../lineage/api";

/** Espejo mínimo de cómo App.tsx compone ForecastPage con el hook
 * compartido (entrega 2): el workspace se instancia una sola vez y se
 * pasa como prop, en vez de que ForecastPage lo posea. */
function Harness({ sensorId }: { sensorId: string }) {
  const workspace = useForecastWorkspace(sensorId);
  return <ForecastPage sensorId={sensorId} workspace={workspace} />;
}

describe("ForecastPage (Alertas y revisión)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("consults the persisted history on mount without running a forecast", async () => {
    const listFeedbackSpy = vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.72,
          fecha_objetivo: "2024-11-03",
        },
      ],
    });
    const runForecastSpy = vi.spyOn(api, "runForecast");

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByText("2024-10-31")).toBeInTheDocument();
    });
    expect(listFeedbackSpy).toHaveBeenCalledWith("sensor-a");
    expect(runForecastSpy).not.toHaveBeenCalled();
  });

  it("keeps rows without probability instead of dropping them", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-30",
          alerta_generada: 0,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: null,
          fecha_objetivo: null,
        },
      ],
    });

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => screen.getByText("2024-10-30"));
    expect(screen.getByText(/no disponible/i)).toBeInTheDocument();
  });

  it("reloads the history for the newly applied sensor and drops the previous one", async () => {
    const spy = vi.spyOn(api, "listFeedback");
    spy.mockResolvedValueOnce({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.5,
          fecha_objetivo: null,
        },
      ],
    });

    const { rerender } = render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByText("2024-10-31"));

    spy.mockResolvedValueOnce({
      rows: [
        {
          fecha: "2024-11-05",
          alerta_generada: 0,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.1,
          fecha_objetivo: null,
        },
      ],
    });

    rerender(<Harness sensorId="sensor-b" />);

    await waitFor(() => screen.getByText("2024-11-05"));
    expect(screen.queryByText("2024-10-31")).not.toBeInTheDocument();
    expect(spy).toHaveBeenLastCalledWith("sensor-b");
  });

  it("discards a late response from a sensor that is no longer active", async () => {
    const spy = vi.spyOn(api, "listFeedback");
    let resolveSensorA!: (value: api.FeedbackListResponse) => void;
    spy.mockReturnValueOnce(new Promise((resolve) => (resolveSensorA = resolve)));

    const { rerender } = render(<Harness sensorId="sensor-a" />);

    spy.mockResolvedValueOnce({
      rows: [
        {
          fecha: "2024-11-05",
          alerta_generada: 0,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.1,
          fecha_objetivo: null,
        },
      ],
    });
    rerender(<Harness sensorId="sensor-b" />);
    await waitFor(() => screen.getByText("2024-11-05"));

    resolveSensorA({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.9,
          fecha_objetivo: null,
        },
      ],
    });

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByText("2024-10-31")).not.toBeInTheDocument();
    expect(screen.getByText("2024-11-05")).toBeInTheDocument();
  });

  it("shows an explicit empty state on 404, distinct from a query error", async () => {
    vi.spyOn(api, "listFeedback").mockRejectedValue(
      new HttpError(404, "Todavía no se corrió ningún pronóstico."),
    );

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByText(/todavía no hay pronósticos registrados/i)).toBeInTheDocument();
    });
  });

  it("shows a retryable error (not a zero-count empty state) on a 500", async () => {
    vi.spyOn(api, "listFeedback").mockRejectedValue(new HttpError(500, "Error interno"));

    render(<Harness sensorId="sensor-a" />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/error interno/i);
    });
    expect(
      screen.queryByText(/todavía no hay pronósticos registrados/i),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reintentar/i })).toBeInTheDocument();
  });

  it("ignores a second click on Confirmar while the first confirmation is in flight", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({
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
    let resolveConfirm!: (value: api.FeedbackRow) => void;
    const confirmSpy = vi
      .spyOn(api, "confirmAlert")
      .mockReturnValueOnce(new Promise((resolve) => (resolveConfirm = resolve)));

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByText("2024-10-31"));

    const confirmButton = screen.getByRole("button", { name: /confirmar/i });
    await userEvent.click(confirmButton);
    await userEvent.click(confirmButton);

    expect(confirmSpy).toHaveBeenCalledTimes(1);

    resolveConfirm({
      fecha: "2024-10-31",
      alerta_generada: 1,
      estado_validacion: "confirmada",
      etiqueta_corregida: null,
      observacion: null,
    });
    await waitFor(() => expect(screen.getByText(/confirmada/i)).toBeInTheDocument());
  });

  it("keeps each row independent when there are two rows with different states", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({
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
        {
          fecha: "2024-10-30",
          alerta_generada: 0,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
          y_proba: 0.2,
          fecha_objetivo: null,
        },
      ],
    });
    vi.spyOn(api, "confirmAlert").mockResolvedValue({
      fecha: "2024-10-31",
      alerta_generada: 1,
      estado_validacion: "confirmada",
      etiqueta_corregida: null,
      observacion: null,
    });

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByText("2024-10-31"));

    const rows = screen.getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    const confirmButtons = screen.getAllByRole("button", { name: /confirmar/i });
    await userEvent.click(confirmButtons[0]);

    await waitFor(() =>
      expect(screen.getByText("2024-10-31").closest("li")).toHaveTextContent(/confirmada/i),
    );
    expect(screen.getByText("2024-10-30").closest("li")).toHaveTextContent(/pendiente/i);
  });

  it("shows the relative-signal disclaimer next to the probability gauge", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({ rows: [] });
    render(<Harness sensorId="sensor-a" />);
    expect(
      screen.getByText(/señal predictiva relativa del modelo/i),
    ).toBeInTheDocument();
  });

  it("shows a recalibrate button only when there is a pending correction, and using it shows the registered version and its lineage", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({
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
    vi.spyOn(api, "recalibrate").mockResolvedValue({
      version: "1",
      n_correcciones: 1,
      fechas_corregidas: ["2024-10-31"],
      recalibration_id: "abc123",
    });
    vi.spyOn(lineageApi, "getLineage").mockResolvedValue({
      sensor_id: "sensor-a",
      chain: [
        {
          recalibration_id: "abc123",
          source_model_id: "modelo-origen-000000",
          successor_model_id: "modelo-sucesor-000000",
          feedback_references: [
            {
              sensor_id: "sensor-a",
              fecha: "2024-10-31",
              model_version: "modelo-origen-000000",
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

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByRole("button", { name: /recalibrar modelo/i }));

    await userEvent.click(screen.getByRole("button", { name: /recalibrar modelo/i }));

    await waitFor(() => {
      expect(screen.getByText(/versión 1/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/recalibration_id abc123/i)).toBeInTheDocument();
    expect(screen.getByText(/predictor origen/i)).toBeInTheDocument();
  });

  it("does not show the recalibrate button when there are no pending corrections", async () => {
    vi.spyOn(api, "listFeedback").mockResolvedValue({
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

    render(<Harness sensorId="sensor-a" />);
    await waitFor(() => screen.getByText("2024-10-31"));

    expect(
      screen.queryByRole("button", { name: /recalibrar modelo/i }),
    ).not.toBeInTheDocument();
  });

  describe("filtros de historial (task 2.3)", () => {
    async function renderTwoRows() {
      vi.spyOn(api, "listFeedback").mockResolvedValue({
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
          {
            fecha: "2024-10-20",
            alerta_generada: 0,
            estado_validacion: "confirmada",
            etiqueta_corregida: null,
            observacion: null,
            y_proba: 0.2,
            fecha_objetivo: null,
          },
        ],
      });
      render(<Harness sensorId="sensor-a" />);
      await waitFor(() => screen.getByText("2024-10-31"));
    }

    it("filters by alert state without triggering new writes, and keeps the unfiltered counters", async () => {
      const listFeedbackSpy = vi.spyOn(api, "listFeedback");
      await renderTwoRows();
      const callsBeforeFilter = listFeedbackSpy.mock.calls.length;

      await userEvent.selectOptions(screen.getByLabelText(/^alerta$/i), "sin_alerta");

      expect(screen.queryByText("2024-10-31")).not.toBeInTheDocument();
      expect(screen.getByText("2024-10-20")).toBeInTheDocument();
      expect(listFeedbackSpy.mock.calls.length).toBe(callsBeforeFilter);
      // el contador general de "sin revisar" sigue contando el historial completo
      expect(screen.getByText(/feedback sin revisar/i).closest("p")).toHaveTextContent("1");
    });

    it("distinguishes 'no matches' from an empty history, and clears filters back to the full list", async () => {
      await renderTwoRows();

      await userEvent.selectOptions(screen.getByLabelText(/^alerta$/i), "alerta");
      await userEvent.selectOptions(screen.getByLabelText(/estado de validación/i), "rechazada");

      expect(
        screen.getByText(/sin coincidencias con los filtros aplicados/i),
      ).toBeInTheDocument();
      expect(
        screen.queryByText(/todavía no hay pronósticos registrados/i),
      ).not.toBeInTheDocument();

      await userEvent.click(screen.getByRole("button", { name: /limpiar filtros/i }));

      expect(screen.getByText("2024-10-31")).toBeInTheDocument();
      expect(screen.getByText("2024-10-20")).toBeInTheDocument();
    });

    it("filters by an inclusive reference-date range", async () => {
      await renderTwoRows();

      const desde = screen.getByLabelText(/fecha de referencia desde/i);
      await userEvent.type(desde, "2024-10-25");

      expect(screen.queryByText("2024-10-20")).not.toBeInTheDocument();
      expect(screen.getByText("2024-10-31")).toBeInTheDocument();
    });
  });
});
