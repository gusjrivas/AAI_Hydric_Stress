import { useEffect, useState } from "react";

export const ROUTES = ["resumen", "prediccion", "calidad", "linaje", "evidencia"] as const;
export type RouteId = (typeof ROUTES)[number];

export const DEFAULT_ROUTE: RouteId = "resumen";

export const DESTINATION_LABELS: Record<RouteId, string> = {
  resumen: "Resumen",
  prediccion: "Historial y observaciones",
  calidad: "Datos disponibles",
  linaje: "Ajustar próximos pronósticos",
  evidencia: "Acerca de esta herramienta",
};

function parseRoute(hash: string): RouteId {
  const id = hash.replace(/^#/, "");
  return (ROUTES as readonly string[]).includes(id) ? (id as RouteId) : DEFAULT_ROUTE;
}

/**
 * Ruteo por hash entre los cinco destinos (task 2.1 de
 * improve-alerting-ui-decision-workflow). Deliberadamente no se suma un
 * router de terceros: son cinco vistas locales y el navegador ya resuelve
 * Atrás/Adelante sobre cambios de `location.hash`.
 */
export function useHashRoute(): RouteId {
  const [route, setRoute] = useState<RouteId>(() => parseRoute(window.location.hash));

  useEffect(() => {
    function onHashChange() {
      setRoute(parseRoute(window.location.hash));
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return route;
}
