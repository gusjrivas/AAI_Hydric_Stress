import { useEffect, useState } from "react";
import "./LineageChain.css";
import { getLineage } from "./api";
import type { LineageEntry } from "./api";

type Status = "loading" | "empty" | "error" | "ready";

function shortId(id: string): string {
  return id.length <= 10 ? id : `${id.slice(0, 8)}…`;
}

export function LineageChain({
  sensorId,
  refreshToken = 0,
}: {
  sensorId: string;
  refreshToken?: number;
}) {
  const requestKey = `${sensorId}:${refreshToken}`;
  const [loadedFor, setLoadedFor] = useState(requestKey);
  const [status, setStatus] = useState<Status>("loading");
  const [chain, setChain] = useState<LineageEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  if (requestKey !== loadedFor) {
    setLoadedFor(requestKey);
    setStatus("loading");
    setChain([]);
    setError(null);
  }

  useEffect(() => {
    let cancelled = false;
    getLineage(sensorId)
      .then((result) => {
        if (cancelled) return;
        setChain(result.chain);
        setStatus(result.chain.length === 0 ? "empty" : "ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError((err as Error).message);
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [sensorId, refreshToken]);

  if (status === "loading") {
    return (
      <p role="status" className="lc-status">
        Reconstruyendo el linaje de recalibraciones…
      </p>
    );
  }

  if (status === "empty") {
    return (
      <p role="status" className="lc-status">
        Este sensor todavía no tiene ninguna recalibración registrada — no hay cadena de linaje
        que mostrar.
      </p>
    );
  }

  if (status === "error") {
    return (
      <p role="alert" className="lc-error">
        Error de integridad de linaje: {error}
      </p>
    );
  }

  return (
    <div className="lc-chain">
      <p className="lc-disclaimer">
        El linaje demuestra <strong>trazabilidad</strong> del ciclo de retroalimentación humana,
        no una mejora automática del desempeño del modelo.
      </p>
      <ol className="lc-list">
        {chain.map((entry) => (
          <li key={entry.recalibration_id} className="lc-entry">
            <div className="lc-nodes">
              <span className="lc-node" title={entry.source_model_id}>
                {shortId(entry.source_model_id)}
              </span>
              <span aria-hidden="true" className="lc-arrow">
                →
              </span>
              <span className="lc-feedback-node">
                feedback ({entry.feedback_references.length})
              </span>
              <span aria-hidden="true" className="lc-arrow">
                →
              </span>
              <span className="lc-node lc-node--successor" title={entry.successor_model_id}>
                {shortId(entry.successor_model_id)}
              </span>
            </div>
            <dl className="lc-meta">
              <div>
                <dt>Versión de linaje</dt>
                <dd>
                  <span className={`lc-version-badge lc-version-badge--v${entry.lineage_version}`}>
                    V{entry.lineage_version}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Recalibrado el</dt>
                <dd>{entry.recalibrated_at}</dd>
              </div>
              <div>
                <dt>SHA-256 del dataset</dt>
                <dd>
                  {entry.dataset_sha256 ? (
                    <>
                      <span aria-hidden="true">{entry.dataset_sha256.slice(0, 10)}…</span>
                      <details className="lc-sha-details">
                        <summary>Ver SHA-256 completo</summary>
                        <code>{entry.dataset_sha256}</code>
                      </details>
                    </>
                  ) : (
                    "no disponible (lineage_version 1)"
                  )}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ol>
    </div>
  );
}
