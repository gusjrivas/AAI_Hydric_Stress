import { HistoricalWalkthrough } from "../producer/HistoricalWalkthrough";
import { RetrospectiveEvidencePanel } from "../evidence/RetrospectiveEvidencePanel";
import "./PergaminoDefensePage.css";

export function PergaminoDefensePage() {
  return <div className="pergamino-defense">
    <header className="defense-header">
      <div className="defense-topbar">
        <span className="defense-brand" aria-label="Cultiv IA">Cultiv <em>IA</em></span>
        <span className="defense-mode">Recorrido histórico</span>
        <nav aria-label="Secciones de la defensa">
          <button type="button" onClick={() => document.getElementById("defense-forecast")?.scrollIntoView()}>Pronóstico y revisión</button>
          <button type="button" onClick={() => document.getElementById("defense-evidence")?.scrollIntoView()}>Evidencia 2023</button>
        </nav>
      </div>
      <div className="defense-hero">
        <p className="producer-eyebrow">AAI Hydric Stress · demostración de defensa</p>
        <h1>Recorrido histórico</h1>
        <p>Pergamino · emisiones persistidas del 13 al 17 de junio de 2023.</p>
        <p className="defense-journey">Procedencia y calidad → pronóstico → acuerdo entre modelos → observación posterior → revisión humana</p>
      </div>
    </header>
    <section id="defense-forecast" aria-label="Pronóstico de una emisión">
      <p className="producer-eyebrow">A · Una emisión seleccionada</p>
      <HistoricalWalkthrough sensorId="pergamino-ensemble-demo" defense />
    </section>
    <section id="defense-evidence" aria-label="Desempeño agregado retrospectivo"><RetrospectiveEvidencePanel /></section>
  </div>;
}
