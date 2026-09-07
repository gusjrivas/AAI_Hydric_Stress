import { useCallback, useState } from "react";
import "./App.css";
import { ArchitectureFlow } from "./features/architecture-flow/ArchitectureFlow";
import { QualityPanel } from "./features/quality/QualityPanel";
import { ForecastPage } from "./features/forecast/ForecastPage";
import { LineageChain } from "./features/lineage/LineageChain";
import { EvidencePanel } from "./features/evidence/EvidencePanel";

const SENSOR_ID_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;

function App() {
  const [sensorId, setSensorId] = useState("sensor-a");
  const [lineageRefreshToken, setLineageRefreshToken] = useState(0);

  const handleRecalibrated = useCallback(() => {
    setLineageRefreshToken((token) => token + 1);
  }, []);

  const validSensorId = SENSOR_ID_PATTERN.test(sensorId) ? sensorId : null;

  return (
    <div className="app-page">
      <ArchitectureFlow />
      <main className="app-sections">
        <section id="calidad" className="app-section" aria-labelledby="calidad-heading">
          <h2 id="calidad-heading" className="app-section-heading">
            1–2. Datos IoT y calidad
          </h2>
          {validSensorId ? (
            <QualityPanel sensorId={validSensorId} />
          ) : (
            <p role="status">Ingresá un sensor_id válido para ver su calidad de datos.</p>
          )}
        </section>

        <section id="prediccion" className="app-section" aria-labelledby="prediccion-heading">
          <h2 id="prediccion-heading" className="app-section-heading">
            3–6. Features, predicción, alerta y feedback humano
          </h2>
          <ForecastPage
            sensorId={sensorId}
            onSensorIdChange={setSensorId}
            onRecalibrated={handleRecalibrated}
          />
        </section>

        <section id="linaje" className="app-section" aria-labelledby="linaje-heading">
          <h2 id="linaje-heading" className="app-section-heading">
            7. Recalibración y linaje
          </h2>
          {validSensorId ? (
            <LineageChain sensorId={validSensorId} refreshToken={lineageRefreshToken} />
          ) : (
            <p role="status">Ingresá un sensor_id válido para ver su linaje.</p>
          )}
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
