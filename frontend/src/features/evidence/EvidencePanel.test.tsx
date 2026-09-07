import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidencePanel } from "./EvidencePanel";

describe("EvidencePanel", () => {
  it("labels the formal evidence and the operational predictor as visually separate sections", () => {
    render(<EvidencePanel />);

    expect(
      screen.getByText(/evidencia experimental formal — controlled_daily_v3/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/^predictor operativo vigente$/i)).toBeInTheDocument();
  });

  it("shows the canonical, frozen F1 for the base configuration without recalculating it", () => {
    render(<EvidencePanel />);

    expect(screen.getByText(/0\.5592 ± 0\.0287/)).toBeInTheDocument();
  });

  it("cites the exact provenance (source file, mlflow experiment, scientific tag)", () => {
    const { container } = render(<EvidencePanel />);

    expect(container.textContent).toContain("reference-v3-formal-table.md");
    expect(container.textContent).toContain("hu7-controlled-daily-v3-formal");
    expect(container.textContent).toContain("scientific-baseline-v3");
  });

  it("does not present a recalibration as a metric improvement demonstration", () => {
    render(<EvidencePanel />);

    expect(
      screen.getByText(/no constituye evidencia de mejora métrica/i),
    ).toBeInTheDocument();
  });
});
