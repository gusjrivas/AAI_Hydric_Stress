import { HistoricalWalkthrough } from "../producer/HistoricalWalkthrough";
import { SiteHeader } from "./SiteHeader";
import "./PergaminoDefensePage.css";

export function PergaminoDefensePage() {
  return <div className="pergamino-defense">
    <SiteHeader site="pergamino" />
    <section id="defense-forecast" aria-label="Pronóstico de una emisión">
      <HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />
    </section>
    <section id="defense-evidence" className="site-evidence-link" aria-label="Evidencia de este método">
      <p>
        <strong>Evidencia de este método.</strong> Hay una evaluación agregada de Pergamino 2023,
        exploratoria y no independiente (auditoría de gobernanza: FAIL por ejecución duplicada).{" "}
        <a href="#evidencia-resultados">Ver evidencia y sus límites</a>.
      </p>
    </section>
  </div>;
}
