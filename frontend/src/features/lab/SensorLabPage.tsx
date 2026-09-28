import { useState } from "react";
import "./SensorLabPage.css";
import { QualityPanel } from "../quality/QualityPanel";
import { ForecastPage } from "../forecast/ForecastPage";
import { useForecastWorkspace } from "../forecast/useForecastWorkspace";
import { makeLabSensorId } from "./labSensor";
import { LAB_GAP_DAYS, LAB_HISTORY_DAYS, useSensorLabScenarios } from "./useSensorLabScenarios";
import type { LabPhase } from "./useSensorLabScenarios";

const PHASE_LABELS: Record<LabPhase, string> = {
  idle: "Sin iniciar",
  seeding: "Cargando historial normal (Escenario A)…",
  normal: "Escenario A · Lecturas normales",
  "injecting-anomaly": "Inyectando anomalía de sensado (Escenario B)…",
  anomaly: "Escenario B · Anomalía de sensado",
  interrupting: "Interrumpiendo lecturas (Escenario C)…",
  interrupted: "Escenario C · Interrupción de lecturas",
  recovering: "Recuperando lecturas (Escenario D)…",
  recovered: "Escenario D · Recuperación",
  error: "Error en el paso solicitado",
};

function realNowLabel(): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date());
}

export function SensorLabPage() {
  const [sensorId, setSensorId] = useState(() => makeLabSensorId());
  const [qualityRefreshToken, setQualityRefreshToken] = useState(0);
  const workspace = useForecastWorkspace(sensorId);

  const lab = useSensorLabScenarios(sensorId, {
    onIngested: () => setQualityRefreshToken((token) => token + 1),
    runForecast: workspace.runForecast,
  });

  function resetSession() {
    setSensorId(makeLabSensorId());
    setQualityRefreshToken(0);
  }

  const canStartA = lab.phase === "idle" || lab.phase === "error";
  const canRunB = lab.phase === "normal";
  const canRunC = lab.phase === "anomaly";
  const canRunD = lab.phase === "interrupted";

  return (
    <div className="sensor-lab">
      <p className="sl-badge" role="note">
        Datos sintéticos / sensor de prueba. Demostración técnica.
      </p>

      <header className="sl-header">
        <p className="producer-eyebrow">AAI Hydric Stress · demostración técnica</p>
        <h1>Laboratorio de sensores de prueba</h1>
        <p className="sl-journey">
          Un sensor de laboratorio propio (nunca Pergamino, Melchor Romero ni un dataset científico)
          reproduce, con semilla fija, cuatro escenarios encadenados: lecturas normales, una anomalía
          de sensado, una interrupción de lecturas y su recuperación -- usando los endpoints reales de
          ingesta, calidad, pronóstico y revisión humana de esta misma aplicación.
        </p>
      </header>

      <dl className="sl-identity">
        <div>
          <dt>Sensor demo</dt>
          <dd>
            <code>{sensorId}</code>
          </dd>
        </div>
        <div>
          <dt>Reloj simulado</dt>
          <dd>{lab.clockDate ?? "Sin iniciar"}</dd>
        </div>
        <div>
          <dt>Hora real del sistema (UTC)</dt>
          <dd>{realNowLabel()}</dd>
        </div>
        <div>
          <dt>Estado del escenario</dt>
          <dd aria-live="polite">{PHASE_LABELS[lab.phase]}</dd>
        </div>
      </dl>

      <div className="sl-controls" role="group" aria-label="Escenarios del laboratorio">
        <button type="button" onClick={() => void lab.runScenarioA()} disabled={!canStartA || lab.busy}>
          {lab.phase === "seeding" ? "Cargando…" : `A · Iniciar laboratorio (${LAB_HISTORY_DAYS} días normales)`}
        </button>
        <button type="button" onClick={() => void lab.runScenarioB()} disabled={!canRunB || lab.busy}>
          {lab.phase === "injecting-anomaly" ? "Inyectando…" : "B · Inyectar anomalía de sensado"}
        </button>
        <button type="button" onClick={() => void lab.runScenarioC()} disabled={!canRunC || lab.busy}>
          {lab.phase === "interrupting" ? "Interrumpiendo…" : `C · Interrumpir lecturas (${LAB_GAP_DAYS} días)`}
        </button>
        <button type="button" onClick={() => void lab.runScenarioD()} disabled={!canRunD || lab.busy}>
          {lab.phase === "recovering" ? "Recuperando…" : "D · Reanudar lecturas (recuperación)"}
        </button>
        <button type="button" className="sl-reset" onClick={resetSession}>
          Reiniciar en una sesión nueva
        </button>
      </div>

      {lab.error && (
        <p role="alert" className="sl-error">
          {lab.error}
        </p>
      )}

      {lab.phase === "interrupted" && (
        <p role="alert" className="sl-stale-banner">
          <strong>Sin lecturas nuevas desde el {lab.lastQuality?.period_end ?? "última fecha confirmada"}.</strong>{" "}
          No se muestra "sin alerta" como sustituto de datos faltantes ni se vuelve a pedir un pronóstico sin
          datos nuevos que lo sustenten: los resultados debajo son los últimos obtenidos, fechados, no un
          estado vigente. <strong>Verificar sensor y cultivo.</strong>
        </p>
      )}

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
        <h2 id="sl-quality-heading">Calidad de los datos del sensor de laboratorio</h2>
        <QualityPanel sensorId={sensorId} refreshToken={qualityRefreshToken} />
      </section>

      <section aria-labelledby="sl-forecast-heading" className="sl-section">
        <h2 id="sl-forecast-heading">Pronóstico y revisión humana</h2>
        {workspace.runError && (
          <p role="alert" className="sl-error">
            {workspace.runError}
          </p>
        )}
        <ForecastPage sensorId={sensorId} workspace={workspace} />
      </section>

      <p className="sl-disclaimer">
        Esta demostración usa el mismo pipeline de pronóstico operativo del resto de la aplicación
        (`backend/app/pipeline.py::execute_configured_pipeline`), sobre lecturas sintéticas aisladas de este
        sensor. No entrena otro modelo, no simula un pronóstico ni acredita desempeño predictivo sobre
        sensores físicos reales; una revisión humana registrada acá no dispara entrenamiento ni recalibración.
      </p>
    </div>
  );
}
