import { createContext, useContext } from "react";
import type { Forecast } from "./forecastsApi";

export const ReviewsContext = createContext<{
  updates: Record<string, Forecast>;
  publish: (forecast: Forecast) => void;
}>({ updates: {}, publish: () => {} });

export function useForecastReviews() { return useContext(ReviewsContext); }