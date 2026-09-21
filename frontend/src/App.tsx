import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import { ArchitectureFlow } from "./features/architecture-flow/ArchitectureFlow";
import { QualityPanel } from "./features/quality/QualityPanel";
import { ForecastPage } from "./features/forecast/ForecastPage";
import { ActivePredictorSummary } from "./features/forecast/ActivePredictorSummary";
import { RecalibrationPanel } from "./features/forecast/RecalibrationPanel";
import { useForecastWorkspace } from "./features/forecast/useForecastWorkspace";
import { LineageChain } from "./features/lineage/LineageChain";
import { EvidencePanel } from "./features/evidence/EvidencePanel";
import { ResumenView } from "./features/summary/ResumenView";
import { ProducerView } from "./features/producer/ProducerView";
import { DestinationNav } from "./features/navigation/DestinationNav";
import { DESTINATION_LABELS, useHashRoute } from "./features/navigation/useHashRoute";
import { DemoPage } from "./features/demo/DemoPage";
import { useDemoSession } from "./features/demo/useDemoSession";
import { demoGateForSensor } from "./features/demo/lock";

const DEMO_HASH = "#demo";

function useIsDemoRoute(): boolean {
  const [isDemo, setIsDemo] = useState(() => window.location.hash === DEMO_HASH);
  useEffect(() => {
    function onHashChange() {
      setIsDemo(window.location.hash === DEMO_HASH);
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return isDemo;
}

const SENSOR_ID_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;
const INITIAL_SENSOR_ID = "sensor-a";
const APP_TITLE = "Seguimiento del agua en el cultivo";

function App() {
  const [draftSensorId, setDraftSensorId] = useState(INITIAL_SENSOR_ID);
  const [activeSensorId, setActiveSensorId] = useState(INITIAL_SENSOR_ID);
  const [sensorError, setSensorError] = useState<string | null>(null);
  const workspace = useForecastWorkspace(activeSensorId);
  const forecastBusy = workspace.activeMutation !== null;
  const [predictorRefreshToken, setPredictorRefreshToken] = useState(0);
  const [lineageRefreshToken, setLineageRefreshToken] = useState(0);

  const handleRecalibrated = useCallback(() => {
    setPredictorRefreshToken((token) => token + 1);
    setLineageRefreshToken((token) => token + 1);
  }, []);

  const demo = useDemoSession();
  const demoGate = demoGateForSensor(demo.session, activeSensorId);
  const isViewingDemoSensor = demo.session !== null && demo.session.sensor_id === activeSensorId;
  const [demoQualityRefreshToken, setDemoQualityRefreshToken] = useState(0);
  const lastAppliedProgressTokenRef = useRef(0);

  useEffect(() => {
    if (!isViewingDemoSensor) return;
    if (demo.progressToken === lastAppliedProgressTokenRef.current) return;
    lastAppliedProgressTokenRef.current = demo.progressToken;
    void workspace.reloadHistory();
    setDemoQualityRefreshToken((token) => token + 1);
  }, [isViewingDemoSensor, demo.progressToken, workspace]);

  const route = useHashRoute();
  const isDemoRoute = useIsDemoRoute();
  const isFirstRouteRender = useRef(true);

  useEffect(() => {
    document.title = `${APP_TITLE} — ${DESTINATION_LABELS[route]}`;
    if (isFirstRouteRender.current) {
      isFirstRouteRender.current = false;
      return;
    }
    document.getElementById(`${route}-heading`)?.focus();
  }, [route]);

  function applySensor() {
    const candidate = draftSensorId.trim();
    if (!SENSOR_ID_PATTERN.test(candidate)) {
      setSensorError("Ingresá un identificador válido: letras, números, guiones o guiones bajos, hasta 64 caracteres.");
      return;
    }
    setSensorError(null);
    setActiveSensorId(candidate);
  }

  return (
    <div className="app-page">
      <a href="#main-content" className="skip-link">
        Saltar al contenido
      </a>
      <header className="app-sensor-header">
        <h1>Seguimiento del agua en el cultivo</h1>
        <p className="app-intro">Consultá el pronóstico y registrá lo que observaste en el cultivo.</p>
        <p className="app-intro">Herramienta en evaluación. Ayuda a revisar la situación; no indica cuánto ni cuándo regar.</p>
        {route !== "productor" && (
          <>
            <form
              className="app-sensor-form"
              onSubmit={(event) => {
                event.preventDefault();
                applySensor();
              }}
            >
              <label htmlFor="sensor-draft-input">Punto de medición (sensor)</label>
              <input
                id="sensor-draft-input"
                value={draftSensorId}
                onChange={(event) => setDraftSensorId(event.target.value)}
                aria-invalid={sensorError ? true : undefined}
                aria-describedby={sensorError ? "sensor-error" : undefined}
              />
              <button type="submit" disabled={forecastBusy}>
                Aplicar
              </button>
            </form>
            <p className="app-sensor-active" aria-live="polite">
              Sensor activo: <strong>{activeSensorId}</strong>
            </p>
            {sensorError && (
              <p id="sensor-error" role="alert" className="app-sensor-error">
                {sensorError}
              </p>
            )}
          </>
        )}
      </header>

      <DestinationNav active={route} />
      {demo.configured && (
        <p className="app-demo-link">
          <a href={DEMO_HASH} aria-current={isDemoRoute ? "page" : undefined}>
            Demostración
          </a>
        </p>
      )}

      <main id="main-content" className="app-sections" tabIndex={-1}>
        {isDemoRoute && (
          <section aria-labelledby="demo-heading">
            <h2 id="demo-heading" className="app-section-heading" tabIndex={-1}>
              Demostración
            </h2>
            <DemoPage demo={demo} />
          </section>
        )}

        {!isDemoRoute && route === "resumen" && (
          <section aria-labelledby="resumen-heading">
            <h2 id="resumen-heading" className="app-section-heading" tabIndex={-1}>
              Resumen
            </h2>
            <ResumenView
              sensorId={activeSensorId}
              workspace={workspace}
              demoGate={demoGate}
              refreshToken={demoQualityRefreshToken}
            />
          </section>
        )}

        {!isDemoRoute && route === "productor" && (
          <section aria-labelledby="productor-heading">
            <h2 id="productor-heading" className="app-section-heading" tabIndex={-1}>
              Mi cultivo
            </h2>
            <ProducerView />
          </section>
        )}

        {!isDemoRoute && route === "prediccion" && (
          <section aria-labelledby="prediccion-heading">
            <h2 id="prediccion-heading" className="app-section-heading" tabIndex={-1}>
              Historial y observaciones
            </h2>
            <ForecastPage sensorId={activeSensorId} workspace={workspace} demoGate={demoGate} />
          </section>
        )}

        {!isDemoRoute && route === "calidad" && (
          <section aria-labelledby="calidad-heading">
            <h2 id="calidad-heading" className="app-section-heading" tabIndex={-1}>
              Datos disponibles
            </h2>
            <QualityPanel sensorId={activeSensorId} refreshToken={demoQualityRefreshToken} />
          </section>
        )}

        {!isDemoRoute && route === "linaje" && (
          <section aria-labelledby="linaje-heading">
            <h2 id="linaje-heading" className="app-section-heading" tabIndex={-1}>
              Ajustar próximos pronósticos
            </h2>
            <RecalibrationPanel
              sensorId={activeSensorId}
              workspace={workspace}
              refreshToken={predictorRefreshToken}
              onRecalibrated={handleRecalibrated}
              demoGate={demoGate}
            />
            <details className="app-technical">
              <summary>Información técnica de los ajustes</summary>
              <ActivePredictorSummary sensorId={activeSensorId} refreshToken={predictorRefreshToken} />
              <LineageChain sensorId={activeSensorId} refreshToken={lineageRefreshToken} />
            </details>
          </section>
        )}

        {!isDemoRoute && route === "evidencia" && (
          <section aria-labelledby="evidencia-heading">
            <h2 id="evidencia-heading" className="app-section-heading" tabIndex={-1}>
              Acerca de esta herramienta
            </h2>
            <p>Esta herramienta usa las mediciones disponibles para estimar si puede haber una alerta en una fecha posterior. Podés consultar los resultados guardados y registrar si coinciden con lo observado.</p>
            <p>Fue desarrollada como parte de un trabajo de investigación. Sus resultados no garantizan el estado del cultivo ni reemplazan la revisión en el lugar.</p>
            <details className="app-technical">
              <summary>Ver el estudio y la documentación técnica</summary>
              <ArchitectureFlow />
              <EvidencePanel />
            </details>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
