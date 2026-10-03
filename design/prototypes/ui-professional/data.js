/* Datos estáticos del prototipo de diseño. Ningún valor se envía ni se lee del backend.
   Procedencia de cada bloque indicada en `source`. Ver docs/design/ui-professional-redesign-plan.md */
(function () {
  // Melchor Romero: data/melchor_romero_2024_consolidado.parquet (columna soil_moisture, m³/m³).
  // El 2024-10-26 está vacío en la fuente; la API lo completa por arrastre del día anterior (imputado).
  var MELCHOR_SERIES = [
    ["2024-10-14", 0.344160, "obs"], ["2024-10-15", 0.316016, "obs"], ["2024-10-16", 0.324512, "obs"],
    ["2024-10-17", 0.317458, "obs"], ["2024-10-18", 0.338390, "obs"], ["2024-10-19", 0.313671, "obs"],
    ["2024-10-20", 0.296382, "obs"], ["2024-10-21", 0.294929, "obs"], ["2024-10-22", 0.278511, "obs"],
    ["2024-10-23", 0.294632, "obs"], ["2024-10-24", 0.349501, "obs"], ["2024-10-25", 0.363274, "obs"],
    ["2024-10-26", 0.363274, "imp"], ["2024-10-27", 0.329569, "obs"], ["2024-10-28", 0.327161, "obs"]
  ];

  // Pergamino: la serie diaria de humedad NO está versionada en el repositorio.
  // Serie ILUSTRATIVA (no son mediciones de Pergamino). Solo el umbral (P20 de entrenamiento 2015-2021) es real.
  var PERGAMINO_SERIES = [
    ["2023-06-07", 0.352, "obs"], ["2023-06-08", 0.349, "obs"], ["2023-06-09", 0.346, "obs"],
    ["2023-06-10", 0.341, "obs"], ["2023-06-11", 0.338, "obs"], ["2023-06-12", 0.336, "obs"],
    ["2023-06-13", 0.331, "obs"], ["2023-06-14", 0.329, "obs"], ["2023-06-15", 0.326, "obs"],
    ["2023-06-16", 0.326, "imp"], ["2023-06-17", 0.322, "obs"], ["2023-06-18", null, "miss"],
    ["2023-06-19", 0.321, "obs"], ["2023-06-20", 0.319, "obs"]
  ];

  function toSeries(rows) {
    return rows.map(function (r) { return { date: r[0], v: r[1], status: r[2] }; });
  }

  window.PROTO_DATA = {
    sites: {
      pergamino: {
        id: "pergamino",
        name: "Pergamino",
        region: "Buenos Aires, Argentina",
        tag: "Datos externos",
        tagKind: "external",
        source: "ERA5-Land / NASA POWER (reanálisis)",
        provenanceNote: "Son datos externos, no mediciones de un sensor instalado ni observaciones agronómicas directas del cultivo.",
        emissions: ["2023-06-13", "2023-06-14", "2023-06-15", "2023-06-16", "2023-06-17"],
        clockMax: "2023-06-20",
        periodLabel: "Emisiones persistidas del 13 al 17 de junio de 2023",
        threshold: 0.3130583333333333,
        thresholdNote: "Umbral del protocolo: humedad del suelo inferior al percentil 20 del período de entrenamiento 2015–2021.",
        yDomain: [0.30, 0.36],
        series: toSeries(PERGAMINO_SERIES),
        seriesIllustrative: true,
        forecastKind: "persisted", // pronósticos reales de la emisión persistida: 15 de 15 con "sin alerta por unanimidad"
        // único puntaje combinado citado en docs/design/ensemble-real-execution-report-2026-09-26.md
        knownScores: { "2023-06-15|1": 0.01657426242378581 },
        evidenceLink: true
      },
      melchor: {
        id: "melchor",
        name: "Melchor Romero",
        region: "La Plata, Buenos Aires, Argentina",
        tag: "Histórico",
        tagKind: "historical",
        source: "ESA CCI (humedad de suelo) / NASA POWER (clima)",
        provenanceNote: "Dataset real consolidado del repositorio, reutilizado aquí solo como datos de entrada del recorrido.",
        emissions: ["2024-10-20", "2024-10-21", "2024-10-22", "2024-10-23", "2024-10-24"],
        clockMax: "2024-10-28",
        periodLabel: "Emisiones persistidas del 20 al 24 de octubre de 2024",
        threshold: null,
        thresholdNote: "El umbral de Melchor Romero se calcula al preparar la demo y no está versionado: este prototipo no lo muestra.",
        yDomain: [0.26, 0.38],
        series: toSeries(MELCHOR_SERIES),
        seriesIllustrative: false,
        forecastKind: "example", // los pronósticos no están versionados: se muestran estados de ejemplo
        knownScores: {},
        evidenceLink: false
      }
    },
    // Plantillas de estados de ejemplo para el pronóstico (solo diseño).
    exampleScores: { alert: [0.71, 0.64, 0.58], noalert: [0.12, 0.09, 0.15] }
  };
})();
