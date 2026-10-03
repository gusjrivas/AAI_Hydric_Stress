import type { ReactNode } from "react";
import "./DestinationNav.css";
import { DESTINATION_LABELS, SUMMARY_PAIR, TOOL_NAV_LABELS, TOOL_NAV_ROUTES } from "./useHashRoute";
import type { RouteId } from "./useHashRoute";

/** Destinos de «Herramientas técnicas»: las capacidades que ya existían, sin cambios funcionales. */
export function DestinationNav({
  active,
  routes = TOOL_NAV_ROUTES,
  extra,
}: {
  active: RouteId;
  routes?: readonly RouteId[];
  /** Entradas adicionales (como `<li>`) en la misma barra, p. ej. Demostración y Reproducción histórica. */
  extra?: ReactNode;
}) {
  return (
    <nav className="dn-nav" aria-label="Destinos principales">
      <ul className="dn-list">
        {routes.map((routeId) => (
          <li key={routeId}>
            <a
              href={`#${routeId}`}
              className="dn-link"
              aria-current={active === routeId || (routeId === "resumen" && active === "prediccion") ? "page" : undefined}
            >
              {TOOL_NAV_LABELS[routeId] ?? DESTINATION_LABELS[routeId]}
            </a>
          </li>
        ))}
        {extra}
      </ul>
    </nav>
  );
}

/** Selector interno de «Resumen e historial»: dos vistas del mismo flujo, con sus anclas de siempre. */
export function SummarySwitch({ active }: { active: RouteId }) {
  return (
    <nav className="dn-switch" aria-label="Resumen e historial">
      {SUMMARY_PAIR.map((routeId) => (
        <a key={routeId} href={`#${routeId}`} aria-current={active === routeId ? "page" : undefined}>
          {DESTINATION_LABELS[routeId]}
        </a>
      ))}
    </nav>
  );
}
