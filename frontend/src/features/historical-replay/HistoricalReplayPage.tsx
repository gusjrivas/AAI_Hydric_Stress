import { useEffect, useRef, useState } from "react";
import "./HistoricalReplayPage.css";
import {
  ReplayNotFoundError,
  ReplayNotYetRevealedError,
  createFeedback,
  getCandidate,
  getFeedback,
  getHistory,
  getPrediction,
  listOrigins,
  type EstadoValidacion,
  type ReplayCandidateInfo,
  type ReplayFeedbackEntry,
  type ReplayHistoryRow,
  type ReplayPredictionResponse,
} from "./api";
import { addDaysIso, clampIso, compareIso } from "./dateUtils";
import { classLabel } from "./labelRule";
import { MoistureHistoryChart } from "./MoistureHistoryChart";
import { ReplayCaseControls } from "./ReplayCaseControls";
import { ReplayComparisonCard } from "./ReplayComparisonCard";
import { ReplayEvidenceCard } from "./ReplayEvidenceCard";
import { ReplayFeedbackForm } from "./ReplayFeedbackForm";
import { ReplayPredictionSummary } from "./ReplayPredictionSummary";
import { taggedFor, visibleFor, type ForSelection } from "./selectionScope";

type PageStatus = "loading" | "unavailable" | "error" | "ready";

type PredictionState =
  | { status: "loading" }
  | { status: "hidden-before-origin" }
  | { status: "unknown-origin" }
  | { status: "error"; message: string }
  | { status: "ready"; data: ReplayPredictionResponse };

type HistoryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; rows: ReplayHistoryRow[] };

type FeedbackState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; entries: ReplayFeedbackEntry[] };

const LOADING_PREDICTION: PredictionState = { status: "loading" };
const LOADING_HISTORY: HistoryState = { status: "loading" };
const LOADING_FEEDBACK: FeedbackState = { status: "loading" };

/**
 * Pantalla central "Explorar una predicción" (entrega "recorrido guiado":
 * datos disponibles → predicción archivada → revelación → explicación).
 * Consume exclusivamente las respuestas ya filtradas del backend — nunca
 * descarga el paquete completo ni el dataset entero, y nunca oculta el
 * futuro solo con CSS/JS: lo que no llega del backend, no se dibuja.
 *
 * Aislamiento de estado: cada resultado (predicción, historial, feedback)
 * se guarda etiquetado con el `(origen, fecha simulada)` para el que se
 * pidió (`selectionScope.ts`, `taggedFor`). En el render, `visibleFor`
 * decide si ese resultado corresponde a la selección vigente — si no, se
 * usa el estado `loading` en su lugar. Esta garantía es una comparación
 * pura hecha en cada render a partir del estado ya comprometido, no
 * depende de que ningún `useEffect` haya corrido todavía: cambiar de caso
 * descarta visualmente el resultado anterior de inmediato, sin esperar a
 * que termine ninguna solicitud en vuelo.
 *
 * Un contador de generación (`generationRef`) resuelve además la carrera
 * asincrónica entre promesas para el mismo `(origen, fecha)` (p. ej.
 * A→B→A): solo la promesa iniciada en la generación todavía vigente puede
 * escribir estado al resolver.
 */
export function HistoricalReplayPage() {
  const [pageStatus, setPageStatus] = useState<PageStatus>("loading");
  const [pageError, setPageError] = useState<string | null>(null);
  const [candidate, setCandidate] = useState<ReplayCandidateInfo | null>(null);
  const [origins, setOrigins] = useState<string[]>([]);
  const [selectedOrigin, setSelectedOrigin] = useState<string>("");
  const [simulatedDate, setSimulatedDate] = useState<string>("");

  const [predictionState, setPredictionState] = useState<ForSelection<PredictionState>>(
    taggedFor("", "", LOADING_PREDICTION),
  );
  const [historyState, setHistoryState] = useState<ForSelection<HistoryState>>(
    taggedFor("", "", LOADING_HISTORY),
  );
  const [feedbackState, setFeedbackState] = useState<ForSelection<FeedbackState>>(
    taggedFor("", "", LOADING_FEEDBACK),
  );

  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackSubmitError, setFeedbackSubmitError] = useState<string | null>(null);

  const generationRef = useRef(0);
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getCandidate(), listOrigins()])
      .then(([candidateInfo, originsResponse]) => {
        if (cancelled) return;
        const sortedOrigins = originsResponse.origins
          .map((o) => o.timestamp_origen)
          .sort(compareIso);
        setCandidate(candidateInfo);
        setOrigins(sortedOrigins);
        setSelectedOrigin(sortedOrigins[0] ?? "");
        setSimulatedDate(sortedOrigins[0] ?? candidateInfo.periodo_inicio);
        setPageStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        if (error instanceof ReplayNotFoundError) {
          setPageStatus("unavailable");
        } else {
          setPageError((error as Error).message);
          setPageStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedOrigin || !simulatedDate) return;
    const myGeneration = ++generationRef.current;
    const origin = selectedOrigin;
    const clock = simulatedDate;
    const stillCurrent = () => mountedRef.current && generationRef.current === myGeneration;

    setPredictionState(taggedFor(origin, clock, LOADING_PREDICTION));
    setHistoryState(taggedFor(origin, clock, LOADING_HISTORY));
    setFeedbackState(taggedFor(origin, clock, LOADING_FEEDBACK));
    setFeedbackSubmitError(null);
    setFeedbackSubmitting(false);

    getPrediction(origin, clock)
      .then((result) => {
        if (!stillCurrent()) return;
        setPredictionState(taggedFor(origin, clock, { status: "ready", data: result }));
      })
      .catch((error) => {
        if (!stillCurrent()) return;
        if (error instanceof ReplayNotFoundError) {
          setPredictionState(
            taggedFor(origin, clock, {
              status: compareIso(clock, origin) < 0 ? "hidden-before-origin" : "unknown-origin",
            }),
          );
        } else {
          setPredictionState(
            taggedFor(origin, clock, { status: "error", message: (error as Error).message }),
          );
        }
      });

    getHistory(clock)
      .then((result) => {
        if (!stillCurrent()) return;
        setHistoryState(taggedFor(origin, clock, { status: "ready", rows: result.rows }));
      })
      .catch((error) => {
        if (!stillCurrent()) return;
        setHistoryState(
          taggedFor(origin, clock, { status: "error", message: (error as Error).message }),
        );
      });

    getFeedback(origin, clock)
      .then((result) => {
        if (!stillCurrent()) return;
        setFeedbackState(taggedFor(origin, clock, { status: "ready", entries: result.feedback }));
      })
      .catch((error) => {
        if (!stillCurrent()) return;
        setFeedbackState(
          taggedFor(origin, clock, { status: "error", message: (error as Error).message }),
        );
      });
  }, [selectedOrigin, simulatedDate]);

  function moveClock(days: number) {
    if (!candidate) return;
    setSimulatedDate((current) =>
      clampIso(addDaysIso(current, days), candidate.periodo_inicio, candidate.periodo_fin),
    );
  }

  // "Volver al inicio de este caso" (Paso "recorrido guiado" §B): conserva
  // el origen seleccionado, solo reubica el reloj en él. A diferencia del
  // "Reiniciar" anterior, nunca cambia de caso.
  function resetToCaseStart() {
    if (!selectedOrigin) return;
    setSimulatedDate(selectedOrigin);
  }

  // Cambiar de origen sitúa también el reloj en ese origen y oculta de
  // inmediato cualquier resultado posterior (Paso "recorrido guiado" §B) —
  // ya no son selecciones independientes.
  function selectOrigin(origin: string) {
    setSelectedOrigin(origin);
    setSimulatedDate(origin);
  }

  function revealTarget(targetDate: string) {
    if (!candidate) return;
    setSimulatedDate(clampIso(targetDate, candidate.periodo_inicio, candidate.periodo_fin));
  }

  function handleFeedbackSubmit(input: {
    estado_validacion: EstadoValidacion;
    etiqueta_corregida?: 0 | 1 | null;
    observacion?: string | null;
  }) {
    const origin = selectedOrigin;
    const clock = simulatedDate;
    const myGeneration = generationRef.current;
    const stillCurrent = () => mountedRef.current && generationRef.current === myGeneration;

    setFeedbackSubmitting(true);
    setFeedbackSubmitError(null);
    createFeedback(origin, { simulated_date: clock, ...input })
      .then((entry) => {
        if (!stillCurrent()) return;
        setFeedbackState(taggedFor(origin, clock, { status: "ready", entries: [entry] }));
      })
      .catch((error) => {
        if (!stillCurrent()) return;
        if (error instanceof ReplayNotYetRevealedError) {
          setFeedbackSubmitError("La observación todavía no fue revelada en esta fecha simulada.");
        } else {
          setFeedbackSubmitError((error as Error).message);
        }
      })
      .finally(() => {
        if (stillCurrent()) setFeedbackSubmitting(false);
      });
  }

  if (pageStatus === "loading") {
    return (
      <p role="status" className="hr-status">
        Cargando la reproducción histórica…
      </p>
    );
  }

  if (pageStatus === "unavailable") {
    return (
      <p role="status" className="hr-status">
        La reproducción histórica no está habilitada en este backend.
      </p>
    );
  }

  if (pageStatus === "error" || !candidate) {
    return (
      <p role="alert" className="hr-error">
        No se pudo cargar la reproducción histórica: {pageError}
      </p>
    );
  }

  const predictionVisible = visibleFor(predictionState, selectedOrigin, simulatedDate, LOADING_PREDICTION);
  const historyVisible = visibleFor(historyState, selectedOrigin, simulatedDate, LOADING_HISTORY);
  const feedbackVisible = visibleFor(feedbackState, selectedOrigin, simulatedDate, LOADING_FEEDBACK);

  const prediction = predictionVisible.status === "ready" ? predictionVisible.data : null;
  // El formulario solo se habilita cuando la observación fue efectivamente
  // revelada (target_observed === true) — no simplemente cuando el estado
  // ya no es undefined, lo que también incluiría target_observed === false
  // (objetivo que nunca maduró en este run).
  const revealed = prediction?.target_observed === true;

  // La fecha objetivo se deriva del origen y del horizonte fijo del
  // candidato (RH-11: la diferencia siempre coincide con `horizon_days`),
  // así que puede mostrarse desde el primer render, sin esperar a que
  // cargue la predicción — y coincide exactamente con `target_timestamp`
  // una vez que la predicción llega.
  const targetDate = prediction?.target_timestamp ?? addDaysIso(selectedOrigin, candidate.horizon_days);

  return (
    <div className="hr-page">
      <p className="hr-badge" role="note">
        Reproducción histórica retrospectiva — no son emisiones de un sistema en producción.
      </p>
      <p className="hr-intro">
        Elegí una fecha, consultá qué anticipó el modelo y avanzá para comparar con lo que ocurrió.
      </p>
      <p className="hr-disclaimer">
        Alerta basada en un umbral estadístico de humedad, sin diagnóstico agronómico validado.
      </p>

      <ReplayEvidenceCard candidate={candidate} />

      <ReplayCaseControls
        origins={origins}
        selectedOrigin={selectedOrigin}
        simulatedDate={simulatedDate}
        targetDate={targetDate}
        minDate={candidate.periodo_inicio}
        maxDate={candidate.periodo_fin}
        onSelectOrigin={selectOrigin}
        onMoveClock={moveClock}
        onResetToCaseStart={resetToCaseStart}
        onRevealTarget={() => revealTarget(targetDate)}
      />

      <section aria-label="Historial de humedad integrado" className="hr-history">
        <h3>Historial de humedad</h3>
        {historyVisible.status === "loading" && <p role="status">Cargando historial…</p>}
        {historyVisible.status === "error" && (
          <p role="alert" className="hr-error">
            Error al consultar el historial: {historyVisible.message}
          </p>
        )}
        {historyVisible.status === "ready" && (
          <MoistureHistoryChart
            key={selectedOrigin}
            rows={historyVisible.rows}
            originDate={selectedOrigin}
            targetDate={targetDate}
            simulatedDate={simulatedDate}
            threshold={{
              value: candidate.regla_etiqueta.umbral,
              unit: candidate.regla_etiqueta.unidad,
              variable: candidate.regla_etiqueta.variable,
            }}
            predictedClass={
              prediction
                ? { value: prediction.y_pred as 0 | 1, label: classLabel(prediction.y_pred as 0 | 1, candidate.regla_etiqueta) }
                : null
            }
          />
        )}
      </section>

      <section aria-label="Predicción archivada" className="hr-prediction">
        <h3>Predicción archivada (+{candidate.horizon_days} días)</h3>
        {predictionVisible.status === "loading" && <p role="status">Cargando predicción…</p>}
        {predictionVisible.status === "hidden-before-origin" && (
          <p role="status" className="hr-status">
            La fecha simulada es anterior al origen de esta predicción: todavía no fue "emitida".
          </p>
        )}
        {predictionVisible.status === "unknown-origin" && (
          <p role="alert" className="hr-error">
            Predicción no disponible: no hay ninguna predicción archivada para este origen.
          </p>
        )}
        {predictionVisible.status === "error" && (
          <p role="alert" className="hr-error">
            Error al consultar la predicción: {predictionVisible.message}
          </p>
        )}
        {prediction && (
          <ReplayPredictionSummary
            targetDate={prediction.target_timestamp}
            horizonDays={candidate.horizon_days}
            yPred={prediction.y_pred as 0 | 1}
            rule={candidate.regla_etiqueta}
          />
        )}
      </section>

      {prediction && (
        <section aria-label="Resultado" className="hr-result">
          <h3>Resultado</h3>
          {prediction.target_observed === undefined && (
            <p role="status" className="hr-status">
              Resultado todavía oculto: la fecha simulada todavía no alcanzó el objetivo. Usá "Ver
              qué ocurrió el {targetDate}" para revelarlo.
            </p>
          )}
          {prediction.target_observed === false && (
            <p role="status" className="hr-status">
              Observación no disponible: el objetivo no maduró en este run (no se interpreta como
              "sin alerta").
            </p>
          )}
          {prediction.target_observed === true && (
            <ReplayComparisonCard
              yPred={prediction.y_pred as 0 | 1}
              yTrue={prediction.y_true as 0 | 1}
              rule={candidate.regla_etiqueta}
              medicionOriginal={prediction.medicion_original ?? null}
            />
          )}
        </section>
      )}

      {revealed && (
        <section aria-label="Feedback de demostración" className="hr-feedback-section">
          <h3>Feedback de demostración</h3>
          <p className="hr-status">
            El pronóstico original se conserva tal cual: registrar una observación no cambia
            automáticamente las predicciones futuras.
          </p>
          {feedbackVisible.status === "loading" && <p role="status">Cargando feedback…</p>}
          {feedbackVisible.status === "error" && (
            <p role="alert" className="hr-error">
              No se pudo consultar el feedback existente: {feedbackVisible.message}. No se habilita
              un nuevo registro hasta poder confirmar que no existe uno previo.
            </p>
          )}
          {feedbackVisible.status === "ready" && (
            <ReplayFeedbackForm
              key={`${selectedOrigin}|${simulatedDate}`}
              existing={feedbackVisible.entries}
              submitting={feedbackSubmitting}
              error={feedbackSubmitError}
              labelRule={candidate.regla_etiqueta}
              onSubmit={handleFeedbackSubmit}
            />
          )}
        </section>
      )}
    </div>
  );
}
