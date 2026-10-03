import "./DestinationNav.css";
import { DESTINATION_LABELS, TOOL_ROUTES } from "./useHashRoute";
import type { RouteId } from "./useHashRoute";

/** Destinos de «Herramientas técnicas»: las capacidades que ya existían, sin cambios funcionales. */
export function DestinationNav({ active, routes = TOOL_ROUTES }: { active: RouteId; routes?: readonly RouteId[] }) {
  return (
    <nav className="dn-nav" aria-label="Destinos principales">
      <ul className="dn-list">
        {routes.map((routeId) => (
          <li key={routeId}>
            <a
              href={`#${routeId}`}
              className="dn-link"
              aria-current={active === routeId ? "page" : undefined}
            >
              {DESTINATION_LABELS[routeId]}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
