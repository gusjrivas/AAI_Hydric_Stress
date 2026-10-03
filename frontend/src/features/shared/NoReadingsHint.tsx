/**
 * Orientación cuando un punto de medición no tiene mediciones: el pipeline de
 * herramientas técnicas necesita un dataset por punto, que se crea al cargar
 * lecturas (Laboratorio con sensor simulado, o la demostración acelerada).
 */
export function NoReadingsHint() {
  return (
    <p className="no-readings-hint">
      Las mediciones de un punto se cargan desde el Laboratorio (sensor simulado) o con la demostración.{" "}
      <a href="#laboratorio-sensores">Ir al Laboratorio</a>
    </p>
  );
}
