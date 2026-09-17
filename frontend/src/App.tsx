import { useCallback, useState } from "react";
import "./App.css";
import { ArchitectureFlow } from "./features/architecture-flow/ArchitectureFlow";
import { QualityPanel } from "./features/quality/QualityPanel";
import { ForecastPage } from "./features/forecast/ForecastPage";
import { LineageChain } from "./features/lineage/LineageChain";
import { EvidencePanel } from "./features/evidence/EvidencePanel";

const SENSOR_ID_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;
const INITIAL_SENSOR_ID = "sensor-a";

function App() {
  const [draftSensorId, setDraftSensorId] = useState(INITIAL_SENSOR_ID);
  const [activeSensorId, setActiveSensorId] = useState(INITIAL_SENSOR_ID);
  const [sensorError, setSensorError] = useState<string | null>(null);
  const [forecastBusy, setForecastBusy] = useState(false);
  const [lineageRefreshToken, setLineageRefreshToken] = useState(0);

  const handleRecalibrated = useCallback(() => {
    setLineageRefreshToken((token) => token + 1);
  }, []);

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

      <ArchitectureFlow />
      <main className="app-sections">
        <section id="calidad" className="app-section" aria-labelledby="calidad-heading">
          <h2 id="calidad-heading" className="app-section-heading">
            1–2. Datos IoT y calidad
          </h2>
          <QualityPanel sensorId={activeSensorId} />
        </section>

        <section id="prediccion" className="app-section" aria-labelledby="prediccion-heading">
          <h2 id="prediccion-heading" className="app-section-heading">
            3–6. Features, predicción, alerta y feedback humano
          </h2>
          <ForecastPage
            sensorId={activeSensorId}
            onRecalibrated={handleRecalibrated}
            onBusyChange={setForecastBusy}
          />
        </section>

        <section id="linaje" className="app-section" aria-labelledby="linaje-heading">
          <h2 id="linaje-heading" className="app-section-heading">
            7. Recalibración y linaje
          </h2>
          <LineageChain sensorId={activeSensorId} refreshToken={lineageRefreshToken} />
        </section>

        <section id="evidencia" className="app-section" aria-labelledby="evidencia-heading">
          <h2 id="evidencia-heading" className="app-section-heading">
            Evidencia científica y limitaciones
          </h2>
          <EvidencePanel />
        </section>
      </main>
    </div>
  );
}

export default App;
