import { HistoricalWalkthrough } from "../producer/HistoricalWalkthrough";
import { MelchorEvidenceNote } from "./MelchorEvidenceNote";
import { SiteHeader } from "./SiteHeader";
import "./MelchorRomeroDefensePage.css";

/**
 * Segundo sitio real del recorrido histórico (generaliza la arquitectura
 * ya usada por `PergaminoDefensePage`, sin copiarla cosméticamente): datos
 * reales ya versionados de Melchor Romero (ESA CCI + NASA POWER, 2024),
 * el mismo dataset que es la evidencia congelada de `controlled_daily_v3`
 * -- nunca la misma corrida, nunca el mismo paquete de historical-replay
 * (`replay_packages/base-seed4-1157696b7b-v2`). Cinco emisiones
 * preparadas (2024-10-20 a 2024-10-24), igual que Pergamino tiene cinco
 * (2023-06-13 a 2023-06-17) -- una demostración técnica retrospectiva
 * independiente, no una validación científica confirmatoria ni una
 * réplica de la evidencia de v3.
 */
const MELCHOR_ROMERO_DATES = [
  "2024-10-20",
  "2024-10-21",
  "2024-10-22",
  "2024-10-23",
  "2024-10-24",
];
const MELCHOR_ROMERO_REVEAL_MAX = "2024-10-27";
const MELCHOR_ROMERO_PROVENANCE_NOTICE = (
  <p className="historical-provenance">
    <strong>Origen: Melchor Romero · ESA CCI (humedad de suelo) / NASA POWER (clima).</strong> Es
    el mismo dataset real consolidado que sostiene la evidencia congelada de{" "}
    <code>controlled_daily_v3</code>, reutilizado aquí solo como observaciones/datos de entrada de
    una demostración técnica separada -- nunca la misma corrida ni el mismo paquete de
    reproducción histórica. Hay emisiones del 20 al 24 de octubre de 2024.
  </p>
);

export function MelchorRomeroDefensePage() {
  return <div className="melchor-romero-defense">
    <SiteHeader site="melchor" />
    <section id="defense-forecast-melchor" aria-label="Pronóstico de una emisión">
      <HistoricalWalkthrough
        sensorId="melchor-romero-demo"
        defense
        availableDates={MELCHOR_ROMERO_DATES}
        revealMax={MELCHOR_ROMERO_REVEAL_MAX}
        provenanceNotice={MELCHOR_ROMERO_PROVENANCE_NOTICE}
        sourceSummary={{ label: "Histórico", detail: "ESA CCI (humedad de suelo) / NASA POWER (clima)" }}
      />
    </section>
    <section className="site-evidence-link site-evidence-link--na" aria-label="Evidencia agregada retrospectiva">
      <p>
        <strong>Sin evaluación agregada equivalente.</strong> Melchor Romero no tiene una evaluación
        retrospectiva propia acreditada, y no se le atribuyen los resultados de Pergamino.{" "}
        <a href="#evidencia-resultados">Ver evidencia y sus límites</a>.
      </p>
      <details className="app-technical">
        <summary>Ver el alcance completo de la evidencia de Melchor Romero</summary>
        <MelchorEvidenceNote />
      </details>
    </section>
  </div>;
}
