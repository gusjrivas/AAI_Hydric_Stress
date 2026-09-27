import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import projection from "../../../public/retrospective-2023.json";
import { RetrospectiveEvidencePanel } from "./RetrospectiveEvidencePanel";

afterEach(() => vi.unstubAllGlobals());

it("keeps an aggregate-evidence failure recoverable", async () => {
  const fetch = vi.fn()
    .mockRejectedValueOnce(new Error("red no disponible"))
    .mockResolvedValueOnce({ ok: true, json: async () => projection });
  vi.stubGlobal("fetch", fetch);
  render(<RetrospectiveEvidencePanel />);
  expect(await screen.findByRole("alert")).toHaveTextContent("red no disponible");
  await userEvent.click(screen.getByRole("button", { name: /reintentar/i }));
  expect(await screen.findByText(/soporte común 364\/364/i)).toBeInTheDocument();
  expect(screen.getByText(/evaluación exploratoria no independiente/i)).toBeInTheDocument();
});

it("shows unavailable values as unavailable, never zero, for non-probabilistic comparisons", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => projection }));
  render(<RetrospectiveEvidencePanel />);
  await screen.findByText(/soporte común 364\/364/i);
  await userEvent.click(screen.getAllByText(/comparar métodos y episodios/i)[0]);
  const persistence = screen.getAllByRole("row", { name: /^Persistencia /i })[0];
  expect(persistence).toHaveTextContent("No disponible");
  expect(persistence).not.toHaveTextContent("0.000");
});
