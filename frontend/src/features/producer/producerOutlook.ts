import type { Forecast, ForecastBatch } from "./forecastsApi";
import type { ReadingsResult } from "./readingsApi";

/**
 * Lenguaje cotidiano para la respuesta principal de «Mi cultivo». Solo reformula lo que el backend ya
 * decidió (alerta combinada por día, horizontes sin pronóstico, antigüedad de los datos): no calcula
 * probabilidades ni cambia ninguna decisión.
 *
 * Regla de semántica: `alert = false` significa «sin alerta prevista», nada más. Nunca se convierte en «sin
 * estrés», «no habrá falta de agua» ni en una garantía agronómica.
 */

export type DayState = "alert" | "clear" | "none";

export interface OutlookDay {
  horizon: 1 | 2 | 3;
  date: string | null;
  /** «mañana», «el sábado 17 de junio» (sin artículo: «mañana»). */
  when: string;
  /** Forma corta para el rótulo de la tira: «Mañana», «Sáb 17 jun». */
  label: string;
  state: DayState;
}

export interface Outlook {
  /** «stale»: hay pronóstico, pero las mediciones son viejas y no describe la situación de hoy. */
  tone: "alert" | "clear" | "none" | "stale";
  headline: string;
  detail: string;
  days: OutlookDay[];
}

const MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const SHORT_MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const WEEKDAYS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
const SHORT_WEEKDAYS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

function utc(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function diffDays(dateIso: string, todayIso: string): number {
  return Math.round((utc(dateIso).getTime() - utc(todayIso).getTime()) / 86_400_000);
}

/** «hoy», «mañana», «pasado mañana» o «el jueves 5 de junio» (con año si no es el actual). */
export function friendlyDay(dateIso: string, todayIso: string): { when: string; label: string } {
  const diff = diffDays(dateIso, todayIso);
  const date = utc(dateIso);
  const weekday = WEEKDAYS[date.getUTCDay()];
  const sameYear = date.getUTCFullYear() === utc(todayIso).getUTCFullYear();
  const full = `${weekday} ${date.getUTCDate()} de ${MONTHS[date.getUTCMonth()]}${sameYear ? "" : ` de ${date.getUTCFullYear()}`}`;
  const short = `${SHORT_WEEKDAYS[date.getUTCDay()]} ${date.getUTCDate()} ${SHORT_MONTHS[date.getUTCMonth()]}${sameYear ? "" : ` ${date.getUTCFullYear()}`}`;
  if (diff === 0) return { when: "hoy", label: "Hoy" };
  if (diff === 1) return { when: "mañana", label: "Mañana" };
  if (diff === 2) return { when: "pasado mañana", label: "Pasado mañana" };
  return { when: `el ${full}`, label: short.charAt(0).toUpperCase() + short.slice(1) };
}

/** «a», «a y b», «a, b y c». */
export function joinPhrases(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}`;
}

/** Las mediciones de ayer son lo normal; desde 2 días de antigüedad el pronóstico deja de describir «hoy». */
const STALE_FROM_DAYS = 2;

/** «los días 18 al 20 de junio de 2023» (o con ambos meses si el rango cruza de mes). */
function rangeText(dates: string[]): string {
  if (dates.length === 0) return "esos días";
  const first = utc(dates[0]);
  const last = utc(dates[dates.length - 1]);
  const year = last.getUTCFullYear();
  const end = `${last.getUTCDate()} de ${MONTHS[last.getUTCMonth()]} de ${year}`;
  if (dates.length === 1) return `el ${end}`;
  if (first.getUTCMonth() === last.getUTCMonth() && first.getUTCFullYear() === year) return `los días ${first.getUTCDate()} al ${end}`;
  const start = `${first.getUTCDate()} de ${MONTHS[first.getUTCMonth()]}${first.getUTCFullYear() === year ? "" : ` de ${first.getUTCFullYear()}`}`;
  return `los días ${start} al ${end}`;
}

function lowerFirst(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

export function describeOutlook(batch: ForecastBatch): Outlook {
  const base = describeFresh(batch);
  const stale = batch.data_age_days !== null && batch.data_age_days >= STALE_FROM_DAYS;
  if (!stale || base.tone === "none") return base;
  const dates = base.days.map((day) => day.date).filter((date): date is string => date !== null).sort();
  return {
    tone: "stale",
    headline: "Este pronóstico no es actual",
    detail: `La última medición es de hace ${batch.data_age_days} días y el pronóstico correspondía a ${rangeText(dates)}. En ese momento indicaba: ${lowerFirst(base.headline)}. Revisá cómo está el cultivo ahora.`,
    days: base.days,
  };
}

function describeFresh(batch: ForecastBatch): Outlook {
  const today = batch.server_today;
  const days: OutlookDay[] = batch.slots.map((slot) => {
    const date = slot.target_date;
    const friendly = date ? friendlyDay(date, today) : { when: `el día ${slot.horizon_days}`, label: `Día ${slot.horizon_days}` };
    const state: DayState = slot.status === "available" ? (slot.alert ? "alert" : "clear") : "none";
    return { horizon: slot.horizon_days, date, when: friendly.when, label: friendly.label, state };
  });
  const phrases = (state: DayState) => days.filter((day) => day.state === state).map((day) => day.when);
  const alerted = phrases("alert");
  const clear = phrases("clear");
  const none = phrases("none");
  const noForecastNote = none.length > 0 ? ` Para ${joinPhrases(none)} no hay pronóstico: eso no significa que no haya riesgo.` : "";

  if (alerted.length > 0) {
    return {
      tone: "alert",
      headline: `Alerta prevista: posible falta de agua ${joinPhrases(alerted)}`,
      detail: `Revisá cómo está el cultivo.${noForecastNote}`,
      days,
    };
  }
  if (clear.length > 0) {
    return {
      tone: "clear",
      headline: clear.length === 3 ? "Sin alerta prevista para los próximos 3 días" : `Sin alerta prevista para ${joinPhrases(clear)}`,
      detail: `Que no haya alerta no garantiza que el cultivo esté en buenas condiciones: revisá su estado.${noForecastNote}`,
      days,
    };
  }
  return {
    tone: "none",
    headline: "No hay información suficiente para emitir un pronóstico",
    detail: "Se recomienda verificar el estado del cultivo.",
    days,
  };
}

/**
 * Aviso de datos viejos, tal como lo informa el backend (`data_age_days`); null si no hay nada que avisar.
 * Cuando el titular ya dice «Este pronóstico no es actual» (`describeOutlook` con tono «stale») no se muestra
 * este aviso aparte: la advertencia principal es una sola.
 */
export function staleNotice(batch: ForecastBatch): string | null {
  if (batch.data_age_days === null || batch.data_age_days <= 0) return null;
  return `La última medición tiene ${batch.data_age_days} días de antigüedad. Los resultados corresponden a esas fechas; no describen necesariamente la situación de hoy.`;
}

function addDays(iso: string, days: number): string {
  const d = utc(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/**
 * Arma el lote de pronósticos ya guardado más reciente a partir del listado (solo lectura): el de mayor
 * fecha de emisión. Los horizontes que no figuran se marcan «no guardado»; nunca se inventa un motivo del modelo.
 */
export function buildSavedBatch(
  items: Forecast[],
  context: { server_today: string; data_age_days: number | null; provenance: ReadingsResult["provenance"] },
): ForecastBatch | null {
  if (items.length === 0) return null;
  const latest = [...items].sort((a, b) => b.as_of_date.localeCompare(a.as_of_date) || b.issued_at.localeCompare(a.issued_at))[0];
  const group = items.filter((item) => item.batch_id === latest.batch_id);
  const slots = ([1, 2, 3] as const).map((horizon) => {
    const found = group.find((item) => item.horizon_days === horizon);
    return found
      ? ({ ...found, status: "available" } as const)
      : ({ horizon_days: horizon, target_date: addDays(latest.as_of_date, horizon), status: "unavailable", reason_code: "not_saved" } as const);
  });
  return {
    batch_id: latest.batch_id,
    revision: 1,
    as_of_date: latest.as_of_date,
    data_age_days: context.data_age_days,
    server_today: context.server_today,
    provenance: context.provenance,
    calendar_timezone: "UTC",
    slots: [...slots],
  };
}
