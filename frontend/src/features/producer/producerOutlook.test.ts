import { describe, expect, it } from "vitest";
import { buildSavedBatch, describeOutlook, friendlyDay, joinPhrases, staleNotice } from "./producerOutlook";
import { sensorLabel } from "./sensorLabels";
import type { Forecast, ForecastBatch } from "./forecastsApi";

function available(h: 1 | 2 | 3, target: string, alert: boolean, batchId = "b1", asOf = "2026-06-03"): Forecast & { status: "available" } {
  return { status: "available", forecast_id: `f${h}${batchId}`, sensor_id: "s", batch_id: batchId, as_of_date: asOf, horizon_days: h, target_date: target, issued_at: `${asOf}T00:00:00Z`, alert } as unknown as Forecast & { status: "available" };
}
const unavailable = (h: 1 | 2 | 3, target: string | null) => ({ horizon_days: h, target_date: target, status: "unavailable" as const, reason_code: "model_not_available" });
function batch(slots: ForecastBatch["slots"], extra: Partial<ForecastBatch> = {}): ForecastBatch {
  return { batch_id: "b1", revision: 1, as_of_date: "2026-06-03", data_age_days: 0, server_today: "2026-06-03", provenance: "real", calendar_timezone: "UTC", slots, ...extra };
}

describe("friendlyDay", () => {
  it("speaks of today, tomorrow and the day after in everyday words, and of the weekday and date beyond that", () => {
    expect(friendlyDay("2026-06-03", "2026-06-03")).toMatchObject({ when: "hoy", label: "Hoy" });
    expect(friendlyDay("2026-06-04", "2026-06-03")).toMatchObject({ when: "mañana", label: "Mañana" });
    expect(friendlyDay("2026-06-05", "2026-06-03")).toMatchObject({ when: "pasado mañana", label: "Pasado mañana" });
    expect(friendlyDay("2026-06-06", "2026-06-03")).toEqual({ when: "el sábado 6 de junio", label: "Sáb 6 jun" });
  });
  it("adds the year when the date is not in the current year (old demonstration data)", () => {
    expect(friendlyDay("2023-06-18", "2026-10-03")).toEqual({ when: "el domingo 18 de junio de 2023", label: "Dom 18 jun 2023" });
  });
  it("joins phrases the way people say them", () => {
    expect(joinPhrases(["mañana"])).toBe("mañana");
    expect(joinPhrases(["mañana", "pasado mañana"])).toBe("mañana y pasado mañana");
    expect(joinPhrases(["a", "b", "c"])).toBe("a, b y c");
  });
});

describe("describeOutlook", () => {
  it("says there is possible water shortage on the alerted days and always asks to check the crop", () => {
    const outlook = describeOutlook(batch([available(1, "2026-06-04", false), available(2, "2026-06-05", true), available(3, "2026-06-06", true)]));
    expect(outlook.tone).toBe("alert");
    expect(outlook.headline).toBe("Alerta prevista: posible falta de agua pasado mañana y el sábado 6 de junio");
    expect(outlook.detail).toMatch(/revisá cómo está el cultivo/i);
    expect(outlook.days.map((d) => d.state)).toEqual(["clear", "alert", "alert"]);
  });

  it("never turns the absence of an alert into a guarantee", () => {
    const outlook = describeOutlook(batch([available(1, "2026-06-04", false), available(2, "2026-06-05", false), available(3, "2026-06-06", false)]));
    expect(outlook.tone).toBe("clear");
    expect(outlook.headline).toBe("Sin alerta prevista para los próximos 3 días");
    expect(outlook.detail).toMatch(/no garantiza que el cultivo esté en buenas condiciones/i);
  });

  it("keeps «sin alerta» and «sin pronóstico» apart: a missing day is not a quiet day", () => {
    const outlook = describeOutlook(batch([available(1, "2026-06-04", false), unavailable(2, "2026-06-05"), unavailable(3, "2026-06-06")]));
    expect(outlook.tone).toBe("clear");
    expect(outlook.headline).toBe("Sin alerta prevista para mañana");
    expect(outlook.detail).toMatch(/para pasado mañana y el sábado 6 de junio no hay pronóstico: eso no significa que no haya riesgo/i);
    expect(outlook.days.map((d) => d.state)).toEqual(["clear", "none", "none"]);
  });

  it("an alert wins over missing days but still reports them", () => {
    const outlook = describeOutlook(batch([unavailable(1, "2026-06-04"), available(2, "2026-06-05", true), unavailable(3, "2026-06-06")]));
    expect(outlook.tone).toBe("alert");
    expect(outlook.detail).toMatch(/para mañana y el sábado 6 de junio no hay pronóstico/i);
  });

  it("with no forecast at all it asks to check the crop instead of saying everything is fine", () => {
    const outlook = describeOutlook(batch([unavailable(1, "2026-06-04"), unavailable(2, "2026-06-05"), unavailable(3, "2026-06-06")]));
    expect(outlook.tone).toBe("none");
    expect(outlook.headline).toMatch(/no hay información suficiente/i);
    expect(outlook.detail).toMatch(/verificar el estado del cultivo/i);
  });
});

describe("describeOutlook with old measurements", () => {
  it("does not present a past-dated «no alert» as today's answer", () => {
    const outlook = describeOutlook(batch([available(1, "2023-06-18", false), available(2, "2023-06-19", false), available(3, "2023-06-20", false)], { data_age_days: 1204, server_today: "2026-10-03" }));
    expect(outlook.tone).toBe("stale");
    expect(outlook.headline).toBe("Este pronóstico no es actual");
    expect(outlook.detail).toMatch(/la última medición es de hace 1204 días/i);
    expect(outlook.detail).toMatch(/correspondía a los días 18 al 20 de junio de 2023/i);
    expect(outlook.detail).toMatch(/indicaba: sin alerta prevista para los próximos 3 días/i);
    expect(outlook.detail).toMatch(/revisá cómo está el cultivo ahora/i);
  });
  it("treats yesterday's measurements as normal and keeps the usual answer", () => {
    const outlook = describeOutlook(batch([available(1, "2026-06-04", false), available(2, "2026-06-05", false), available(3, "2026-06-06", false)], { data_age_days: 1 }));
    expect(outlook.tone).toBe("clear");
  });
  it("keeps the alert wording visible when the data is old", () => {
    const outlook = describeOutlook(batch([available(1, "2026-06-04", true), unavailable(2, "2026-06-05"), unavailable(3, "2026-06-06")], { data_age_days: 5 }));
    expect(outlook.tone).toBe("stale");
    expect(outlook.detail).toMatch(/indicaba: alerta prevista: posible falta de agua/i);
  });
});

describe("semántica de «sin alerta»", () => {
  const states = ["clear", "alert", "none"] as const;
  const forbidden = /no se espera falta de agua|no habrá|sin estrés|sin falta de agua|todo bien|está bien\b|libre de/i;
  it("nunca convierte alert=false en una garantía, para todas las combinaciones de días y de antigüedad de datos", () => {
    for (const a of states) for (const b of states) for (const c of states) for (const age of [0, 1, 3, 1204]) {
      const slot = (h: 1 | 2 | 3, st: (typeof states)[number]) => st === "none" ? unavailable(h, `2026-06-0${h + 3}`) : available(h, `2026-06-0${h + 3}`, st === "alert");
      const outlook = describeOutlook(batch([slot(1, a), slot(2, b), slot(3, c)], { data_age_days: age }));
      const text = `${outlook.headline} ${outlook.detail}`;
      expect(text, `${a}/${b}/${c} edad ${age}`).not.toMatch(forbidden);
      // Sin alerta siempre va acompañado de la aclaración de que no es una garantía.
      if (outlook.tone === "clear") expect(outlook.detail).toMatch(/no garantiza/i);
    }
  });
  it("un titular sin alerta dice «sin alerta prevista» y no «no hay falta de agua»", () => {
    const outlook = describeOutlook(batch([available(1, "2026-06-04", false), available(2, "2026-06-05", false), available(3, "2026-06-06", false)]));
    expect(outlook.headline).toMatch(/^sin alerta prevista/i);
  });
});

describe("staleNotice", () => {
  it("warns only when the backend reports old data", () => {
    expect(staleNotice(batch([], { data_age_days: 0 }))).toBeNull();
    expect(staleNotice(batch([], { data_age_days: null }))).toBeNull();
    expect(staleNotice(batch([], { data_age_days: 3 }))).toMatch(/3 días de antigüedad.*no describen necesariamente la situación de hoy/i);
  });
});

describe("buildSavedBatch", () => {
  const context = { server_today: "2026-06-05", data_age_days: 2, provenance: "real" as const };
  it("returns null when nothing was saved yet", () => {
    expect(buildSavedBatch([], context)).toBeNull();
  });
  it("picks the most recently issued batch and marks horizons that were not saved, without inventing a model reason", () => {
    const items = [
      available(1, "2026-06-04", false, "old", "2026-06-03"),
      available(2, "2026-06-05", false, "old", "2026-06-03"),
      available(1, "2026-06-05", false, "new", "2026-06-04"),
      available(3, "2026-06-07", true, "new", "2026-06-04"),
    ];
    const saved = buildSavedBatch(items, context)!;
    expect(saved.batch_id).toBe("new");
    expect(saved.as_of_date).toBe("2026-06-04");
    expect(saved.slots.map((s) => s.status)).toEqual(["available", "unavailable", "available"]);
    const missing = saved.slots[1];
    expect(missing.status === "unavailable" && missing.reason_code).toBe("not_saved");
    expect(missing.target_date).toBe("2026-06-06");
    expect(saved.data_age_days).toBe(2);
  });
});

describe("sensorLabel", () => {
  it("keeps a registered name, names the demonstration sites, and never shows a raw technical id", () => {
    expect(sensorLabel({ sensor_id: "sensor-a", display_name: "Sensor A", registered: true })).toBe("Sensor A");
    expect(sensorLabel({ sensor_id: "pergamino-ensemble-demo", display_name: "pergamino-ensemble-demo", registered: false })).toBe("Pergamino · demostración");
    expect(sensorLabel({ sensor_id: "melchor-romero-demo", display_name: "melchor-romero-demo" })).toBe("Melchor Romero · demostración");
    expect(sensorLabel({ sensor_id: "lote-sur", display_name: "lote-sur" })).toBe("Lote sur");
  });
});
