import "./FactsStrip.css";

export interface Fact {
  label: string;
  value: string;
  sub?: string;
}

/**
 * Franja de contexto de lectura: qué datos se ven, cuándo se emitió, para qué
 * fechas aplica y hasta dónde llega el reloj. Misma pieza en el seguimiento
 * histórico y en «Mi cultivo» para que la identidad sea constante.
 */
export function FactsStrip({ facts, label = "Contexto de lectura" }: { facts: Fact[]; label?: string }) {
  return (
    <dl className="facts-strip" aria-label={label}>
      {facts.map((fact) => (
        <div key={fact.label}>
          <dt>{fact.label}</dt>
          <dd>{fact.value}</dd>
          {fact.sub && <dd className="facts-strip-sub">{fact.sub}</dd>}
        </div>
      ))}
    </dl>
  );
}
