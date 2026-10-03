/**
 * Nota sobre la evidencia agregada de Melchor Romero. Se usa en su pantalla de
 * seguimiento (dentro de un detalle accesible) y en la vista de Evidencia: el
 * texto completo se conserva, no se resume ni se suaviza.
 */
export function MelchorEvidenceNote() {
  return (
    <div className="melchor-evidence-note">
      <p className="historical-evidence-unavailable">
        Estas cinco emisiones demostrativas de Melchor Romero (las ajustadas para esta
        demostración, sección A de arriba) no tienen una evaluación agregada propia acreditada en
        esta entrega: no se ejecutó ninguna corrida de evaluación retrospectiva agregada sobre
        ellas. Esto es distinto de la evidencia histórica congelada de <code>controlled_daily_v3</code> (
        <code>scientific-baseline-v3</code>), que sí existe sobre este mismo sitio y dataset, con su
        propio alcance, y que estas cinco emisiones nunca reejecutan, reinterpretan ni sustituyen.
      </p>
      <p className="historical-evidence-unavailable">
        Pergamino sí muestra un panel de evidencia agregada 2023 en su propia pantalla de defensa
        (<code>/defensa-pergamino</code>, no en esta), pero corresponde a un
        protocolo propio y separado -- la evaluación retrospectiva exploratoria del ensamble
        Pergamino 2023 (<code>docs/research/ensemble-retrospective-evaluation-protocol.md</code> /{" "}
        <code>-results.md</code>) -- no a la campaña científica{" "}
        <code>controlled_daily_v4_external_pergamino</code> (ADR-0011, etapas A, B y C, con holdout
        en la etapa C). Esa evaluación 2023 es exploratoria, no independiente (2023 ya se usó en
        análisis anteriores del proyecto), y su auditoría científica concluyó FAIL por ejecución
        duplicada; no se le atribuye aquí ningún resultado confirmatorio ni superioridad. Mostrar un
        panel equivalente para Melchor Romero equivaldría a fabricar paridad donde no hay evidencia
        real.
      </p>
    </div>
  );
}
