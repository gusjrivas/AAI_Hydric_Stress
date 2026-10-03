import { useState } from "react";
import { MelchorEvidenceNote } from "../defense/MelchorEvidenceNote";
import { EvidenceBars } from "./EvidenceBars";
import { RetrospectiveEvidencePanel } from "./RetrospectiveEvidencePanel";
import {
  FORMAL_CONFIGURATIONS,
  FORMAL_EVIDENCE_LIMITATIONS,
  FORMAL_EVIDENCE_SOURCE,
} from "./formalEvidence";
import "./EvidenceResultsPage.css";

type EvidenceTab = "pergamino" | "v3" | "melchor";

const TABS: { id: EvidenceTab; label: string }[] = [
  { id: "pergamino", label: "Pergamino 2023 · pronóstico" },
  { id: "v3", label: "Experimento controlado v3" },
  { id: "melchor", label: "Melchor Romero" },
];

function FormalSummary() {
  const bars = FORMAL_CONFIGURATIONS.map((row) => ({
    key: row.configuracion,
    name: row.configuracion,
    note: `± ${row.f1Desvio.toFixed(3)} entre semillas`,
    value: row.f1Media,
    kind: row.configuracion === "base" ? ("active" as const) : ("plain" as const),
  }));
  return (
    <div className="er-stack">
      <section className="er-card" aria-labelledby="er-v3-summary">
        <p className="er-tier"><span>1</span> Resumen</p>
        <h3 id="er-v3-summary">Experimento controlado v3</h3>
        <ul className="er-list">
          <li>8 configuraciones × 5 semillas, con tag científico congelado. Es un diseño distinto de la evaluación de Pergamino 2023 y de la demo operativa.</li>
          <li>El único efecto consistente es la escasez por recencia; el resto es mixto o casi nulo.</li>
          <li>No hay evidencia cuantitativa de mejora por retroalimentación humana.</li>
        </ul>
      </section>
      <section className="er-card" aria-labelledby="er-v3-compare">
        <p className="er-tier"><span>2</span> Comparación por configuración</p>
        <h3 id="er-v3-compare">F1 medio por configuración</h3>
        <EvidenceBars label="F1 medio por configuración" data={bars} max={1} decimals={3} />
        <p className="er-note">
          Color fuerte: configuración «base». La tabla completa (F1, MCC y AP, con identificadores de
          corrida) está en Herramientas técnicas, <a href="#evidencia">Acerca de esta herramienta</a>.
        </p>
      </section>
      <section className="er-card" aria-labelledby="er-v3-limits">
        <p className="er-tier"><span>3</span> Metodología, procedencia y limitaciones</p>
        <h3 id="er-v3-limits">Qué no permite concluir</h3>
        <ul className="er-list">
          {FORMAL_EVIDENCE_LIMITATIONS.map((item) => <li key={item}>{item}</li>)}
        </ul>
        <p className="er-note">
          Experimento MLflow <code>{FORMAL_EVIDENCE_SOURCE.mlflowExperiment}</code>, tag{" "}
          <code>{FORMAL_EVIDENCE_SOURCE.scientificTag}</code> (commit{" "}
          <code>{FORMAL_EVIDENCE_SOURCE.scientificCommit.slice(0, 10)}…</code>).
        </p>
      </section>
    </div>
  );
}

/**
 * Evidencia por niveles: resumen comprensible, comparación por horizonte,
 * métricas y soporte, detalle técnico y metodología. El estado de gobernanza
 * y las limitaciones exploratorias están siempre visibles; las tablas largas
 * viven en detalles accesibles.
 */
export function EvidenceResultsPage() {
  const [tab, setTab] = useState<EvidenceTab>("pergamino");
  return (
    <div className="evidence-results">
      <header className="er-head">
        <p className="producer-eyebrow">Evidencia</p>
        <h1 id="evidencia-resultados-heading" tabIndex={-1}>Qué se midió y qué se puede afirmar</h1>
        <p className="er-lead">
          Resultados agregados, ordenados de lo más simple a lo más técnico. Ningún resultado de esta
          sección acredita validación agronómica ni preparación productiva.
        </p>
      </header>
      <div className="er-governance" role="note">
        <strong>Estado de gobernanza: evaluación exploratoria no independiente.</strong>{" "}
        La ejecución duplicada incumplió el requisito de corrida única: auditoría científica FAIL. Ese
        estado se distingue del funcionamiento de esta interfaz. No hay un ganador general ni
        probabilidades operativas acreditadas.
      </div>
      <div className="er-tabs" role="tablist" aria-label="Fuente de evidencia">
        {TABS.map((item) => (
          <button
            key={item.id}
            id={`er-tab-${item.id}`}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            aria-controls="er-tabpanel"
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div id="er-tabpanel" role="tabpanel" aria-labelledby={`er-tab-${tab}`}>
        {tab === "pergamino" && <RetrospectiveEvidencePanel />}
        {tab === "v3" && <FormalSummary />}
        {tab === "melchor" && (
          <section className="er-card" aria-labelledby="er-melchor">
            <h3 id="er-melchor">Melchor Romero no tiene evaluación agregada propia</h3>
            <MelchorEvidenceNote />
            <p className="er-note">
              Lo que sí ofrece es un recorrido histórico reproducible desde datos versionados, con la
              distinción entre observaciones e imputaciones.{" "}
              <a href="#defensa-melchor-romero">Ir al seguimiento de Melchor Romero</a>.
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
