# HU1 — Auditoría de cierre

Este documento mapea los criterios de aceptación de la Épica 1 (issue #10) y el estado de los issues hijos (#21 a #32) contra la evidencia documental disponible. No cierra ningún issue: propone un estado por issue para revisión posterior.

## Criterios de aceptación del issue #10

### Criterio 1 — Se identificaron y analizaron antecedentes científicos y técnicos relevantes

**Estado: CUMPLE**

**Evidencia:** corpus consolidado de 450 registros (`docs/research/hu1-corpus-final.csv`), procesado a partir de exports reales de Scopus e IEEE Xplore (`docs/research/exports/`) y fuentes complementarias (Crossref, OpenAlex, DOAJ), con deduplicación, cribado semántico por título y abstract, y clasificación en incluir/excluir/indeterminado (`docs/research/hu1-cola-revision-humana.csv`). Selección representativa validada de 25 referencias (`docs/research/hu1-referencias-representativas-validadas.csv`), sintetizada en `docs/research/hu1-matriz-comparativa-final.md`. La revisión se caracteriza como una revisión bibliográfica estructurada y dirigida, con criterios explícitos de búsqueda, inclusión, exclusión, trazabilidad y verificación; no reclama exhaustividad.

**Limitaciones metodológicas documentadas (no afectan el cumplimiento de este criterio):** Web of Science no pudo ejecutarse por falta de acceso institucional a Document Search/Core Collection. AGRIS no pudo completarse bajo el protocolo previsto por limitación de herramienta. La cobertura regional (Argentina) se relevó mediante búsqueda dirigida acotada, no mediante el protocolo sistemático completo. 14 registros del corpus permanecen indeterminados por metadatos insuficientes, resultado válido de la evaluación cuando la evidencia disponible fue insuficiente para decidir inclusión o exclusión. Ninguna de estas limitaciones invalida la identificación y el análisis de antecedentes científicos y técnicos relevantes ya realizado sobre el corpus consolidado.

### Criterio 2 — Se documentaron las principales técnicas de IA aplicadas a la detección temprana de estrés hídrico

**Estado: CUMPLE**

**Evidencia:** `docs/research/hu1-matriz-comparativa-final.md` documenta, por eje, las técnicas relevadas: modelado predictivo (Random Forest, SVR, ANN, LSTM, Bi-GRU, ARIMA), detección de anomalías (reglas estadísticas, Isolation Forest, One-Class SVM, LOF), generación de datos sintéticos (GAN, VAE, TimeGAN, simulación restringida por física) y retroalimentación humana (sistemas expertos con intervención humana, plataformas colaborativas humano-robot).

**Limitaciones:** ninguna sustancial para este criterio específico.

### Criterio 3 — Se justificó la selección de las técnicas que serán evaluadas

**Estado: CUMPLE**

**Evidencia:** `docs/research/hu1-estado-del-arte.md`, sección 5 ("Criterios derivados para la selección de técnicas"), distingue para cada componente las técnicas candidatas por literatura, las efectivamente adoptadas por las especificaciones formales vigentes (`openspec/specs/predictive-modeling/spec.md`, `openspec/specs/data-quality/spec.md`, `openspec/specs/human-feedback/spec.md`) y las que permanecen como alternativas experimentales, sin modificar ninguna decisión formal ya adoptada.

**Limitaciones:** ninguna sustancial para este criterio específico.

### Criterio 4 — El estado del arte y el marco conceptual quedaron documentados

**Estado: CUMPLE**

**Evidencia:** `docs/research/hu1-estado-del-arte.md`, versión definitiva, con introducción, marco conceptual por eje, síntesis comparativa, vacancia revalidada, criterios de selección de técnicas, antecedentes regionales, limitaciones y conclusión.

**Limitaciones:** ninguna sustancial para este criterio específico.

## Auditoría de issues hijos (#21 a #32)

| Issue | Título | Evidencia disponible | Estado propuesto |
|---|---|---|---|
| #21 | Ejecutar y registrar búsquedas en Scopus y Web of Science | Scopus ejecutado y registrado para los 4 ejes (`docs/research/exports/scopus/`, `docs/research/hu1-registro-busquedas.csv`). Web of Science intentado (2026-09-05) y no ejecutable: la cuenta institucional disponible permite búsqueda de perfiles de investigadores, pero no Document Search/Core Collection. La limitación quedó registrada y no impide satisfacer el criterio científico superior de HU1. | CERRAR COMO COMPLETADO CON LIMITACIÓN DOCUMENTADA |
| #22 | Ejecutar y registrar búsquedas en IEEE Xplore | IEEE Xplore ejecutado y registrado para los 4 ejes (`docs/research/exports/ieee/`, `docs/research/hu1-registro-busquedas.csv`), sin limitación pendiente. | CERRAR COMO COMPLETADO |
| #23 | Buscar antecedentes agronómicos en AGRIS, SciELO y Horticultura Argentina | Relevamiento dirigido existente en SciELO Argentina y Horticultura Argentina (`docs/research/hu1-antecedentes-argentina.md`, 3 antecedentes territoriales/agronómicos). AGRIS no pudo completarse bajo el protocolo previsto (interfaz no automatizable, ver `docs/research/hu1-registro-busquedas.csv`). No se afirma una ejecución de AGRIS que no existió. | CERRAR COMO COMPLETADO CON LIMITACIÓN DOCUMENTADA |
| #24 | Revisar documentación técnica del INTA, FAO y organismos académicos nacionales | Existe evidencia parcial de INTA y referencias técnicas relevantes, pero no se completó una revisión amplia de FAO y organismos nacionales. La búsqueda bibliográfica ya se considera cerrada y esta ampliación no es necesaria para satisfacer los criterios de aceptación de HU1. No afirmar que la tarea fue completada. | CERRAR COMO NOT_PLANNED CON LIMITACIÓN DOCUMENTADA |
| #25 | Consolidar referencias y eliminar registros duplicados | Corpus consolidado y deduplicado por DOI/título+año (`docs/research/hu1-corpus-final.csv`, 450 registros). Proceso completo, con trazabilidad de duplicados fusionados. | CERRAR COMO COMPLETADO |
| #26 | Evaluar títulos y resúmenes según los criterios definidos | Cribado semántico por título y abstract ejecutado sobre los registros incluidos automáticamente, con clasificación A/B/C y resolución posterior de la cola de revisión humana (71 casos: 29 incluir, 30 excluir, 12 indeterminado) más control final de metadatos no verificables. Los títulos y resúmenes fueron evaluados. La existencia de registros INDETERMINADOS constituye un resultado válido de la evaluación cuando la evidencia fue insuficiente y no implica que la tarea siga pendiente. | CERRAR COMO COMPLETADO |
| #27 | Analizar trabajos sobre modelado predictivo de estrés hídrico | 6 referencias representativas validadas (`docs/research/hu1-matriz-comparativa-final.md`, eje 1), con síntesis de patrones, limitaciones e implicancias de diseño. | CERRAR COMO COMPLETADO |
| #28 | Analizar trabajos sobre detección de anomalías y datos sintéticos | 5 referencias representativas de detección de anomalías (eje 2) y 9 de generación de datos sintéticos (eje 3), ambos ejes tratados de forma independiente en la matriz comparativa final, con síntesis propia de cada uno. | CERRAR COMO COMPLETADO |
| #29 | Analizar trabajos sobre retroalimentación humana y recalibración | 5 referencias representativas validadas (`docs/research/hu1-matriz-comparativa-final.md`, eje 4), con síntesis de patrones, limitaciones e implicancias de diseño. | CERRAR COMO COMPLETADO |
| #30 | Elaborar la matriz comparativa de antecedentes | `docs/research/hu1-matriz-comparativa-final.md`, con las 25 referencias representativas organizadas por eje, síntesis por eje y síntesis de vacancia. Reemplaza la matriz preliminar de 8 filas. | CERRAR COMO COMPLETADO |
| #31 | Identificar vacancias y criterios para el diseño de la arquitectura | Vacancia revalidada contra las 25 referencias (`docs/research/hu1-matriz-comparativa-final.md`, sección "Síntesis de vacancia"; `docs/research/hu1-estado-del-arte.md`, sección 4). Criterios de diseño ya incorporados en el esquema de datos de HU2 y en las especificaciones de `human-feedback`. | CERRAR COMO COMPLETADO |
| #32 | Redactar el estado del arte y el marco conceptual | `docs/research/hu1-estado-del-arte.md`, versión definitiva. | CERRAR COMO COMPLETADO |

Ningún issue se cierra en esta iteración. Este mapeo queda a disposición para la decisión de cierre correspondiente.

## Nota sobre el issue #10 (Épica 1)

Los cuatro criterios de aceptación del issue #10 quedan documentalmente satisfechos (CUMPLE en los cuatro casos). Las limitaciones metodológicas explícitas (Web of Science, AGRIS, cobertura regional acotada, registros indeterminados) quedaron registradas como parte de la caracterización honesta de una revisión bibliográfica estructurada y dirigida, no exhaustiva; ninguna de ellas constituye un incumplimiento de criterio, y la evidencia científica disponible (corpus de 450 registros, 25 referencias representativas validadas, matriz comparativa y vacancia revalidada) se considera suficiente para fundamentar las decisiones de diseño de la arquitectura. La decisión de cierre del issue #10 queda para revisión posterior; este documento no lo cierra.
