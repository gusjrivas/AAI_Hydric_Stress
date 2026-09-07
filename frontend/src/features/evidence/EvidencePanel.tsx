import "./EvidencePanel.css";
import {
  FORMAL_CONFIGURATIONS,
  FORMAL_EVIDENCE_LIMITATIONS,
  FORMAL_EVIDENCE_SOURCE,
  OPERATIONAL_PREDICTOR_NOTE,
} from "./formalEvidence";

// Panel estático: no hace fetch, no depende del sensor seleccionado, no
// recalcula nada. Contenido congelado, verificado contra el artefacto
// versionado citado en `formalEvidence.ts`.
export function EvidencePanel() {
  return (
    <div className="ep-panel">
      <section className="ep-formal" aria-labelledby="ep-formal-heading">
        <h3 id="ep-formal-heading" className="ep-formal-label">
          {FORMAL_EVIDENCE_SOURCE.label}
        </h3>
        <p className="ep-provenance">
          Fuente: <code>{FORMAL_EVIDENCE_SOURCE.tableFile}</code> — experimento MLflow{" "}
          <code>{FORMAL_EVIDENCE_SOURCE.mlflowExperiment}</code> — tag{" "}
          <code>{FORMAL_EVIDENCE_SOURCE.scientificTag}</code> (commit{" "}
          <code>{FORMAL_EVIDENCE_SOURCE.scientificCommit.slice(0, 10)}…</code>). Ver{" "}
          <code>{FORMAL_EVIDENCE_SOURCE.analysisFile}</code> para la interpretación vigente.
        </p>

        <div className="ep-table-wrap">
          <table className="ep-table">
            <caption className="ep-table-caption">
              8 configuraciones × 5 semillas [0,1,2,3,4] — evidencia congelada, no recalculada
            </caption>
            <thead>
              <tr>
                <th scope="col">Configuración</th>
                <th scope="col">F1 media ± desvío</th>
                <th scope="col">MCC media</th>
                <th scope="col">AP media</th>
              </tr>
            </thead>
            <tbody>
              {FORMAL_CONFIGURATIONS.map((row) => (
                <tr key={row.configuracion}>
                  <th scope="row">{row.configuracion}</th>
                  <td>
                    {row.f1Media.toFixed(4)} ± {row.f1Desvio.toFixed(4)}
                  </td>
                  <td>{row.mccMedia.toFixed(4)}</td>
                  <td>{row.apMedia.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h4 className="ep-subheading">Limitaciones ya documentadas</h4>
        <ul className="ep-limitations">
          {FORMAL_EVIDENCE_LIMITATIONS.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </section>

      <section className="ep-operational" aria-labelledby="ep-operational-heading">
        <h3 id="ep-operational-heading" className="ep-operational-label">
          Predictor operativo vigente
        </h3>
        <p>{OPERATIONAL_PREDICTOR_NOTE}</p>
      </section>
    </div>
  );
}
