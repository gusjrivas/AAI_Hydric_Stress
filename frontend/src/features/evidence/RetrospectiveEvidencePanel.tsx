import { useEffect, useState } from "react";
import { EvidenceBars } from "./EvidenceBars";
import type { BarDatum } from "./EvidenceBars";
import "./RetrospectiveEvidencePanel.css";

type Metric = { status: string; value: number | null; reason: string | null };
type Method = {
  n: number; positives: number; prevalence: number; false_alerts: number; missed_positive_days: number;
  precision: Metric; recall: Metric; f1: Metric; mcc: Metric; brier: Metric; average_precision: Metric;
  delta_mcc_vs_persistence: Metric;
};
type Horizon = {
  support: { candidate_emissions: number; common_cases: number; coverage_fraction: number };
  metrics: Record<string, Method>;
  episodes: { methods: Record<string, { detected_episodes: number; evaluable_episodes: number }> };
  uncertainty: Record<string, { status: string; delta_mcc_ci95: [number, number] | null; reason: string | null }>;
};
type Projection = {
  schema_version: string; period: { emissions: string; targets: string };
  source_sha256: Record<string, string>; horizons: Record<string, Horizon>;
};
type State = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: Projection };
const names: Record<string, string> = {
  logistic_regression: "Regresión logística", random_forest: "Random Forest",
  hist_gradient_boosting_classifier: "HistGradientBoosting", average: "Promedio vigente",
  majority: "Mayoría exploratoria", persistence: "Persistencia",
};
const order = ["logistic_regression", "random_forest", "hist_gradient_boosting_classifier", "average", "majority", "persistence"];
const number = (value: number) => value.toFixed(3);
const COMPARISON_ORDER = ["average", "majority", "persistence", "logistic_regression", "random_forest", "hist_gradient_boosting_classifier"];
const METHOD_NOTES: Record<string, { note: string; kind: BarDatum["kind"] }> = {
  average: { note: "Política vigente", kind: "active" },
  majority: { note: "Comparación exploratoria", kind: "plain" },
  persistence: { note: "Referencia sin modelo", kind: "reference" },
  logistic_regression: { note: "Modelo individual", kind: "plain" },
  random_forest: { note: "Modelo individual", kind: "plain" },
  hist_gradient_boosting_classifier: { note: "Modelo individual", kind: "plain" },
};
type MetricKey = "mcc" | "f1" | "recall" | "precision" | "false_alerts" | "missed_positive_days";
const METRIC_OPTIONS: { key: MetricKey; label: string; help: string; max: number | null; decimals: number }[] = [
  { key: "mcc", label: "MCC", help: "Acierto equilibrado entre alertas y no alertas (−1 a 1; más es mejor).", max: 1, decimals: 3 },
  { key: "f1", label: "F1", help: "Equilibrio entre precisión y recall (0 a 1; más es mejor).", max: 1, decimals: 3 },
  { key: "recall", label: "Recall", help: "Días con baja humedad que se detectaron (0 a 1; más es mejor).", max: 1, decimals: 3 },
  { key: "precision", label: "Precisión", help: "De los días con alerta, cuántos tenían baja humedad (0 a 1; más es mejor).", max: 1, decimals: 3 },
  { key: "false_alerts", label: "Falsas alertas", help: "Días con alerta sin baja humedad real (menos es mejor).", max: null, decimals: 0 },
  { key: "missed_positive_days", label: "Omisiones", help: "Días con baja humedad sin alerta (menos es mejor).", max: null, decimals: 0 },
];
function metricValue(method: Method | undefined, key: MetricKey): number | null {
  if (!method) return null;
  if (key === "false_alerts") return method.false_alerts;
  if (key === "missed_positive_days") return method.missed_positive_days;
  const item = method[key];
  return item?.status === "defined" && item.value !== null ? item.value : null;
}
const touchesZero = (ci: [number, number] | null | undefined) => !!ci && ci[0] <= 0 && ci[1] >= 0;
const metric = (value: Metric | undefined) => value?.status === "defined" && value.value !== null
  ? number(value.value) : `No disponible${value?.reason ? `: ${value.reason}` : ""}`;

export function RetrospectiveEvidencePanel() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [retry, setRetry] = useState(0);
  const [hz, setHz] = useState("1");
  const [metricKey, setMetricKey] = useState<MetricKey>("mcc");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${import.meta.env.BASE_URL}retrospective-2023.json`, { signal: controller.signal }).then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json() as Projection;
      if (data.schema_version !== "defense-retrospective-aggregate.v1" || !["1", "2", "3"].every((h) => data.horizons[h])) {
        throw new Error("Esquema de evidencia incompatible");
      }
      setState({ status: "ready", data });
    }).catch((error: Error) => { if (!controller.signal.aborted) setState({ status: "error", message: error.message }); });
    return () => controller.abort();
  }, [retry]);

  return <section className="retrospective-panel" aria-labelledby="retrospective-title">
    <div className="retrospective-heading">
      <div><p className="producer-eyebrow">Pergamino · desempeño agregado</p><h2 id="retrospective-title">Evidencia del pronóstico · 2023</h2></div>
      <span className="retrospective-tag">Evaluación exploratoria no independiente</span>
    </div>
    <p>Resultados agregados de Pergamino 2023. No son predicciones fechadas ni la confianza de la emisión seleccionada. El objetivo es baja humedad según el umbral P20 del protocolo; no es un diagnóstico agronómico validado.</p>
    {state.status === "loading" && <p role="status">Cargando evidencia retrospectiva…</p>}
    {state.status === "error" && <p role="alert">No se pudo abrir la evidencia: {state.message} <button type="button" onClick={() => { setState({ status: "loading" }); setRetry((n) => n + 1); }}>Reintentar</button></p>}
    {state.status === "ready" && <>
      {(() => {
        const horizons = state.data.horizons;
        const average = (h: string) => horizons[h].metrics.average;
        const recalls = ["1", "2", "3"].map((h) => metric(average(h)?.recall)).join(" → ");
        const falseAlerts = ["1", "2", "3"].map((h) => average(h)?.false_alerts).join(", ");
        const allCiTouchZero = ["1", "2", "3"].every((h) => touchesZero(horizons[h].uncertainty.average_minus_majority?.delta_mcc_ci95)
          && touchesZero(horizons[h].uncertainty.average_minus_persistence?.delta_mcc_ci95));
        const selected = METRIC_OPTIONS.find((option) => option.key === metricKey)!;
        const current = horizons[hz];
        const counts = COMPARISON_ORDER.map((name) => metricValue(current.metrics[name], metricKey) ?? 0);
        const scale = selected.max ?? (Math.max(...counts, 1));
        const bars: BarDatum[] = COMPARISON_ORDER.filter((name) => current.metrics[name]).map((name) => ({
          key: name, name: names[name], note: METHOD_NOTES[name].note, kind: METHOD_NOTES[name].kind,
          value: metricValue(current.metrics[name], metricKey),
        }));
        return <>
          <section className="retrospective-tier" aria-labelledby="retro-tier1">
            <p className="retrospective-tier-label"><span>1</span> Resumen</p>
            <h3 id="retro-tier1">Qué muestra la evaluación 2023</h3>
            <ul className="retrospective-takeaways">
              <li>Evaluación sobre {horizons["1"].support.common_cases} emisiones de 2023 en Pergamino: un sitio y un año ya usado en análisis previos.</li>
              <li>El promedio de los tres modelos detecta la mayoría de los días de baja humedad (recall {recalls} en +1, +2 y +3 días), con más falsas alertas a mayor horizonte ({falseAlerts} días).</li>
              {allCiTouchZero
                ? <li>Frente a la mayoría y a la persistencia, las diferencias son pequeñas y sus intervalos incluyen o rozan el cero: no hay un ganador general.</li>
                : <li>Las comparaciones con la mayoría y la persistencia son exploratorias: no hay un ganador general.</li>}
              <li>Los puntajes no son probabilidades calibradas; no se presentan como porcentaje de riesgo.</li>
            </ul>
          </section>
          <section className="retrospective-tier" aria-labelledby="retro-tier2">
            <p className="retrospective-tier-label"><span>2</span> Comparación por horizonte</p>
            <h3 id="retro-tier2">Cómo se comparan los métodos</h3>
            <div className="retrospective-controls">
              <div role="group" aria-label="Horizonte">
                {["1", "2", "3"].map((h) => <button key={h} type="button" aria-pressed={hz === h} onClick={() => setHz(h)}>+{h} día{h === "1" ? "" : "s"}</button>)}
              </div>
              <div role="group" aria-label="Métrica">
                {METRIC_OPTIONS.map((option) => <button key={option.key} type="button" aria-pressed={metricKey === option.key} onClick={() => setMetricKey(option.key)}>{option.label}</button>)}
              </div>
            </div>
            <p className="retrospective-help">{selected.help} Soporte común: {current.support.common_cases} casos. Valores no disponibles se muestran como «n/d», nunca como cero.</p>
            <EvidenceBars label={`${selected.label} por método, horizonte +${hz}`} data={bars} max={scale} decimals={selected.decimals} />
            <p className="retrospective-help">Rayado: referencia sin modelo (persistencia). Color fuerte: política vigente (promedio).</p>
          </section>
          <p className="retrospective-tier-label"><span>3</span> Métricas, soporte y detalle técnico</p>
        </>;
      })()}
      <p>Período: emisiones {state.data.period.emissions}; objetivos {state.data.period.targets}. Mayoría es una comparación exploratoria; la política activa conserva el promedio.</p>
      <div className="retrospective-horizons">{["1", "2", "3"].map((h) => {
        const data = state.data.horizons[h];
        const rows = order.filter((name) => data.metrics[name]);
        const first = data.metrics.average;
        const majority = data.metrics.majority;
        const averageVsMajority = data.uncertainty.average_minus_majority;
        return <article className="retrospective-horizon" key={h}>
          <h4>+{h} día{h === "1" ? "" : "s"}</h4>
          <p>Soporte común {data.support.common_cases}/{data.support.candidate_emissions} · Prevalencia {first ? number(first.prevalence) : "No disponible"}</p>
          <p>Promedio: {first ? `F1 ${metric(first.f1)} · MCC ${metric(first.mcc)} · falsas alertas ${first.false_alerts} · omisiones ${first.missed_positive_days}` : "No disponible"}</p>
          {first?.mcc.value !== null && majority?.mcc.value !== null && first?.mcc.value !== undefined && majority?.mcc.value !== undefined && <p>Promedio − mayoría: ΔMCC {number(first.mcc.value - majority.mcc.value)}; IC95 {averageVsMajority?.status === "defined" && averageVsMajority.delta_mcc_ci95 ? `[${number(averageVsMajority.delta_mcc_ci95[0])}, ${number(averageVsMajority.delta_mcc_ci95[1])}]` : "No disponible"}.</p>}
          <details><summary>Comparar métodos y episodios</summary>
            <div className="retrospective-table" tabIndex={0} role="region" aria-label={`Métricas agregadas horizonte +${h}, tabla desplazable`}>
              <table><thead><tr><th scope="col">Método</th><th scope="col">N</th><th scope="col">Precisión</th><th scope="col">Recall</th><th scope="col">F1</th><th scope="col">MCC</th><th scope="col">Falsas alertas</th><th scope="col">Omisiones</th><th scope="col">Brier</th><th scope="col">AP</th><th scope="col">ΔMCC vs persistencia</th><th scope="col">IC95 ΔMCC</th><th scope="col">Inicios detectados</th></tr></thead>
                <tbody>{rows.map((name) => {
                  const row = data.metrics[name]; const ci = data.uncertainty[`${name}_minus_persistence`];
                  const episode = data.episodes.methods[name];
                  return <tr key={name}><th scope="row">{names[name]}</th><td>{row.n}</td><td>{metric(row.precision)}</td><td>{metric(row.recall)}</td><td>{metric(row.f1)}</td><td>{metric(row.mcc)}</td><td>{row.false_alerts}</td><td>{row.missed_positive_days}</td><td>{metric(row.brier)}</td><td>{metric(row.average_precision)}</td><td>{name === "persistence" ? "Referencia" : metric(row.delta_mcc_vs_persistence)}</td><td>{ci?.status === "defined" && ci.delta_mcc_ci95 ? `[${number(ci.delta_mcc_ci95[0])}, ${number(ci.delta_mcc_ci95[1])}]` : "No disponible"}</td><td>{episode ? `${episode.detected_episodes}/${episode.evaluable_episodes}` : "No disponible"}</td></tr>;
                })}</tbody></table>
            </div>
          </details>
        </article>;
      })}</div>
      <p className="retrospective-tier-label"><span>4</span> Metodología, procedencia y limitaciones</p>
      <details className="retrospective-method" open><summary>Fuentes y límites metodológicos</summary>
        <p>Proyección versionada de <code>ui_summary.json</code> y <code>metrics.json</code> canónicos. SHA-256: {state.data.source_sha256["ui_summary.json"]}; {state.data.source_sha256["metrics.json"]}.</p>
        <p>Véanse <code>docs/research/ensemble-retrospective-evaluation-results.md</code> y <code>docs/research/ensemble-retrospective-evaluation-protocol.md</code>. La ejecución duplicada incumplió el requisito de corrida única: auditoría científica FAIL. Ese estado de gobernanza se distingue del funcionamiento de esta interfaz. No hay un ganador general ni probabilidades operativas acreditadas.</p>
      </details>
    </>}
  </section>;
}
