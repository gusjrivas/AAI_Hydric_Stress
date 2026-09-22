import { useState } from "react";
import type { ReactNode } from "react";
import type { Forecast } from "./forecastsApi";
import { ReviewsContext } from "./useForecastReviews";

/** One review per emission across the forecast, pending list and history. */
export function ForecastReviewsProvider({ children }: { children: ReactNode }) {
  const [updates, setUpdates] = useState<Record<string, Forecast>>({});
  function publish(forecast: Forecast) {
    setUpdates((current) => {
      const previous = current[forecast.forecast_id];
      if (previous && previous.review.revision >= forecast.review.revision) return current;
      return { ...current, [forecast.forecast_id]: forecast };
    });
  }
  return <ReviewsContext.Provider value={{ updates, publish }}>{children}</ReviewsContext.Provider>;
}

