import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ForecastPage } from "./ForecastPage";
import { useForecastWorkspace } from "./useForecastWorkspace";
import * as api from "./api";
import { HttpError } from "./api";
import type { DemoWriteGate } from "../demo/lock";
import { targetMaturity } from "./targetMaturity";

function Harness({ demoGate }: { demoGate?: DemoWriteGate }) {
  const workspace = useForecastWorkspace("sensor-a");
  return <ForecastPage sensorId="sensor-a" workspace={workspace} demoGate={demoGate} />;
}

function row(fecha_objetivo: string | null | undefined) {
  return {
    fecha: "2026-06-10",
    alerta_generada: 0,
    estado_validacion: "pendiente" as const,
    etiqueta_corregida: null,
    observacion: null,
    y_proba: 0.1,
    fecha_objetivo,
  };
}

async function flush() {
  await act(async () => {
    for (let i = 0; i < 5; i += 1) await Promise.resolve();
  });
}

async function renderWith(rows: ReturnType<typeof row>[], demoGate?: DemoWriteGate) {
  vi.spyOn(api, "listFeedback").mockResolvedValue({ rows });
  render(<Harness demoGate={demoGate} />);
  await flush();
}

// Reloj fijo: hoy = 2026-06-15 (UTC).
const NOW = "2026-06-15T10:00:00Z";

describe("ForecastPage: madurez del día objetivo (UTC)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"] });
    vi.setSystemTime(new Date(NOW));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("enables review when the target day is before today (yesterday)", async () => {
    await renderWith([row("2026-06-14")]);
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /corregir resultado/i })).toBeEnabled();
    expect(screen.queryByText(/disponible cuando termine/i)).toBeNull();
  });

  it("blocks review when the target day is today", async () => {
    await renderWith([row("2026-06-15")]);
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /corregir resultado/i })).toBeDisabled();
    expect(screen.getByText("Disponible cuando termine el día objetivo: 2026-06-15 (UTC).")).toBeInTheDocument();
  });

  it("blocks review when the target day is tomorrow", async () => {
    await renderWith([row("2026-06-16")]);
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled();
    expect(screen.getByText("Disponible cuando termine el día objetivo: 2026-06-16 (UTC).")).toBeInTheDocument();
  });

  it.each([null, undefined, "", "no-es-fecha", "2026-02-31"])(
    "blocks review and explains a missing or invalid target date (%s), without inventing one",
    async (value) => {
      await renderWith([row(value)]);
      expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /corregir resultado/i })).toBeDisabled();
      expect(
        screen.getByText("No se puede revisar este resultado porque no tiene una fecha objetivo verificable."),
      ).toBeInTheDocument();
    },
  );

  it("unlocks when the UTC day changes while the page stays open", async () => {
    vi.setSystemTime(new Date("2026-06-15T23:59:00Z"));
    await renderWith([row("2026-06-15")]);
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2 * 60 * 1000);
    });
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeEnabled();
  });

  it("re-evaluates on returning to the tab", async () => {
    await renderWith([row("2026-06-15")]);
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled();

    vi.setSystemTime(new Date("2026-06-16T00:30:00Z"));
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeEnabled();
  });

  it("keeps the review blocked when a demo gate blocks a mature target", async () => {
    const gate: DemoWriteGate = {
      locked: true,
      lockedReason: "Sesión en curso.",
      isRowReviewable: () => false,
      rowUnavailableReason: () => "Sesión en curso.",
    };
    await renderWith([row("2026-06-14")], gate);
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /corregir resultado/i })).toBeDisabled();
    expect(screen.getByText("Sesión en curso.")).toBeInTheDocument();
  });

  it("does not relax a demo gate that allows the row: time still blocks an immature target", async () => {
    const gate: DemoWriteGate = {
      locked: false,
      lockedReason: "",
      isRowReviewable: () => true,
      rowUnavailableReason: () => "",
    };
    await renderWith([row("2026-06-15")], gate);
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled();
  });

  it("re-checks the day before saving a correction from an already open form", async () => {
    const rejectSpy = vi.spyOn(api, "rejectAlert").mockResolvedValue({ ...row("2026-06-14"), estado_validacion: "rechazada" });
    await renderWith([row("2026-06-14")]);
    fireEvent.click(screen.getByRole("button", { name: /corregir resultado/i }));
    fireEvent.click(screen.getByRole("radio", { name: "Alerta" }));

    // El reloj retrocede (p. ej. corrección de hora del sistema): el objetivo deja de estar vencido.
    vi.setSystemTime(new Date("2026-06-14T09:00:00Z"));
    fireEvent.click(screen.getByRole("button", { name: /guardar corrección/i }));
    await flush();

    expect(rejectSpy).not.toHaveBeenCalled();
    expect(screen.getByText("Disponible cuando termine el día objetivo: 2026-06-14 (UTC).")).toBeInTheDocument();
  });

  it("still surfaces a backend 409 rejection for a mature target", async () => {
    vi.spyOn(api, "confirmAlert").mockRejectedValue(new HttpError(409, "El día objetivo todavía no terminó."));
    await renderWith([row("2026-06-14")]);
    fireEvent.click(screen.getByRole("button", { name: /confirmar/i }));
    await flush();
    expect(screen.getByRole("alert")).toHaveTextContent(/todavía no terminó/i);
  });
});

describe("ForecastPage: bloqueo por demoGate con el formulario de corrección abierto", () => {
  const permissive: DemoWriteGate = {
    locked: false,
    lockedReason: "",
    isRowReviewable: () => true,
    rowUnavailableReason: () => "",
  };
  const blocking: DemoWriteGate = {
    locked: true,
    lockedReason: "Sesión en curso.",
    isRowReviewable: () => false,
    rowUnavailableReason: () => "Sesión en curso.",
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"] });
    vi.setSystemTime(new Date(NOW));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("disables saving, shows the reason and never calls reject while blocked; keeps typed data and saves once allowed again", async () => {
    const rejectSpy = vi
      .spyOn(api, "rejectAlert")
      .mockResolvedValue({ ...row("2026-06-14"), estado_validacion: "rechazada" });
    vi.spyOn(api, "listFeedback").mockResolvedValue({ rows: [row("2026-06-14")] });
    const view = render(<Harness demoGate={permissive} />);
    await flush();

    // a-b. Objetivo vencido y gate permisivo: abrir la corrección y elegir una etiqueta.
    fireEvent.click(screen.getByRole("button", { name: /corregir resultado/i }));
    fireEvent.click(screen.getByRole("radio", { name: "Alerta" }));
    fireEvent.change(screen.getByLabelText(/observación/i), { target: { value: "texto escrito" } });
    const form = screen.getByRole("group", { name: /corregir resultado del/i });
    const save = within(form).getByRole("button", { name: /guardar corrección/i });
    expect(save).toBeEnabled();

    // c. El gate bloquea la fila sin desmontar el formulario.
    view.rerender(<Harness demoGate={blocking} />);
    await flush();
    const sameForm = screen.getByRole("group", { name: /corregir resultado del/i });
    expect(sameForm).toBe(form);

    // d. Botón deshabilitado, motivo visible, Cancelar disponible, sin llamadas a reject.
    expect(within(form).getByRole("button", { name: /guardar corrección/i })).toBeDisabled();
    expect(within(form).getByRole("button", { name: /cancelar/i })).toBeEnabled();
    expect(within(form).getByText("Sesión en curso.")).toBeInTheDocument();
    fireEvent.click(within(form).getByRole("button", { name: /guardar corrección/i }));
    await flush();
    expect(rejectSpy).not.toHaveBeenCalled();

    // e. Se vuelve a permitir: se conserva lo escrito y puede guardarse.
    view.rerender(<Harness demoGate={permissive} />);
    await flush();
    expect(screen.getByRole("radio", { name: "Alerta" })).toBeChecked();
    expect(screen.getByLabelText(/observación/i)).toHaveValue("texto escrito");
    expect(within(form).queryByText("Sesión en curso.")).toBeNull();
    fireEvent.click(within(form).getByRole("button", { name: /guardar corrección/i }));
    await flush();
    expect(rejectSpy).toHaveBeenCalledTimes(1);
  });

  it("the save handler re-checks the gate itself and does not rely on the disabled attribute", async () => {
    // Sin re-render entre el bloqueo y el clic: un gate mutable evaluado en el momento de actuar.
    let reviewable = true;
    const mutable: DemoWriteGate = {
      locked: false,
      lockedReason: "",
      isRowReviewable: () => reviewable,
      rowUnavailableReason: () => "Bloqueada por la demo.",
    };
    const rejectSpy = vi.spyOn(api, "rejectAlert");
    vi.spyOn(api, "listFeedback").mockResolvedValue({ rows: [row("2026-06-14")] });
    render(<Harness demoGate={mutable} />);
    await flush();
    fireEvent.click(screen.getByRole("button", { name: /corregir resultado/i }));
    fireEvent.click(screen.getByRole("radio", { name: "Alerta" }));
    reviewable = false;
    fireEvent.click(screen.getByRole("button", { name: /guardar corrección/i }));
    await flush();
    expect(rejectSpy).not.toHaveBeenCalled();
    expect(screen.getByText("Bloqueada por la demo.")).toBeInTheDocument();
  });
});

describe("targetMaturity", () => {
  it("compares strictly against the UTC day", () => {
    expect(targetMaturity("2026-06-14", "2026-06-15").status).toBe("mature");
    expect(targetMaturity("2026-06-15", "2026-06-15").status).toBe("immature");
    expect(targetMaturity(undefined, "2026-06-15").status).toBe("unverifiable");
  });
});
