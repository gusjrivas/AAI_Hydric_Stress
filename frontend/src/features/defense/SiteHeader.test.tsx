import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SiteHeader } from "./SiteHeader";

describe("SiteHeader", () => {
  it.each([
    ["pergamino", "Pergamino", /13 al 17 de junio de 2023/],
    ["melchor", "Melchor Romero", /20 al 24 de octubre de 2024/],
  ] as const)("shows only the site name and its period for %s", (site, name, period) => {
    render(<SiteHeader site={site} />);
    expect(screen.getByRole("heading", { level: 1, name })).toBeInTheDocument();
    expect(screen.getByText(period)).toBeInTheDocument();
  });

  it("does not repeat the historical or external nature of the data, which the scene already states", () => {
    const { container } = render(<SiteHeader site="pergamino" />);
    expect(screen.queryByText("Datos externos")).not.toBeInTheDocument();
    expect(screen.queryByText("Histórico")).not.toBeInTheDocument();
    expect(screen.queryByText(/seguimiento histórico · recorrido histórico/i)).not.toBeInTheDocument();
    expect(container.querySelector(".site-chips")).toBeNull();
  });
});
