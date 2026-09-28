/**
 * Generador sintético propio del laboratorio (HU5/HU6, capacidad
 * `alerting-ui`, tercer modo "Laboratorio / Sensores de prueba"). Cliente
 * HTTP más para `POST /sensors/{sensor_id}/readings` (ADR-0007: "el
 * endpoint no sabe ni le importa si quien llama es un sensor real o un
 * generador sintético"), implementado en TypeScript porque corre en el
 * navegador -- no es una copia del generador Python
 * (`src/data_ingestion/mock_sensor.py`), pero usa los mismos límites
 * físicos/climáticos documentados en `src/data_quality/rules.py`
 * (`AGRONOMIC_RANGES`, espejados abajo porque ese módulo Python no es
 * importable desde el frontend) para que:
 * - las lecturas "normales" (Escenario A) nunca disparen `out_of_range`
 *   por accidente;
 * - la perturbación del Escenario B sea una violación deliberada y
 *   verificable del mismo contrato que valida el backend real
 *   (`data_quality.quality_report`), nunca un valor arbitrario ni un
 *   resultado fabricado en el cliente.
 */

export interface LabReadingValues {
  soil_moisture: number;
  temperature: number;
  relative_humidity: number;
  precipitation: number;
  solar_radiation: number;
  wind_speed: number;
}

type RangeMap = Record<keyof LabReadingValues, [number, number]>;

const LAB_RANGES: RangeMap = {
  soil_moisture: [0.0, 0.6],
  temperature: [-10.0, 50.0],
  relative_humidity: [0.0, 100.0],
  precipitation: [0.0, 500.0],
  solar_radiation: [0.0, 40.0],
  wind_speed: [0.0, 50.0],
};

const STEP_FRACTION = 0.02;

/** PRNG determinista (mulberry32) para que el mismo `seed` produzca
 * siempre la misma secuencia -- "semilla/configuración fija" exigida para
 * los escenarios reproducibles. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function next() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gaussian(rand: () => number): number {
  const u1 = Math.max(rand(), 1e-9);
  const u2 = rand();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

function clamp(value: number, range: [number, number]): number {
  return Math.min(range[1], Math.max(range[0], value));
}

const COLUMNS = Object.keys(LAB_RANGES) as (keyof LabReadingValues)[];

/** Paso aleatorio acotado desde `previous` (o el punto medio del rango
 * físico si no hay lectura anterior), recortado al mismo rango --
 * análogo en espíritu a `mock_sensor.generate_next_reading`, sin
 * pretender ser el mismo algoritmo. */
export function generateNormalReading(
  previous: LabReadingValues | null,
  rand: () => number,
): LabReadingValues {
  const values = {} as LabReadingValues;
  for (const column of COLUMNS) {
    const range = LAB_RANGES[column];
    const step = (range[1] - range[0]) * STEP_FRACTION;
    const base = previous ? previous[column] : (range[0] + range[1]) / 2;
    values[column] = clamp(base + gaussian(rand) * step, range);
  }
  return values;
}

/** Escenario B: perturbación explícita -- fuerza la temperatura por
 * encima del límite físico documentado para que la regla real de calidad
 * del backend (`out_of_range`, `data_quality.quality_report`) la marque,
 * nunca un valor "casi anómalo" que dependiera del detector estadístico
 * (Isolation Forest, que no garantiza marcar un único punto). */
export function injectRangeAnomaly(reading: LabReadingValues): LabReadingValues {
  return { ...reading, temperature: LAB_RANGES.temperature[1] + 35 };
}

export function labRangeFor(column: keyof LabReadingValues): [number, number] {
  return LAB_RANGES[column];
}
