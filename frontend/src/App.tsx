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
import { DestinationNav } from "./features/navigation/DestinationNav";
import { DESTINATION_LABELS, useHashRoute } from "./features/navigation/useHashRoute";

const SENSOR_ID_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;
const INITIAL_SENSOR_ID = "sensor-a";
const APP_TITLE = "Demo AAI Hydric Stress";

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

  const route = useHashRoute();
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
      <header className="app-sensor-header">
        <form
          className="app-sensor-form"
          onSubmit={(event) => {
            event.preventDefault();
            applySensor();
          }}
        >
          <label htmlFor="sensor-draft-input">Sensor</label>
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
      </header>

      <DestinationNav active={route} />

      <main className="app-sections">
        {route === "resumen" && (
          <section aria-labelledby="resumen-heading">
            <h2 id="resumen-heading" className="app-section-heading" tabIndex={-1}>
              Resumen
            </h2>
            <ResumenView sensorId={activeSensorId} workspace={workspace} />
          </section>
        )}

        {route === "prediccion" && (
          <section aria-labelledby="prediccion-heading">
            <h2 id="prediccion-heading" className="app-section-heading" tabIndex={-1}>
              Alertas y revisión
            </h2>
            <ForecastPage sensorId={activeSensorId} workspace={workspace} />
          </section>
        )}

        {route === "calidad" && (
          <section aria-labelledby="calidad-heading">
            <h2 id="calidad-heading" className="app-section-heading" tabIndex={-1}>
              Calidad de datos
            </h2>
            <QualityPanel sensorId={activeSensorId} />
          </section>
        )}

        {route === "linaje" && (
          <section aria-labelledby="linaje-heading">
            <h2 id="linaje-heading" className="app-section-heading" tabIndex={-1}>
              Modelo y trazabilidad
            </h2>
            <section aria-label="Predictor activo">
              <h3 className="app-subsection-heading">Predictor activo</h3>
              <ActivePredictorSummary sensorId={activeSensorId} refreshToken={predictorRefreshToken} />
            </section>
            <RecalibrationPanel
              sensorId={activeSensorId}
              workspace={workspace}
              refreshToken={predictorRefreshToken}
              onRecalibrated={handleRecalibrated}
            />
            <section aria-label="Linaje de recalibraciones">
              <h3 className="app-subsection-heading">Linaje de recalibraciones</h3>
              <LineageChain sensorId={activeSensorId} refreshToken={lineageRefreshToken} />
            </section>
          </section>
        )}

        {route === "evidencia" && (
          <section aria-labelledby="evidencia-heading">
            <h2 id="evidencia-heading" className="app-section-heading" tabIndex={-1}>
              Evidencia y arquitectura
            </h2>
            <ArchitectureFlow />
            <EvidencePanel />
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
