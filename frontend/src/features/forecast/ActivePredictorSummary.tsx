import { useEffect, useState } from "react";
import { getActivePredictor } from "./api";
import type { ActivePredictor } from "./api";

type Status = "loading" | "empty" | "error" | "ready";

const ORIGIN_LABEL: Record<string, string> = {
  recalibrado: "Recalibrado (HITL)",
  base_configurado: "Base configurado (Random Forest fijo)",
};

export function ActivePredictorSummary({
  sensorId,
  refreshToken = 0,
}: {
  sensorId: string;
  refreshToken?: number;
}) {
  const requestKey = `${sensorId}:${refreshToken}`;
  const [loadedFor, setLoadedFor] = useState(requestKey);
  const [status, setStatus] = useState<Status>("loading");
  const [predictor, setPredictor] = useState<ActivePredictor | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (requestKey !== loadedFor) {
    setLoadedFor(requestKey);
    setStatus("loading");
    setPredictor(null);
    setError(null);
  }

  useEffect(() => {
    let cancelled = false;
    getActivePredictor(sensorId)
      .then((result) => {
        if (cancelled) return;
        setPredictor(result);
        setStatus(result.origin === null ? "empty" : "ready");
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
      <p role="status" className="fp-predictor-status">
        Cargando predictor activo…
      </p>
    );
  }

  if (status === "empty") {
    return (
      <p role="status" className="fp-predictor-status">
        Todavía no se corrió ningún pronóstico para «{sensorId}» — no hay predictor activo que
        mostrar.
      </p>
    );
  }

  if (status === "error") {
    return (
      <p role="alert" className="fp-predictor-error">
        {error}
      </p>
    );
  }

  const contractSummary = `${predictor!.feature_columns.join(", ")} — lags ${predictor!.lags.join(
    ", ",
  )} — ventanas móviles ${predictor!.rolling_windows.join(", ")} día(s)`;

  return (
    <dl className="fp-predictor-summary">
      <div>
        <dt>Predictor usado</dt>
        <dd>{ORIGIN_LABEL[predictor!.origin ?? ""] ?? predictor!.origin}</dd>
      </div>
      <div>
        <dt>Identificador</dt>
        <dd className="fp-predictor-mono" title={predictor!.model_id ?? undefined}>
          {predictor!.model_id ?? "no disponible"}
          {predictor!.version ? ` (versión ${predictor!.version})` : ""}
        </dd>
      </div>
      <div>
        <dt>Horizonte</dt>
        <dd>{predictor!.horizon_days} día(s)</dd>
      </div>
      <div>
        <dt>Frontera de entrenamiento</dt>
        <dd className="fp-predictor-mono">{predictor!.trained_through ?? "no disponible"}</dd>
      </div>
      <div>
        <dt>Versión de contrato / pipeline</dt>
        <dd className="fp-predictor-mono">
          {predictor!.contract_version} / {predictor!.pipeline_version}
        </dd>
      </div>
      <div className="fp-predictor-contract">
        <dt>Resumen del contrato de variables</dt>
        <dd>{contractSummary}</dd>
      </div>
      <div>
        <dt>Feedback ya aplicado</dt>
        <dd>{predictor!.applied_feedback_count}</dd>
      </div>
    </dl>
  );
}
