/**
 * Filtro puro de "pertenencia a la selección vigente" (Paso 4.1, cierre
 * §1). Cada resultado asíncrono (predicción, historial, feedback) se
 * etiqueta con el `origin`/`date` de la selección para la que se pidió.
 * `visibleFor` decide, en cada render, si ese resultado corresponde a la
 * selección actual — sin depender de que ningún `useEffect` haya corrido
 * todavía. Es una función pura: no lee refs, no depende de temporización de
 * React, así que la garantía se puede probar directamente con datos, sin
 * fingir la carrera entre el render y el efecto.
 *
 * Guarda inicial (loading) para una selección recién elegida: se construye
 * con `initialFor`, ya etiquetada con esa selección, así que también pasa
 * `visibleFor` de inmediato — nunca hace falta un valor "sin etiquetar".
 */
export interface ForSelection<T> {
  origin: string;
  date: string;
  value: T;
}

export function taggedFor<T>(origin: string, date: string, value: T): ForSelection<T> {
  return { origin, date, value };
}

export function belongsToSelection<T>(
  tagged: ForSelection<T>,
  selectedOrigin: string,
  simulatedDate: string,
): boolean {
  return tagged.origin === selectedOrigin && tagged.date === simulatedDate;
}

/**
 * Devuelve `tagged.value` si pertenece a la selección vigente; si no (por
 * ejemplo, es el resultado de la selección anterior y el efecto todavía no
 * corrió para la nueva), devuelve `fallback` en su lugar.
 */
export function visibleFor<T>(
  tagged: ForSelection<T>,
  selectedOrigin: string,
  simulatedDate: string,
  fallback: T,
): T {
  return belongsToSelection(tagged, selectedOrigin, simulatedDate) ? tagged.value : fallback;
}
