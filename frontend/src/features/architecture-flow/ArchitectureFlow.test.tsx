import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ArchitectureFlow } from "./ArchitectureFlow";

describe("ArchitectureFlow", () => {
  it("keeps the stage links to existing sections", () => {
    render(<ArchitectureFlow />);
    const flow = screen.getByRole("navigation", { name: /etapas de la arquitectura/i });
    expect(within(flow).getByRole("link", { name: "Datos IoT" })).toHaveAttribute("href", "#calidad");
    expect(within(flow).getByRole("link", { name: "Recalibración y linaje" })).toHaveAttribute("href", "#linaje");
  });

  it("states that the map is documented design, not live monitoring", () => {
    render(<ArchitectureFlow />);
    expect(screen.getByText(/diseño documentado/i)).toBeInTheDocument();
    expect(screen.getByText(/no es monitoreo en vivo|no refleja el estado en vivo/i)).toBeInTheDocument();
  });

  it("shows the node sheet with responsibility, boundary, evidence and limits when selected", async () => {
    render(<ArchitectureFlow />);
    await userEvent.click(screen.getByRole("button", { name: "Calidad", pressed: false }));
    const sheet = screen.getByRole("region", { name: /ficha de calidad/i });
    for (const label of ["Responsabilidad", "Entrada", "Salida", "Frontera", "Evidencia", "Límites"]) {
      expect(within(sheet).getByText(label)).toBeInTheDocument();
    }
    expect(within(sheet).getByText("src/data_quality/quality_report.py")).toBeInTheDocument();
  });

  it("offers a text alternative table that lists every node", () => {
    render(<ArchitectureFlow />);
    const table = screen.getByRole("table", { name: /componentes de la arquitectura/i });
    expect(within(table).getAllByRole("row").length).toBeGreaterThanOrEqual(8);
  });

  it("leads with the deployment diagram and keeps the pipeline stages below it", () => {
    render(<ArchitectureFlow />);
    const diagram = screen.getByRole("img", { name: /diagrama de despliegue/i });
    const stages = screen.getByRole("navigation", { name: /etapas de la arquitectura/i });
    expect(diagram.compareDocumentPosition(stages) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole("button", { name: /ver el recorrido/i })).toBeInTheDocument();
  });

  it("never presents a stage as running nor shows live metrics or traces", () => {
    render(<ArchitectureFlow />);
    expect(screen.queryByText(/en ejecución|en curso|en tiempo real|latencia|trazas?/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

});
