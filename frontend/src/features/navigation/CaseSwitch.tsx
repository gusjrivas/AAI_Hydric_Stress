import "./CaseSwitch.css";
import type { RouteId } from "./useHashRoute";

interface DemoCase {
  route: RouteId;
  label: string;
  blurb: string;
}

/** Los tres casos de demostración de la defensa, con una línea que dice qué es cada uno. */
const CASES: readonly DemoCase[] = [
  {
    route: "defensa-pergamino",
    label: "Pergamino",
    blurb: "Datos reales · histórico — recorrido día a día con modelo de ensamble y procedencia externa explícita.",
  },
  {
    route: "defensa-melchor-romero",
    label: "Melchor Romero",
    blurb: "Datos reales · reproducible — el mismo recorrido, reproducible desde el propio repositorio.",
  },
  {
    route: "laboratorio-sensores",
    label: "Laboratorio de sensores",
    blurb: "Sintético · sensores de prueba — ruido y fallas de sensor contra el pipeline real; no es evidencia científica.",
  },
];

/** Selector de caso: se muestra solo en las vistas de «Caso de demostración». */
export function CaseSwitch({ route }: { route: RouteId }) {
  const active = CASES.find((item) => item.route === route);
  if (!active) return null;
  return (
    <div className="case-switch-wrap">
      <nav className="case-switch" aria-label="Caso de demostración">
        {CASES.map((item) => (
          <a key={item.route} href={`#${item.route}`} aria-current={item.route === route ? "page" : undefined}>
            {item.label}
          </a>
        ))}
      </nav>
      <p className="case-blurb">{active.blurb}</p>
    </div>
  );
}
