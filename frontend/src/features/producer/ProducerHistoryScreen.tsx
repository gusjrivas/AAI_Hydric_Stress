import { ForecastReviewsProvider } from "./ForecastReviewsContext";
import { ForecastsSection } from "./ForecastsSection";
import { HistoricalWalkthrough } from "./HistoricalWalkthrough";

export function ProducerHistoryScreen({ sensorId }: { sensorId: string }) {
  return (
    <ForecastReviewsProvider key={sensorId}>
      <p className="producer-eyebrow">HISTORIAL</p>
      <ForecastsSection sensorId={sensorId} />
      <HistoricalWalkthrough sensorId={sensorId} />
    </ForecastReviewsProvider>
  );
}
