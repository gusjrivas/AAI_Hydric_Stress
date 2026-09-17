import "./DestinationNav.css";
import { DESTINATION_LABELS, ROUTES } from "./useHashRoute";
import type { RouteId } from "./useHashRoute";

export function DestinationNav({ active }: { active: RouteId }) {
  return (
    <nav className="dn-nav" aria-label="Destinos principales">
      <ul className="dn-list">
        {ROUTES.map((routeId) => (
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
