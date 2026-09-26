import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MoistureHistoryChart } from "./MoistureHistoryChart";
import type { ReplayHistoryRow } from "./api";
import { addDaysIso } from "./dateUtils";

const THRESHOLD = { value: 0.3, unit: "m3/m3", variable: "soil_moisture" };

function row(fecha: string, soil_moisture: number | null): ReplayHistoryRow {
  return { fecha, soil_moisture };
}

describe("MoistureHistoryChart", () => {
  it("shows the empty-history message when there are no rows yet", () => {
    const { getByText } = render(
      <MoistureHistoryChart
        rows={[]}
        originDate="2024-10-19"
        targetDate="2024-10-22"
        simulatedDate="2024-10-19"
        threshold={THRESHOLD}
        predictedClass={null}
      />,
    );
    expect(getByText(/Todavía no hay historial disponible/)).toBeInTheDocument();
  });

  it("cuts the line at an explicit null value instead of joining across it (preserves gaps)", () => {
    const rows = [row("2024-10-19", 0.4), row("2024-10-20", null), row("2024-10-21", 0.35)];
    const { container } = render(
      <MoistureHistoryChart
        rows={rows}
        originDate="2024-10-19"
        targetDate="2024-10-22"
        simulatedDate="2024-10-21"
        threshold={THRESHOLD}
        predictedClass={null}
      />,
    );
    const polylines = container.querySelectorAll("polyline.hr-chart-line");
    // Un hueco corta el trazo en dos segmentos, nunca uno solo.
    expect(polylines.length).toBe(2);
    const circles = container.querySelectorAll("circle.hr-chart-point");
    expect(circles.length).toBe(2); // ningún punto para la fila nula
  });

  it("treats a calendar date entirely absent from rows the same as a null gap", () => {
    // Ausente el 2024-10-20 por completo (no solo con valor nulo).
    const rows = [row("2024-10-19", 0.4), row("2024-10-21", 0.35)];
    const { container } = render(
      <MoistureHistoryChart
        rows={rows}
        originDate="2024-10-19"
        targetDate="2024-10-22"
        simulatedDate="2024-10-21"
        threshold={THRESHOLD}
        predictedClass={null}
      />,
    );
    const polylines = container.querySelectorAll("polyline.hr-chart-line");
    expect(polylines.length).toBe(2);
  });

  it("places points on a real time scale, not evenly by row index", () => {
    // Tres filas con separación de 1, luego 5 días: si la escala fuera por
    // índice, las tres estarían equiespaciadas en X.
    const rows = [row("2024-10-01", 0.4), row("2024-10-02", 0.4), row("2024-10-07", 0.4)];
    const { container } = render(
      <MoistureHistoryChart
        rows={rows}
        originDate="2024-10-01"
        targetDate="2024-10-07"
        simulatedDate="2024-10-07"
        threshold={THRESHOLD}
        predictedClass={null}
      />,
    );
    const circles = Array.from(container.querySelectorAll("circle.hr-chart-point"));
    expect(circles.length).toBe(3);
    const xs = circles.map((c) => Number(c.getAttribute("cx")));
    const gap1 = xs[1] - xs[0];
    const gap2 = xs[2] - xs[1];
    // La segunda separación cubre 5 días de calendario contra 1: debe ser
    // proporcionalmente mayor, no igual.
    expect(gap2).toBeGreaterThan(gap1 * 3);
  });

  it("draws the predicted class as a separate band, never as a moisture curve value", () => {
    const rows = [row("2024-10-19", 0.4)];
    const { container, getByText } = render(
      <MoistureHistoryChart
        rows={rows}
        originDate="2024-10-19"
        targetDate="2024-10-22"
        simulatedDate="2024-10-19"
        threshold={THRESHOLD}
        predictedClass={{ value: 1, label: "Por debajo del umbral de humedad (1)" }}
      />,
    );
    expect(container.querySelector(".hr-chart-band-marker-alert")).toBeInTheDocument();
    expect(getByText("Alerta anticipada")).toBeInTheDocument();
    // Nunca se agrega un punto/polyline extra por la clase predicha en el
    // mismo eje numérico de humedad: solo las filas de historial la aportan.
    expect(container.querySelectorAll("circle.hr-chart-point").length).toBe(1);
  });

  it("shades the hidden future interval between the clock and the target when not yet revealed", () => {
    const rows = [row("2024-10-19", 0.4)];
    const { container } = render(
      <MoistureHistoryChart
        rows={rows}
        originDate="2024-10-19"
        targetDate="2024-10-22"
        simulatedDate="2024-10-19"
        threshold={THRESHOLD}
        predictedClass={null}
      />,
    );
    expect(container.querySelector(".hr-chart-hidden-interval")).toBeInTheDocument();
  });

  it("does not shade a hidden interval once the clock reaches the target", () => {
    const rows = [row("2024-10-19", 0.4), row("2024-10-22", 0.28)];
    const { container } = render(
      <MoistureHistoryChart
        rows={rows}
        originDate="2024-10-19"
        targetDate="2024-10-22"
        simulatedDate="2024-10-22"
        threshold={THRESHOLD}
        predictedClass={null}
      />,
    );
    expect(container.querySelector(".hr-chart-hidden-interval")).not.toBeInTheDocument();
  });

  it("offers to expand beyond the default ~30 day window only when there is more history available", () => {
    const manyRows: ReplayHistoryRow[] = [];
    for (let i = 0; i < 60; i += 1) {
      manyRows.push(row(addDaysIso("2024-08-01", i), 0.4));
    }
    const shortRows = [row("2024-10-19", 0.4)];

    const long = render(
      <MoistureHistoryChart
        rows={manyRows}
        originDate="2024-08-01"
        targetDate="2024-10-22"
        simulatedDate="2024-10-22"
        threshold={THRESHOLD}
        predictedClass={null}
      />,
    );
    expect(long.getByRole("button", { name: /ampliar/i })).toBeInTheDocument();
    long.unmount();

    const short = render(
      <MoistureHistoryChart
        rows={shortRows}
        originDate="2024-10-19"
        targetDate="2024-10-22"
        simulatedDate="2024-10-19"
        threshold={THRESHOLD}
        predictedClass={null}
      />,
    );
    expect(short.queryByRole("button", { name: /ampliar/i })).not.toBeInTheDocument();
  });
});
