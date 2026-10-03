import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import projection from "../../../public/retrospective-2023.json";
import { EvidenceResultsPage } from "./EvidenceResultsPage";

afterEach(() => vi.unstubAllGlobals());

function stubProjection() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => projection }));
}

it("keeps the governance status and the exploratory limits visible at the top, not behind a toggle", async () => {
  stubProjection();
  render(<EvidenceResultsPage />);
  expect(screen.getByText(/estado de gobernanza: evaluación exploratoria no independiente/i)).toBeVisible();
  expect(screen.getByText(/auditoría científica FAIL/i)).toBeVisible();
  expect(screen.getByText(/ningún resultado de esta sección acredita validación agronómica/i)).toBeVisible();
  await screen.findByText(/soporte común 364\/364/i);
});

it("compares methods by horizon with values taken from the versioned projection", async () => {
  stubProjection();
  render(<EvidenceResultsPage />);
  await screen.findByText(/soporte común 364\/364/i);
  await userEvent.click(screen.getByRole("button", { name: "+3 días" }));
  const group = screen.getByRole("group", { name: /MCC por método, horizonte \+3/i });
  const average = (projection.horizons as Record<string, { metrics: Record<string, { mcc: { value: number } }> }>)["3"].metrics.average.mcc.value;
  expect(within(group).getByText(average.toFixed(3))).toBeInTheDocument();
  // Persistencia es una referencia sin modelo y se identifica como tal.
  expect(within(group).getByText(/referencia sin modelo/i)).toBeInTheDocument();
});

it("shows counts as real integers, never as zero bars standing for missing data", async () => {
  stubProjection();
  render(<EvidenceResultsPage />);
  await screen.findByText(/soporte común 364\/364/i);
  await userEvent.click(screen.getByRole("button", { name: "Falsas alertas" }));
  const group = screen.getByRole("group", { name: /Falsas alertas por método/i });
  // Los conteos se muestran como enteros reales, no como 0 por falta de dato.
  expect(within(group).getAllByText(/^\d+$/).length).toBeGreaterThan(0);
});

it("presents the controlled v3 experiment with its limitations, separate from Pergamino", async () => {
  stubProjection();
  render(<EvidenceResultsPage />);
  await userEvent.click(screen.getByRole("tab", { name: /experimento controlado v3/i }));
  expect(screen.getByRole("group", { name: /F1 medio por configuración/i })).toBeInTheDocument();
  expect(screen.getByText(/«Completa» es consistentemente peor/i)).toBeInTheDocument();
  expect(screen.getByText(/diseño distinto de la evaluación de Pergamino 2023/i)).toBeInTheDocument();
});

it("does not show an aggregate panel for Melchor Romero and explains why", async () => {
  stubProjection();
  render(<EvidenceResultsPage />);
  await userEvent.click(screen.getByRole("tab", { name: /melchor romero/i }));
  expect(screen.getByRole("heading", { name: /melchor romero no tiene evaluación agregada propia/i })).toBeInTheDocument();
  expect(screen.getByText(/equivaldría a fabricar paridad/i)).toBeInTheDocument();
  expect(screen.queryByRole("group", { name: /MCC por método/i })).not.toBeInTheDocument();
});

it("follows the ARIA tabs pattern: roving tabindex and arrow, Home and End keys", async () => {
  stubProjection();
  render(<EvidenceResultsPage />);
  const first = screen.getByRole("tab", { name: /pergamino 2023/i });
  const second = screen.getByRole("tab", { name: /experimento controlado v3/i });
  const third = screen.getByRole("tab", { name: /melchor romero/i });
  expect(first).toHaveAttribute("tabindex", "0");
  expect(second).toHaveAttribute("tabindex", "-1");
  first.focus();
  await userEvent.keyboard("{ArrowRight}");
  expect(second).toHaveAttribute("aria-selected", "true");
  expect(second).toHaveFocus();
  await userEvent.keyboard("{End}");
  expect(third).toHaveAttribute("aria-selected", "true");
  await userEvent.keyboard("{ArrowRight}");
  expect(first).toHaveAttribute("aria-selected", "true");
  await userEvent.keyboard("{ArrowLeft}");
  expect(third).toHaveFocus();
  await userEvent.keyboard("{Home}");
  expect(first).toHaveFocus();
});

it("does not skip heading levels under the page title", async () => {
  stubProjection();
  render(<EvidenceResultsPage />);
  await screen.findByText(/soporte común 364\/364/i);
  expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /evidencia del pronóstico · 2023/i, level: 2 })).toBeInTheDocument();
  expect(screen.queryAllByRole("heading", { level: 3 }).length).toBeGreaterThan(0);
});
