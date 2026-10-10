export const PRODUCER_TABS = ["cultivo", "historial", "datos"] as const;
export type ProducerTab = (typeof PRODUCER_TABS)[number];

export const PRODUCER_TAB_LABELS: Record<ProducerTab, string> = {
  cultivo: "Pronóstico",
  historial: "Historial",
  datos: "Datos",
};
