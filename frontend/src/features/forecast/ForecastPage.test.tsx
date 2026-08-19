import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ForecastPage } from "./ForecastPage";
import * as api from "./api";

describe("ForecastPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("runs the forecast and shows the resulting alerts", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
        },
      ],
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));

    await waitFor(() => {
      expect(screen.getByText("2024-10-31")).toBeInTheDocument();
    });
    expect(screen.getByText(/pendiente/i)).toBeInTheDocument();
  });

  it("confirms an alert and updates its displayed state", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
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

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));
    await waitFor(() => screen.getByText("2024-10-31"));

    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }));

    await waitFor(() => {
      expect(screen.getByText(/confirmada/i)).toBeInTheDocument();
    });
  });
});
