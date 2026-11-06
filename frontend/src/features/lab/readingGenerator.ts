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

/** Humedad del suelo de partida, dentro del rango físico. */
const INITIAL_SOIL_MOISTURE = 0.34;
/** Humedad del suelo mínima que el generador permite (suelo nunca exactamente seco). */
const MIN_SOIL_MOISTURE = 0.02;
/** Días de un ciclo estacional del generador. */
const SEASON_DAYS = 120;
/** Lluvias posibles de un día con precipitación (mm) y probabilidad de que el día sea lluvioso. */
const RAIN_AMOUNTS_MM = [8, 15, 28] as const;
const RAIN_DAY_PROBABILITY = 0.24;
/** Recarga del suelo por mm de lluvia y secado diario máximo por evapotranspiración. */
const RECHARGE_PER_MM = 0.0035;
const DRYING_RATE = 0.0125;
/** Efecto de una sequía: sin lluvia, más calor (°C) y más radiación (MJ/m²). */
const DRY_EXTRA_TEMPERATURE = 9;
const DRY_EXTRA_RADIATION = 6;

export interface WaterBalanceOptions {
  /** Racha seca: sin lluvia, más calor y más radiación. */
  dry?: boolean;
}

/**
 * Lectura diaria por balance hídrico simple: la lluvia recarga la humedad del
 * suelo y la temperatura y la radiación la secan. Así el clima y la humedad
 * están relacionados (lo que el predictor operativo necesita aprender) y una
 * racha seca produce una caída sostenida de la humedad, a diferencia de un
 * paso aleatorio independiente por variable.
 *
 * La humedad previa es el estado del balance (`previous` o un valor inicial
 * moderado). `dayIndex` ubica el día en un ciclo estacional. Es un generador
 * de demostración, no un modelo agronómico.
 */
export function generateWaterBalanceReading(
  previous: LabReadingValues | null,
  rand: () => number,
  dayIndex: number,
  options: WaterBalanceOptions = {},
): LabReadingValues {
  const season = Math.sin((dayIndex / SEASON_DAYS) * 2 * Math.PI);
  let temperature = 22 + 6 * season + gaussian(rand) * 1.5;
  let radiation = clamp(18 + 6 * season + gaussian(rand) * 2, LAB_RANGES.solar_radiation);
  const humidity = clamp(60 - 10 * season + gaussian(rand) * 5, LAB_RANGES.relative_humidity);
  const wind = clamp(8 + gaussian(rand) * 2, LAB_RANGES.wind_speed);
  const rainRoll = rand();
  const rainPick = rand();
  let rain = rainRoll < RAIN_DAY_PROBABILITY ? RAIN_AMOUNTS_MM[Math.floor(rainPick * RAIN_AMOUNTS_MM.length)] : 0;
  if (options.dry) {
    rain = 0;
    temperature += DRY_EXTRA_TEMPERATURE;
    radiation = clamp(radiation + DRY_EXTRA_RADIATION, LAB_RANGES.solar_radiation);
  }
  temperature = clamp(temperature, LAB_RANGES.temperature);
  const soilBefore = previous ? previous.soil_moisture : INITIAL_SOIL_MOISTURE;
  const drying = DRYING_RATE * (Math.max(temperature, 0) / 25) * (radiation / 18);
  const soil = clamp(soilBefore + RECHARGE_PER_MM * rain - drying, [MIN_SOIL_MOISTURE, LAB_RANGES.soil_moisture[1]]);
  return {
    soil_moisture: soil,
    temperature,
    relative_humidity: humidity,
    precipitation: rain,
    solar_radiation: radiation,
    wind_speed: wind,
  };
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
