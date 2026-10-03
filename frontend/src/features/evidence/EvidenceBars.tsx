export interface BarDatum {
  key: string;
  name: string;
  note?: string;
  /** `null` = no disponible: se muestra «n/d», nunca una barra en cero. */
  value: number | null;
  kind?: "active" | "reference" | "plain";
}

/**
 * Barras horizontales comparables. Son un complemento visual: cada fila ya
 * trae su valor en texto y la tabla completa sigue disponible en detalle.
 * La escala es absoluta (0 a `max`), nunca relativa al mejor valor, para no
 * exagerar diferencias pequeñas.
 */
export function EvidenceBars({
  label,
  data,
  max,
  decimals,
}: {
  label: string;
  data: BarDatum[];
  max: number;
  decimals: number;
}) {
  return (
    <div className="eb-bars" role="group" aria-label={label}>
      {data.map((item) => {
        const width = item.value === null ? 0 : Math.max(0, Math.min(1, item.value / max)) * 100;
        return (
          <div key={item.key} className={`eb-row eb-row--${item.kind ?? "plain"}`}>
            <div className="eb-name">
              {item.name}
              {item.note && <small>{item.note}</small>}
            </div>
            <div className="eb-track" aria-hidden="true">
              <div className="eb-fill" style={{ width: `${width}%` }} />
            </div>
            <div className="eb-value">{item.value === null ? "n/d" : item.value.toFixed(decimals)}</div>
          </div>
        );
      })}
    </div>
  );
}
