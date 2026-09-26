import { ForecastReviewsProvider } from "./ForecastReviewsContext";
import { ForecastsSection } from "./ForecastsSection";
import { HistoricalWalkthrough } from "./HistoricalWalkthrough";

/**
 * `ForecastsSection` (operativo, reloj real, rutas `/forecasts/...`) y
 * `HistoricalWalkthrough` (recorrido histórico, reloj simulado, rutas
 * `/historical/...`) nunca comparten un `ForecastReviewsProvider`: cada
 * `ForecastCard` publica y lee actualizaciones a través de ese contexto
 * por `forecast_id`, sin distinguir con qué reloj se renderizó -- si
 * ambos compartieran uno, una tarjeta histórica podría terminar
 * mostrando la revisión operativa (o viceversa) solo porque llegó con
 * una revisión igual o mayor. `ForecastsSection` recibe su propio
 * proveedor, scoped a esta pantalla; `HistoricalWalkthrough` queda fuera
 * de cualquier proveedor y usa el contexto por defecto (sin publicar ni
 * leer nada compartido), consistente con que el backend ya aísla su
 * almacenamiento (`HistoricalReviewStore`, nunca
 * `OperationalRepository`).
 */
export function ProducerHistoryScreen({ sensorId }: { sensorId: string }) {
  return (
    <>
      <ForecastReviewsProvider key={sensorId}>
        <ForecastsSection sensorId={sensorId} />
      </ForecastReviewsProvider>
      <HistoricalWalkthrough sensorId={sensorId} />
    </>
  );
}
