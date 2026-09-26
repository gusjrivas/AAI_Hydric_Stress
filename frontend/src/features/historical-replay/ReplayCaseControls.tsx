interface Props {
  origins: string[];
  selectedOrigin: string;
  simulatedDate: string;
  targetDate: string;
  minDate: string;
  maxDate: string;
  onSelectOrigin: (origin: string) => void;
  onMoveClock: (days: number) => void;
  onResetToCaseStart: () => void;
  onRevealTarget: () => void;
}

/**
 * Selección temporal comprensible (Paso "recorrido guiado" §B). Distingue
 * tres fechas que se confunden fácilmente en la versión anterior de esta
 * pantalla: la de los datos usados para predecir (el origen), la que ya
 * alcanzó la reproducción (el reloj) y la fecha objetivo de la predicción.
 * Cambiar el origen también reubica el reloj en ese origen (oculta
 * inmediatamente cualquier resultado posterior) — a diferencia de la
 * versión previa, donde origen y reloj eran independientes y confundían al
 * usuario ("¿por qué sigo viendo el resultado de otro caso?").
 */
export function ReplayCaseControls({
  origins,
  selectedOrigin,
  simulatedDate,
  targetDate,
  minDate,
  maxDate,
  onSelectOrigin,
  onMoveClock,
  onResetToCaseStart,
  onRevealTarget,
}: Props) {
  const alreadyAtOrPastTarget = simulatedDate >= targetDate;

  return (
    <section className="hr-controls" aria-label="Selección del caso y reloj de la reproducción">
      <label className="hr-origin-label">
        Datos disponibles hasta
        <select
          value={selectedOrigin}
          onChange={(event) => onSelectOrigin(event.target.value)}
        >
          {origins.map((origin) => (
            <option key={origin} value={origin}>
              {origin}
            </option>
          ))}
        </select>
      </label>

      <dl className="hr-dates">
        <div>
          <dt>Fecha de los datos usados para predecir</dt>
          <dd>{selectedOrigin}</dd>
        </div>
        <div>
          <dt>Fecha hasta la que avanzó la reproducción</dt>
          <dd aria-live="polite" data-testid="hr-clock-value">
            {simulatedDate}
          </dd>
        </div>
        <div>
          <dt>Fecha objetivo de la predicción</dt>
          <dd>{targetDate}</dd>
        </div>
      </dl>

      <div className="hr-clock-controls">
        <button type="button" onClick={() => onMoveClock(-1)} disabled={simulatedDate === minDate}>
          ◀ Retroceder un día
        </button>
        <button type="button" onClick={() => onMoveClock(1)} disabled={simulatedDate === maxDate}>
          Avanzar un día ▶
        </button>
        <button type="button" onClick={onResetToCaseStart} disabled={simulatedDate === selectedOrigin}>
          Volver al inicio de este caso
        </button>
      </div>

      {!alreadyAtOrPastTarget && (
        <button type="button" className="hr-reveal-action" onClick={onRevealTarget}>
          Ver qué ocurrió el {targetDate}
        </button>
      )}
    </section>
  );
}
