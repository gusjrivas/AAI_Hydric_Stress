import { HistoricalWalkthrough } from "../producer/HistoricalWalkthrough";
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
    <header className="defense-header">
      <div className="defense-topbar">
        <span className="defense-brand" aria-label="Cultiv IA">Cultiv <em>IA</em></span>
        <span className="defense-mode">Recorrido histórico</span>
        <nav aria-label="Secciones de la defensa">
          <button type="button" onClick={() => document.getElementById("defense-forecast-melchor")?.scrollIntoView()}>Pronóstico y revisión</button>
        </nav>
      </div>
      <div className="defense-hero">
        <p className="producer-eyebrow">AAI Hydric Stress · demostración de defensa</p>
        <h1>Recorrido histórico</h1>
        <p>Melchor Romero · emisiones persistidas del 20 al 24 de octubre de 2024.</p>
        <p className="defense-journey">Primero revisá de dónde vienen los datos. Elegí una emisión, mirá la decisión para +1, +2 y +3 días, y avanzá el reloj para contrastarla con lo observado y registrar tu revisión.</p>
      </div>
    </header>
    <section id="defense-forecast-melchor" aria-label="Pronóstico de una emisión">
      <p className="producer-eyebrow">A · Una emisión seleccionada</p>
      <HistoricalWalkthrough
        sensorId="melchor-romero-demo"
        defense
        availableDates={MELCHOR_ROMERO_DATES}
        revealMax={MELCHOR_ROMERO_REVEAL_MAX}
        provenanceNotice={MELCHOR_ROMERO_PROVENANCE_NOTICE}
      />
    </section>
    <section aria-label="Evidencia agregada retrospectiva">
      <p className="producer-eyebrow">B · Evidencia agregada</p>
      <p className="historical-evidence-unavailable">
        No hay un panel de evidencia agregada retrospectiva para Melchor Romero: a diferencia de
        Pergamino (protocolo <code>controlled_daily_v4_external_pergamino</code>, evaluación
        agregada 2023 ya ejecutada), no existe una corrida de evaluación retrospectiva agregada
        para este sitio en este repositorio. Mostrarla equivaldría a fabricar paridad donde no hay
        evidencia real. Esta demostración solo cubre las cinco emisiones individuales de arriba.
      </p>
    </section>
  </div>;
}
