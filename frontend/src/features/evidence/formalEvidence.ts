// Evidencia experimental formal — congelada, estática, sin llamadas HTTP.
//
// Provenance exacta (no recalculada, no redondeada de forma distinta):
//   - Fuente: docs/research/reference-v3-formal-table.md
//     (docs/research/reference-v3-formal-results.json es el JSON crudo del
//     mismo experimento; el .md es la tabla ya verificada, ver
//     docs/research/hu8-analisis-resultados.md, sección 13).
//   - Protocolo: controlled_daily_v3 (docs/research/protocolo-experimental-v3.md).
//   - Experimento MLflow: hu7-controlled-daily-v3-formal
//     (8 configuraciones x 5 semillas [0,1,2,3,4] = 40 child runs + 8 parent runs).
//   - Tag científico: scientific-baseline-v3
//     (commit 7772ce0692860bf74836a5380c1e58e785baa85f, 2026-09-06).
//   - Interpretación vigente: docs/research/hu8-analisis-resultados.md, sección 13;
//     docs/research/hu8-auditoria-revalidacion.md.

export const FORMAL_EVIDENCE_SOURCE = {
  label: "Evidencia experimental formal — controlled_daily_v3",
  protocolFile: "docs/research/protocolo-experimental-v3.md",
  tableFile: "docs/research/reference-v3-formal-table.md",
  analysisFile: "docs/research/hu8-analisis-resultados.md (sección 13)",
  mlflowExperiment: "hu7-controlled-daily-v3-formal",
  scientificTag: "scientific-baseline-v3",
  scientificCommit: "7772ce0692860bf74836a5380c1e58e785baa85f",
};

export interface FormalConfigurationResult {
  configuracion: string;
  f1Media: number;
  f1Desvio: number;
  mccMedia: number;
  apMedia: number;
  runId: string;
}

// Copiado verbatim de docs/research/reference-v3-formal-table.md — no
// recalculado, no redondeado de forma distinta.
export const FORMAL_CONFIGURATIONS: FormalConfigurationResult[] = [
  { configuracion: "base", f1Media: 0.5592, f1Desvio: 0.0287, mccMedia: -0.0135, apMedia: 0.5816, runId: "6d516bb9f778450f8fbe2e5492818e57" },
  { configuracion: "recent_fraction_0.5", f1Media: 0.6891, f1Desvio: 0.0407, mccMedia: 0.1417, apMedia: 0.6546, runId: "70cc3df842df46bab7c501a8ffe03c51" },
  { configuracion: "sinteticos", f1Media: 0.5450, f1Desvio: 0.0986, mccMedia: 0.0582, apMedia: 0.6029, runId: "a98a5ee456204239aec5e9e5c1a18fc6" },
  { configuracion: "noise_test_only_0.3", f1Media: 0.5605, f1Desvio: 0.0346, mccMedia: 0.0100, apMedia: 0.5755, runId: "c98684bd7aa841818398a125901db72a" },
  { configuracion: "completa", f1Media: 0.5052, f1Desvio: 0.0374, mccMedia: -0.0706, apMedia: 0.5493, runId: "cbb37b55e9d941818350a3a25d583a9f" },
  { configuracion: "noise_both_0.3", f1Media: 0.5041, f1Desvio: 0.0719, mccMedia: -0.0058, apMedia: 0.5804, runId: "e5648fffe64244b2b8c2ab659f866fba" },
  { configuracion: "anomalias", f1Media: 0.5689, f1Desvio: 0.0395, mccMedia: 0.0110, apMedia: 0.5672, runId: "ecf3ef69368d47818999a6f2ecd21316" },
  { configuracion: "coverage_fraction_0.5", f1Media: 0.5238, f1Desvio: 0.0631, mccMedia: -0.0376, apMedia: 0.5913, runId: "f4c7ae32a19144fbb04f88317b7a9dfe" },
];

// Limitaciones ya documentadas — sin agregar conclusiones nuevas. Copiadas de
// docs/research/hu8-analisis-resultados.md, secciones 13.3 y 13.5.
export const FORMAL_EVIDENCE_LIMITATIONS: string[] = [
  "«base» es una configuración experimental de la arquitectura (Random Forest fijo, sin anomalías ni sintéticos), no un “enfoque tradicional” de riego.",
  "Detección de anomalías: evidencia MIXTA — F1/MCC mejoran en 3 de 5 semillas, pero AP empeora en las 5/5 semillas sin excepción.",
  "Datos sintéticos: evidencia mixta, restringida a este generador (normal multivariada) y a este dataset de un único sitio/año.",
  "«Completa» es consistentemente peor que «base» en las 3 métricas (AP 5/5 semillas); no incluye HITL cuantitativo y no debe describirse como \"arquitectura completa de los cuatro componentes\".",
  "Escasez por recencia (recent_fraction_0.5) es el único efecto consistente del estudio (5/5 semillas positivas en F1/MCC/AP); no permite afirmar que \"menos datos mejora el desempeño\" en general.",
  "Ruido (noise_both_0.3, noise_test_only_0.3): patrón casi nulo/mixto, sin evidencia de degradación uniforme ni de robustez general.",
  "Retroalimentación humana (HITL): evidencia funcional SÍ — evidencia cuantitativa formal de mejora predictiva NO (diseñada pero no ejecutada dentro de controlled_daily_v3, ver ADR-0009).",
];

export const OPERATIONAL_PREDICTOR_NOTE =
  "El predictor operativo vigente (esta demo) usa un contrato Random Forest explícito, " +
  "una decisión operativa deliberada distinta de la selección automática entre candidatos " +
  "que sí usa controlled_daily_v3 (openspec/specs/alerting-ui/spec.md, sección " +
  "\"Modelo operativo vs. selección automática experimental\"). Una recalibración exitosa en " +
  "esta demo no constituye evidencia de mejora métrica: es trazabilidad HITL funcional, " +
  "no una repetición del protocolo experimental formal.";
