import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DeploymentDiagram } from "./DeploymentDiagram";
import { DEPLOYMENT_COMPONENTS, DEPLOYMENT_TOUR } from "./deploymentCatalog";

function mockReducedMotion(matches: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockImplementation((query: string) => ({
      matches: matches && query.includes("prefers-reduced-motion"),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("DeploymentDiagram", () => {
  it("draws every component of the deployment as a selectable element", () => {
    render(<DeploymentDiagram />);
    const diagram = screen.getByRole("img", { name: /diagrama de despliegue/i });
    for (const component of DEPLOYMENT_COMPONENTS) {
      const escaped = component.label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      expect(within(diagram).getByRole("button", { name: new RegExp(`^${escaped}`) })).toBeInTheDocument();
    }
  });

  it("shows the sheet of a component with its responsibility, connections, evidence and limits", async () => {
    render(<DeploymentDiagram />);
    await userEvent.click(screen.getByRole("button", { name: /^MLflow/ }));
    const sheet = screen.getByRole("region", { name: /ficha de mlflow/i });
    for (const label of ["Responsabilidad", "Conexiones", "Evidencia", "Límites"]) {
      expect(within(sheet).getByText(label)).toBeInTheDocument();
    }
    expect(within(sheet).getByText("src/human_feedback/model_registry.py")).toBeInTheDocument();
  });

  it("labels the tour as illustrative and shows no data or metrics of its own", () => {
    render(<DeploymentDiagram />);
    expect(screen.getByText(/recorrido ilustrativo/i)).toBeInTheDocument();
    expect(screen.queryByText(/en ejecución|en curso|en tiempo real|latencia|trazas?/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("walks the tour step by step and marks the components involved", async () => {
    render(<DeploymentDiagram />);
    const caption = screen.getByTestId("tour-caption");
    await userEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    expect(caption).toHaveTextContent(DEPLOYMENT_TOUR[0].caption);
    expect(screen.getByRole("button", { name: /^Fuentes de datos/ })).toHaveAttribute("aria-current", "step");
    expect(screen.getByRole("button", { name: /^MLflow/ })).not.toHaveAttribute("aria-current");

    await userEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    expect(caption).toHaveTextContent(DEPLOYMENT_TOUR[1].caption);
    await userEvent.click(screen.getByRole("button", { name: /anterior/i }));
    expect(caption).toHaveTextContent(DEPLOYMENT_TOUR[0].caption);
  });

  it("stops at the last step and returns to the idle state when leaving the tour", async () => {
    render(<DeploymentDiagram />);
    const next = screen.getByRole("button", { name: /siguiente/i });
    for (let i = 0; i < DEPLOYMENT_TOUR.length + 3; i += 1) await userEvent.click(next);
    expect(screen.getByTestId("tour-caption")).toHaveTextContent(DEPLOYMENT_TOUR[DEPLOYMENT_TOUR.length - 1].caption);
    await userEvent.click(screen.getByRole("button", { name: /salir/i }));
    expect(screen.queryByRole("button", { current: "step" })).not.toBeInTheDocument();
    expect(screen.getByTestId("tour-caption")).not.toHaveTextContent(DEPLOYMENT_TOUR[0].caption);
  });

  it("plays the tour automatically, can be paused and ends on the last step", () => {
    mockReducedMotion(false);
    vi.useFakeTimers();
    render(<DeploymentDiagram />);
    fireEvent.click(screen.getByRole("button", { name: /ver el recorrido/i }));
    expect(screen.getByTestId("tour-caption")).toHaveTextContent(DEPLOYMENT_TOUR[0].caption);

    act(() => void vi.advanceTimersByTime(4200));
    expect(screen.getByTestId("tour-caption")).toHaveTextContent(DEPLOYMENT_TOUR[1].caption);

    fireEvent.click(screen.getByRole("button", { name: /pausar/i }));
    act(() => void vi.advanceTimersByTime(20000));
    expect(screen.getByTestId("tour-caption")).toHaveTextContent(DEPLOYMENT_TOUR[1].caption);

    fireEvent.click(screen.getByRole("button", { name: /ver el recorrido/i }));
    act(() => void vi.advanceTimersByTime(4200 * DEPLOYMENT_TOUR.length));
    expect(screen.getByTestId("tour-caption")).toHaveTextContent(DEPLOYMENT_TOUR[DEPLOYMENT_TOUR.length - 1].caption);
    expect(screen.getByRole("button", { name: /ver el recorrido/i })).toBeInTheDocument();
  });

  it("does not advance by itself when the user prefers reduced motion", () => {
    mockReducedMotion(true);
    vi.useFakeTimers();
    render(<DeploymentDiagram />);
    fireEvent.click(screen.getByRole("button", { name: /ver el recorrido/i }));
    expect(screen.getByTestId("tour-caption")).toHaveTextContent(DEPLOYMENT_TOUR[0].caption);
    act(() => void vi.advanceTimersByTime(60000));
    expect(screen.getByTestId("tour-caption")).toHaveTextContent(DEPLOYMENT_TOUR[0].caption);
  });

  it("offers a text alternative table that lists every component and connection", () => {
    render(<DeploymentDiagram />);
    const table = screen.getByRole("table", { name: /componentes y conexiones/i });
    for (const component of DEPLOYMENT_COMPONENTS) {
      expect(within(table).getByRole("rowheader", { name: component.label })).toBeInTheDocument();
    }
  });
});
