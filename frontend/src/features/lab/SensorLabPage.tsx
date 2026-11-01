import { useEffect, useId, useState } from "react";
import "./SensorLabPage.css";
import { QualityPanel } from "../quality/QualityPanel";
import { ForecastPage } from "../forecast/ForecastPage";
import { useForecastWorkspace } from "../forecast/useForecastWorkspace";
import { LabStage } from "./LabStage";
import { makeLabSensorId } from "./labSensor";
import { LAB_DEMO_PAUSE_MS, useLabDemoRun } from "./useLabDemoRun";
import { LAB_DRY_DAYS, LAB_SEED, useSensorLabScenarios } from "./useSensorLabScenarios";
import type { LabPhase } from "./useSensorLabScenarios";

const PHASE_LABELS: Record<LabPhase, string> = {
  idle: "Sin iniciar",
  seeding: "Generando historial de prueba (paso A)…",
  normal: "Paso A · Historial de prueba generado",
  "injecting-anomaly": "Enviando la lectura anómala (paso B)…",
  anomaly: "Paso B · Lectura anómala enviada",
  interrupting: "Simulando la interrupción (paso C)…",
  interrupted: "Paso C · Envío del generador suspendido",
  recovering: "Simulando la recuperación (paso D)…",
  recovered: "Paso D · Lecturas de prueba para las fechas pendientes",
  drying: "Generando la sequía simulada (paso E)…",
  drought: "Paso E · Sequía simulada y pronóstico solicitado",
  error: "El paso solicitado no pudo completarse",
};

/** Qué hacer a continuación, según la fase; nunca sugiere acciones fuera de la secuencia A–E. */
const NEXT_ACTION: Record<LabPhase, string> = {
  idle: "Generar el historial de prueba (paso A).",
  seeding: "Esperá: se está generando el historial de prueba.",
  normal: "Introducir una lectura anómala (paso B).",
  "injecting-anomaly": "Esperá: se está enviando la lectura anómala.",
  anomaly: "Simular una interrupción (paso C).",
  interrupting: "Esperá: se está simulando la interrupción.",
  interrupted: "Simular la recuperación (paso D).",
  recovering: "Esperá: se está simulando la recuperación.",
  recovered: "Simular una sequía (paso E).",
  drying: "Esperá: se está generando la sequía simulada.",
  drought: "El recorrido terminó. Podés iniciar una sesión nueva.",
  error: "Iniciar una sesión nueva: los datos de la sesión anterior se conservan.",
};

export const LAB_ERROR_GUIDANCE =
  "Este paso no pudo completarse. Para evitar modificar lecturas ya guardadas, iniciá una sesión nueva. Los datos de la sesión anterior se conservan.";

const STEP_BUSY_NOTE = "Se habilita al completar el paso anterior. Hay un paso en curso: esperá a que termine.";

/** Por qué un paso está deshabilitado, según la fase real; no agrega reglas fuera de la secuencia A–E. */
const DISABLED_STEP_NOTE: Record<LabPhase, string> = {
  idle: "Se habilita al completar el paso anterior. Por ahora solo está disponible el paso A.",
  seeding: STEP_BUSY_NOTE,
  normal: "Se habilita al completar el paso anterior. Por ahora solo está disponible el paso B.",
  "injecting-anomaly": STEP_BUSY_NOTE,
  anomaly: "Se habilita al completar el paso anterior. Por ahora solo está disponible el paso C.",
  interrupting: STEP_BUSY_NOTE,
  interrupted: "Se habilita al completar el paso anterior. Por ahora solo está disponible el paso D.",
  recovering: STEP_BUSY_NOTE,
  recovered: "Se habilita al completar el paso anterior. Por ahora solo está disponible el paso E.",
  drying: STEP_BUSY_NOTE,
  drought: "El recorrido A–E terminó: no quedan pasos pendientes. Iniciá una sesión nueva para repetirlo.",
  error: "El paso anterior no pudo completarse, así que los pasos siguientes no están disponibles. Iniciá una sesión nueva.",
};

function realNowLabel(): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date());
}

/** Fases en las que el sensor de prueba ya tiene lecturas guardadas (el paso A terminó). */
const PHASES_WITH_DATA: readonly LabPhase[] = [
  "normal",
  "injecting-anomaly",
  "anomaly",
  "interrupting",
  "interrupted",
  "recovering",
  "recovered",
  "drying",
  "drought",
];

/** Fases desde las que la demostración automática puede continuar. */
const PHASES_DEMO_CAN_RESUME: readonly LabPhase[] = ["idle", "normal", "anomaly", "interrupted", "recovered"];

export function SensorLabPage({
  onSensorWithData,
  onOpenInTools,
  demoPauseMs = LAB_DEMO_PAUSE_MS,
}: {
  /** Se llama cuando la sesión ya tiene datos, para que el resto de la app conozca el sensor sin copiar su id. */
  onSensorWithData?: (sensorId: string) => void;
  /** Abre el sensor de la sesión en Herramientas técnicas (Resumen e historial). */
  onOpenInTools?: (sensorId: string) => void;
  /** Pausa entre pasos de la demostración automática. */
  demoPauseMs?: number;
} = {}) {
  const disabledNoteId = useId();
  const [sensorId, setSensorId] = useState(() => makeLabSensorId());
  const [qualityRefreshToken, setQualityRefreshToken] = useState(0);
  const workspace = useForecastWorkspace(sensorId);

  const lab = useSensorLabScenarios(sensorId, {
    onIngested: () => setQualityRefreshToken((token) => token + 1),
    runForecast: workspace.runForecast,
  });
  const demo = useLabDemoRun(lab, demoPauseMs);

  const hasData = PHASES_WITH_DATA.includes(lab.phase);
  useEffect(() => {
    if (hasData) onSensorWithData?.(sensorId);
  }, [hasData, sensorId, onSensorWithData]);

  function startNewSession() {
    demo.stop();
    setSensorId(makeLabSensorId());
    setQualityRefreshToken(0);
  }

  const canStartA = lab.phase === "idle";
  const canRunB = lab.phase === "normal";
  const canRunC = lab.phase === "anomaly";
  const canRunD = lab.phase === "interrupted";
  const canRunE = lab.phase === "recovered";
  const canDemo = PHASES_DEMO_CAN_RESUME.includes(lab.phase) && !lab.busy;
  const stepProps = (enabled: boolean) => ({
    className: enabled ? "sl-btn-primary" : "sl-btn-secondary",
    disabled: !enabled || lab.busy,
    "aria-describedby": enabled ? undefined : disabledNoteId,
  });

  return (
    <div className="sensor-lab">
      <p className="sl-badge" role="note">
        SIMULACIÓN · Datos sintéticos · Sin sensor físico conectado
      </p>

      <header className="sl-header">
        <p className="producer-eyebrow">AAI Hydric Stress · demostración técnica</p>
        <h1 id="laboratorio-sensores-heading" tabIndex={-1}>Laboratorio de sensor simulado</h1>
        <p className="sl-journey">
          Este recorrido genera lecturas de prueba para mostrar cómo responde la aplicación ante datos
          normales, un valor anómalo, una interrupción y una sequía. Los días avanzan de forma simulada; no se
          reciben mediciones de un cultivo.
        </p>
      </header>

      <div className="sl-controls" role="group" aria-label="Escenarios del laboratorio">
        <div className="sl-demo-row">
          <button
            type="button"
            className="sl-btn-demo"
            onClick={demo.running ? demo.stop : demo.start}
            disabled={!demo.running && !canDemo}
          >
            {demo.running ? "❚❚ Detener la demostración" : "▶ Ver la demostración"}
          </button>
          <p className="sl-demo-hint">Ejecuta los pasos pendientes, de A a E, con una pausa entre cada uno.</p>
        </div>
        <ol className="sl-steps">
          <li>
            <button type="button" onClick={() => void lab.runScenarioA()} {...stepProps(canStartA)}>
              {lab.phase === "seeding" ? "Generando…" : "A — Generar historial de prueba"}
            </button>
            <p>Carga 120 días sintéticos con lluvias y calor, y solicita un pronóstico.</p>
          </li>
          <li>
            <button type="button" onClick={() => void lab.runScenarioB()} {...stepProps(canRunB)}>
              {lab.phase === "injecting-anomaly" ? "Enviando…" : "B — Introducir una lectura anómala"}
            </button>
            <p>
              Envía una temperatura de 85 °C para comprobar si el control de calidad la señala. Una anomalía
              de medición no equivale a una alerta de estrés hídrico.
            </p>
          </li>
          <li>
            <button type="button" onClick={() => void lab.runScenarioC()} {...stepProps(canRunC)}>
              {lab.phase === "interrupting" ? "Simulando…" : "C — Simular una interrupción"}
            </button>
            <p>
              Avanza cuatro días simulados sin enviar lecturas. Los resultados anteriores siguen visibles,
              pero no describen una situación actualizada. No se desconecta ningún dispositivo físico: se
              suspende el envío del generador.
            </p>
          </li>
          <li>
            <button type="button" onClick={() => void lab.runScenarioD()} {...stepProps(canRunD)}>
              {lab.phase === "recovering" ? "Simulando…" : "D — Simular la recuperación"}
            </button>
            <p>
              Genera y envía lecturas sintéticas para las fechas pendientes y vuelve a solicitar un
              pronóstico. No se recuperan mediciones almacenadas por un dispositivo.
            </p>
          </li>
          <li>
            <button type="button" onClick={() => void lab.runScenarioE()} {...stepProps(canRunE)}>
              {lab.phase === "drying" ? "Simulando…" : "E — Simular una sequía"}
            </button>
            <p>
              Genera {LAB_DRY_DAYS} días secos y calurosos, sin lluvia, y vuelve a solicitar un pronóstico real.
              La humedad del suelo generada baja; si hay una alerta, la decide el predictor operativo.
            </p>
          </li>
        </ol>
        <p id={disabledNoteId} className="sl-disabled-note">
          {DISABLED_STEP_NOTE[lab.phase]}
        </p>
        <button type="button" className="sl-reset sl-btn-secondary" onClick={startNewSession}>
          Iniciar una sesión nueva
        </button>
      </div>

      {lab.error && (
        <div role="alert" className="sl-error">
          <p>{lab.error}</p>
          <p>{LAB_ERROR_GUIDANCE}</p>
        </div>
      )}

      {lab.phase === "interrupted" && (
        <p role="alert" className="sl-stale-banner">
          <strong>
            El generador simulado no envía lecturas desde el {lab.lastQuality?.period_end ?? "última fecha guardada"}.
          </strong>{" "}
          No se muestra "sin alerta" como sustituto de datos faltantes ni se vuelve a pedir un pronóstico sin
          datos nuevos que lo sustenten: los resultados debajo son los últimos obtenidos, fechados, no un
          estado vigente. <strong>Verificar sensor y cultivo.</strong>
        </p>
      )}

      <LabStage phase={lab.phase} readings={lab.readings} forecastRows={workspace.rows} quality={lab.lastQuality} />

      <p className="sl-next" aria-live="polite">
        <strong>Siguiente acción:</strong> {NEXT_ACTION[lab.phase]}
      </p>

      {hasData && onOpenInTools && (
        <p className="sl-open-tools">
          Este sensor ya tiene datos.{" "}
          <button type="button" onClick={() => onOpenInTools(sensorId)}>
            Ver «{sensorId}» en Resumen e historial
          </button>
        </p>
      )}

      <details className="sl-info">
        <summary>Qué simulamos, qué funciona realmente y trazabilidad de esta sesión</summary>

        <p className="sl-disclaimer" role="note">
          El predictor operativo puede entrenarse o actualizarse con las lecturas sintéticas de esta sesión. Sus
          resultados sirven para demostrar el funcionamiento del sistema; no prueban precisión en campo ni
          mejoran la evidencia científica del trabajo. Guardar una revisión humana no inicia por sí solo
          entrenamiento ni recalibración.
        </p>

        <div className="sl-explain">
          <section aria-labelledby="sl-simulated-heading">
            <h2 id="sl-simulated-heading">Qué simulamos</h2>
            <p>
              Las lecturas, las fechas, la interrupción y la sequía se generan para esta demostración. La
              temperatura anómala se introduce deliberadamente.
            </p>
          </section>
          <section aria-labelledby="sl-real-heading">
            <h2 id="sl-real-heading">Qué funciona realmente</h2>
            <p>
              La aplicación recibe y guarda las lecturas de prueba, evalúa su calidad, ejecuta el predictor
              operativo y permite registrar una revisión humana cuando corresponde.
            </p>
          </section>
        </div>

        <section aria-label="Trazabilidad de esta sesión de prueba" className="sl-trace">
          <h2>Trazabilidad de esta sesión de prueba</h2>
          <dl>
            <div>
              <dt>Sensor de prueba (sensor_id)</dt>
              <dd>
                <code>{sensorId}</code>
              </dd>
            </div>
            <div>
              <dt>Semilla del generador</dt>
              <dd>{LAB_SEED}</dd>
            </div>
            <div>
              <dt>Procedencia de las lecturas</dt>
              <dd>sintético</dd>
            </div>
            <div>
              <dt>Reloj local ficticio</dt>
              <dd>{lab.clockDate ?? "Sin iniciar"}</dd>
            </div>
          </dl>
          <p className="sl-unavailable">
            No disponible en este recorrido: commit, SHA-256 del dataset, corridas de MLflow, versión de modelo
            y linaje de recalibración.
          </p>
          <p>
            El reloj es ficticio: organiza los escenarios y no representa fechas de medición reales. Los datos y
            la revisión humana son sintéticos y no aportan evidencia científica.
          </p>
        </section>

        <dl className="sl-identity">
          <div>
            <dt>Hora real del sistema (UTC)</dt>
            <dd>{realNowLabel()}</dd>
          </div>
          <div>
            <dt>Estado del escenario</dt>
            <dd aria-live="polite">{PHASE_LABELS[lab.phase]}</dd>
          </div>
        </dl>
        <p className="sl-clock-note">
          El reloj de esta pantalla organiza los escenarios. No cambia la fecha real del servidor ni
          habilita por sí mismo la revisión de resultados futuros.
        </p>
      </details>

      {lab.log.length > 0 && (
        <section aria-label="Registro del laboratorio" className="sl-log">
          <h2>Registro de esta sesión</h2>
          <ul>
            {lab.log.map((entry) => (
              <li key={entry.id}>
                <strong>{entry.scenario}</strong> · {entry.message}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="sl-quality-heading" className="sl-section">
        <h2 id="sl-quality-heading">Calidad de los datos de prueba</h2>
        <QualityPanel sensorId={sensorId} refreshToken={qualityRefreshToken} />
      </section>

      <section aria-labelledby="sl-forecast-heading" className="sl-section">
        <h2 id="sl-forecast-heading">Pronóstico y revisión humana</h2>
        {workspace.runError && (
          <p role="alert" className="sl-error">
            {workspace.runError}
          </p>
        )}
        <p className="sl-review-note">
          La revisión que registres aquí también forma parte del ejercicio con datos sintéticos. No
          representa una observación independiente de un cultivo real.
        </p>
        <ForecastPage sensorId={sensorId} workspace={workspace} />
      </section>

      <details className="sl-future">
        <summary>¿Cómo se conectaría un sensor real?</summary>
        <p>
          En una siguiente etapa, un sensor físico y un servicio de adquisición reemplazarían al generador de
          esta pantalla. Ese servicio enviaría mediciones identificadas y fechadas a la entrada de datos de la
          aplicación.
        </p>
        <ol>
          <li>Elegir e instalar el sensor y verificar su calibración para el suelo y el cultivo.</li>
          <li>
            Convertir sus mediciones a las unidades y al formato que espera el sistema. Incorporar otras
            fuentes si el sensor no mide todas las variables necesarias.
          </li>
          <li>
            Implementar identificación, autenticación y envío, con manejo de cortes, duplicados y datos que
            llegan tarde.
          </li>
          <li>
            Validar en campo la calidad de los datos y el desempeño de los modelos antes de usar sus
            resultados para apoyar decisiones de riego.
          </li>
        </ol>
        <p>
          Esta demostración verifica el recorrido con datos sintéticos. La conexión física y su validación en
          campo quedan como trabajo futuro.
        </p>
      </details>
    </div>
  );
}
