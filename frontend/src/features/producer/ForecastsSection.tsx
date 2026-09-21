import { useEffect, useState } from "react";
import { ForecastCard } from "./ForecastCard";
import { ProducerV2UnavailableError } from "./catalogApi";
import { listForecasts } from "./forecastsApi";
import type { Forecast, ReviewStatus } from "./forecastsApi";
import "./ForecastsSection.css";

type FeedState =
  | { key: string; status: "loading" }
  | { key: string; status: "error"; message: string }
  | {
      key: string;
      status: "ready";
      items: Forecast[];
      nextCursor: string | null;
      pendingTotal: number;
      reviewablePendingTotal: number;
    };

/**
 * Historial paginado de emisiones de un sensor. Se usa dos veces en esta
 * pantalla (historial completo y pendientes de revisar) con filtros
 * distintos; una respuesta atrasada de un sensor o filtro previo no debe
 * reemplazar la lista vigente (misma protección que `ProducerHistoryPanel`).
 */
function useForecastFeed(sensorId: string, reviewStatus?: ReviewStatus) {
  const feedKey = `${sensorId}:${reviewStatus ?? "all"}`;
  const [resetToken, setResetToken] = useState(0);
  const key = `${feedKey}:${resetToken}`;
  const [state, setState] = useState<FeedState>({ key, status: "loading" });
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState({ key, status: "loading" });
    listForecasts(sensorId, { reviewStatus, limit: 20 }).then(
      (result) => {
        if (cancelled) return;
        setState({
          key,
          status: "ready",
          items: result.items,
          nextCursor: result.next_cursor,
          pendingTotal: result.pending_total,
          reviewablePendingTotal: result.reviewable_pending_total,
        });
      },
      (error: Error) => {
        if (cancelled) return;
        const message =
          error instanceof ProducerV2UnavailableError
            ? error.message
            : `${error.message}`;
        setState({ key, status: "error", message });
      },
    );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sensorId, reviewStatus, resetToken]);

  const current = state.key === key ? state : null;

  async function loadMore() {
    if (!current || current.status !== "ready" || !current.nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const result = await listForecasts(sensorId, { reviewStatus, limit: 20, cursor: current.nextCursor });
      setState((prev) =>
        prev.key !== key || prev.status !== "ready"
          ? prev
          : {
              key,
              status: "ready",
              items: [...prev.items, ...result.items],
              nextCursor: result.next_cursor,
              pendingTotal: result.pending_total,
              reviewablePendingTotal: result.reviewable_pending_total,
            },
      );
    } catch {
      // El estado no cambia: "Ver más" queda disponible para reintentar.
    } finally {
      setLoadingMore(false);
    }
  }

  function retry() {
    setResetToken((n) => n + 1);
  }

  function updateItem(updated: Forecast) {
    setState((prev) =>
      prev.status !== "ready"
        ? prev
        : { ...prev, items: prev.items.map((item) => (item.forecast_id === updated.forecast_id ? updated : item)) },
    );
  }

  function removeFromPending(forecastId: string) {
    setState((prev) => {
      if (prev.status !== "ready") return prev;
      if (!prev.items.some((item) => item.forecast_id === forecastId)) return prev;
      return {
        ...prev,
        items: prev.items.filter((item) => item.forecast_id !== forecastId),
        pendingTotal: Math.max(0, prev.pendingTotal - 1),
        reviewablePendingTotal: Math.max(0, prev.reviewablePendingTotal - 1),
      };
    });
  }

  return { current, loadingMore, loadMore, retry, updateItem, removeFromPending };
}

function ForecastList({
  sensorId,
  feed,
  emptyMessage,
  onItemChanged,
}: {
  sensorId: string;
  feed: ReturnType<typeof useForecastFeed>;
  emptyMessage: string;
  onItemChanged: (updated: Forecast) => void;
}) {
  const { current, loadingMore, loadMore, retry } = feed;

  if (!current) return <p role="status">Cargando pronósticos…</p>;
  if (current.status === "loading") return <p role="status">Cargando pronósticos…</p>;
  if (current.status === "error") {
    return (
      <p role="alert">
        {current.message} <button type="button" onClick={retry}>Reintentar</button>
      </p>
    );
  }
  if (current.items.length === 0) {
    return <p role="status">{emptyMessage}</p>;
  }
  return (
    <>
      <ul className="forecast-list">
        {current.items.map((item) => (
          <li key={item.forecast_id}>
            <ForecastCard sensorId={sensorId} forecast={item} onChanged={onItemChanged} />
          </li>
        ))}
      </ul>
      {current.nextCursor && (
        <button type="button" onClick={() => void loadMore()} disabled={loadingMore}>
          {loadingMore ? "Cargando más…" : "Ver más"}
        </button>
      )}
    </>
  );
}

/**
 * Pronósticos y revisión humana de un sensor (contrato v2). Todavía no
 * existe generación real de emisiones: sin registros del backend, se
 * muestra el vacío honesto, nunca datos inventados ni un botón para
 * generar pronósticos de ejemplo.
 */
export function ForecastsSection({ sensorId }: { sensorId: string }) {
  const historyFeed = useForecastFeed(sensorId);
  const pendingFeed = useForecastFeed(sensorId, "pending");

  function handleHistoryChanged(updated: Forecast) {
    historyFeed.updateItem(updated);
    if (updated.review.status !== "pending") {
      pendingFeed.removeFromPending(updated.forecast_id);
    } else {
      pendingFeed.updateItem(updated);
    }
  }

  const counts = pendingFeed.current?.status === "ready" ? pendingFeed.current : null;

  return (
    <section className="forecasts-section" aria-label="Pronósticos y revisión">
      <div className="forecasts-subsection" role="group" aria-label="Pendientes de revisar">
        <div className="forecasts-heading">
          <h3>Pendientes de revisar</h3>
          {counts && (
            <p className="forecasts-counts">
              {counts.pendingTotal} {counts.pendingTotal === 1 ? "pendiente en total" : "pendientes en total"}
              {counts.reviewablePendingTotal !== counts.pendingTotal &&
                ` · ${counts.reviewablePendingTotal} ${counts.reviewablePendingTotal === 1 ? "habilitado" : "habilitados"} para revisar ahora`}
            </p>
          )}
        </div>
        <p>
          Un pronóstico queda pendiente hasta que registrás tu opinión. No hay vencimiento: los pendientes antiguos
          siguen disponibles acá, no solo los recientes.
        </p>
        <ForecastList
          sensorId={sensorId}
          feed={pendingFeed}
          emptyMessage="No tenés pronósticos pendientes de revisar."
          onItemChanged={handleHistoryChanged}
        />
      </div>

      <div className="forecasts-subsection" role="group" aria-label="Historial de pronósticos">
        <div className="forecasts-heading">
          <h3>Historial de pronósticos</h3>
        </div>
        <p>
          Cada emisión es independiente aunque coincida la fecha objetivo: se distinguen por la fecha de emisión y el
          horizonte con el que se calcularon.
        </p>
        <ForecastList
          sensorId={sensorId}
          feed={historyFeed}
          emptyMessage="Todavía no hay pronósticos disponibles. La ausencia de pronósticos no significa ausencia de riesgo: seguí observando el cultivo."
          onItemChanged={handleHistoryChanged}
        />
      </div>
    </section>
  );
}
