import { useEffect, useState } from "react";

/**
 * Condición de interfaz para revisar un resultado: el día objetivo debe
 * haber terminado en UTC (`fecha_objetivo < hoy UTC`). Solo decide qué
 * acciones ofrecer; la autoridad sigue siendo el backend, cuyos rechazos
 * (409) se siguen mostrando. No deriva ni asume ninguna fecha: usa la
 * `fecha_objetivo` recibida y bloquea si falta o no es verificable.
 */
export type TargetMaturity =
  | { status: "mature" }
  | { status: "immature"; target: string }
  | { status: "unverifiable" };

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export const TARGET_UNVERIFIABLE_MESSAGE =
  "No se puede revisar este resultado porque no tiene una fecha objetivo verificable.";

export function targetImmatureMessage(target: string): string {
  return `Disponible cuando termine el día objetivo: ${target} (UTC).`;
}

export function utcToday(now: number = Date.now()): string {
  return new Date(now).toISOString().slice(0, 10);
}

function isValidIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function targetMaturity(fechaObjetivo: string | null | undefined, today: string): TargetMaturity {
  if (!fechaObjetivo || !isValidIsoDate(fechaObjetivo)) return { status: "unverifiable" };
  return fechaObjetivo < today ? { status: "mature" } : { status: "immature", target: fechaObjetivo };
}

function msUntilNextUtcMidnight(now: number): number {
  const date = new Date(now);
  const next = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + 1);
  return next - now;
}

/** Día UTC real, actualizado al volver a la pestaña y al cambiar el día
 * mientras la pantalla permanece abierta. Nunca usa un reloj simulado. */
export function useUtcToday(): string {
  const [today, setToday] = useState(() => utcToday());

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;

    function refresh() {
      setToday(utcToday());
    }

    function arm() {
      timer = setTimeout(() => {
        refresh();
        arm();
      }, msUntilNextUtcMidnight(Date.now()) + 250);
    }

    function onVisibilityChange() {
      if (document.visibilityState === "visible") refresh();
    }

    arm();
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      if (timer !== undefined) clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return today;
}
