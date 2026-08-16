# Seguimiento de tareas — plan de proyecto vs. estado real del repo

Auditoría honesta del desglose de tareas técnicas del plan de tesis (sección 9 del plan de proyecto) contra lo que efectivamente existe en este repositorio a la fecha. No es autoevaluación optimista: cada tarea se marca según evidencia verificable (archivo, test, PR), no según intención.

Leyenda: ✅ Completado (cumple el criterio de aceptación de su HU) · 🟡 Parcial (hay artefacto real pero no cubre toda la tarea) · ⬜ No iniciado.

## Sprint 0 — Planificación

Ya estaba 100% completo antes de crear este repositorio: es el propio documento de planificación de tesis (acta de constitución, propósito/alcance, hipótesis, backlog, criterios de aceptación, CRISP-DM, cronograma). No cambia.

## HU1 — Estado del arte y comprensión del dominio (110 h planificadas)

| Tarea | Estado | Evidencia / motivo |
|---|---|---|
| Definir el protocolo de revisión bibliográfica | ✅ | `docs/research/hu1-protocolo-revision-bibliografica.md` define objetivo/alcance, términos, cadenas de búsqueda, criterios y procedimiento de registro. |
| Definir términos, sinónimos y cadenas de búsqueda (ES/EN) | ✅ | Mismo documento, secciones 2 y 3, con cadenas adaptadas a Scopus, Web of Science, IEEE Xplore y AGRIS/SciELO/Horticultura Argentina. |
| Definir criterios de inclusión, exclusión y período de análisis | ✅ | Mismo documento, secciones 4 y 5 (período 2019–2026 con excepción para referencias seminales). |
| Ejecutar y registrar búsquedas en Scopus y Web of Science | ⬜ | No iniciado — requiere acceso institucional a esas bases. |
| Ejecutar y registrar búsquedas en IEEE Xplore | ⬜ | No iniciado. |
| Buscar antecedentes agronómicos en AGRIS, SciELO y Horticultura Argentina | ⬜ | No iniciado. |
| Revisar documentación técnica del INTA, FAO y organismos nacionales | 🟡 | Se relevó INTA RIAN, pero como fuente de **datos** (HU2), no como antecedente bibliográfico de estrés hídrico. |
| Consolidar referencias y eliminar registros duplicados | ⬜ | No aplica todavía — no hay corpus de búsqueda sistemática. |
| Evaluar títulos y resúmenes según criterios definidos | ⬜ | No se ejecutó un protocolo de cribado; la búsqueda hecha fue dirigida y acotada, no sistemática. |
| Analizar trabajos sobre modelado predictivo de estrés hídrico | 🟡 | `docs/research/hu1-variables-y-antecedentes.md` tiene ~4 referencias verificables sobre esto, pero es una búsqueda dirigida puntual, no el análisis exhaustivo que exige la tarea. |
| Analizar trabajos sobre detección de anomalías y datos sintéticos | 🟡 | Mismo documento incluye ~5 referencias sobre anomalías/datos sintéticos en sensores agrícolas, con la misma limitación de alcance. |
| Analizar trabajos sobre retroalimentación humana y recalibración | 🟡 | `docs/research/hu1-retroalimentacion-humana.md` tiene 6 referencias verificables (HILAD, scoping review de HITL en agricultura de precisión, LLM human-in-the-loop para manejo agrícola, revisión sistemática de HITL, marco conceptual de rol del usuario, CALM), pero es búsqueda dirigida acotada, no el protocolo sistemático completo. |
| Elaborar la matriz comparativa de antecedentes | 🟡 | Existe una matriz de 8 filas en el documento de investigación, pero es un borrador preliminar, explícitamente marcado como no sustituto del protocolo sistemático. |
| Identificar vacancias y criterios para el diseño de la arquitectura | 🟡 | Se identificaron 3 vacancias y 2 criterios de diseño concretos, ya usados para el esquema de `data-ingestion` — pero acotados a lo que la búsqueda parcial permitió ver. |
| Redactar el estado del arte y el marco conceptual | 🟡 | `docs/research/hu1-estado-del-arte.md` consolida los tres ejes en un documento único (marco conceptual, síntesis comparativa, vacancias, limitaciones), pero sigue basado en búsqueda dirigida acotada, no en el protocolo sistemático (Scopus/WoS/IEEE Xplore bloqueadas). |
| Revisar trazabilidad de citas, antecedentes y decisiones metodológicas | ⬜ | No iniciado. |

**Balance HU1:** de 16 tareas, 3 completas (protocolo de revisión bibliográfica), 7 parciales (todas acotadas y explícitamente marcadas como preliminares), 6 no iniciadas. El entregable formal de HU1 (estado del arte redactado, sección 7 del plan) existe como documento (`docs/research/hu1-estado-del-arte.md`) pero **no está cumplido en su versión definitiva**, dado que se basa en búsqueda dirigida acotada y no en el protocolo sistemático. Las búsquedas en Scopus/WoS/IEEE Xplore siguen bloqueadas por falta de acceso institucional; el protocolo ya está listo para ejecutarlas en cuanto haya acceso.

## HU2 — Preparación del conjunto experimental de datos (70 h planificadas)

| Tarea | Estado | Evidencia / motivo |
|---|---|---|
| Definir variables agronómicas, climáticas y temporales requeridas | ✅ | `src/data_ingestion/schema.py` fija columnas obligatorias/opcionales, derivadas del borrador de HU1. |
| Identificar conjuntos de datos asociados a publicaciones científicas | ⬜ | No se hizo este relevamiento específico. |
| Relevar datos disponibles en SMN, NASA POWER y Copernicus | 🟡 | Documentado en `docs/research/hu2-fuentes-datos-acceso.md`; **NASA POWER** tiene conector implementado y testeado (con HTTP simulado, sin descarga real todavía); **SMN** solo identificado, sin conector; **Copernicus** bloqueado por falta de registro del responsable del proyecto. |
| Evaluar metadatos, licencias, procedencia y restricciones de uso | 🟡 | Hecho a nivel de checklist por fuente candidata, no como diccionario de datos real poblado para ninguna fuente. |
| Descargar y organizar muestras representativas de las fuentes candidatas | ⬜ | **No se ejecutó ninguna descarga real**, ni siquiera de NASA POWER (que no requiere registro) — todo lo probado usó respuestas HTTP simuladas en tests. |
| Homogeneizar formatos, unidades, frecuencias y zonas horarias | 🟡 | Mecanismo implementado (`normalize_to_schema`, `aggregation.to_daily`) y testeado con datos sintéticos de prueba, pero **no validado con datos reales de más de una fuente** — no hay evidencia de que efectivamente homogeneice fuentes distintas. |
| Analizar cobertura temporal, granularidad e integridad de las fuentes | 🟡 | `coverage.py` implementado y testeado, pero nunca corrido sobre un dataset real ingerido. |
| Definir criterios de selección y descarte de fuentes de datos | 🟡 | El checklist usa "requiere o no registro" como criterio, pero no hay criterios de calidad/relevancia agronómica explícitos todavía. |
| Implementar procedimiento reproducible de ingestión y consolidación | 🟡 | Solo existe el conector NASA POWER; no hay **consolidación multi-fuente** (el objetivo real de la tarea es combinar varias fuentes en un conjunto único). |
| Documentar diccionario de datos, procedencia y limitaciones | 🟡 | `dictionary.py` implementado y testeado con datos de ejemplo, pero **no se generó ningún diccionario real** para NASA POWER ni ninguna otra fuente. |

**Balance HU2:** de 10 tareas, 1 completa, 8 parciales, 1 no iniciada. El criterio de aceptación de HU2 ("se obtuvo un conjunto experimental apto para el desarrollo... el procedimiento puede reproducirse") **no está cumplido**: no hay todavía ni una descarga real ejecutada, ni un dataset consolidado.

## HU3 — HU8

Sin avance de código o documentación específica más allá del diseño conceptual ya cubierto por ADR-0001 (arquitectura) y la mención de HU3/HU5 en `openspec/project.md`. Estado: ⬜ no iniciado en las 4 historias (calidad/robustez de datos, modelado predictivo, retroalimentación humana, integración, evaluación experimental). Sin tareas técnicas ejecutadas de las Épicas 2, 3 y 4 (245 h planificadas entre HU3-HU8, más HU6 no contado aquí).

## Conclusión

De las **600 h** planificadas en HU1-HU8, el trabajo real ejecutado en este repositorio equivale, en el mejor de los casos, a una fracción pequeña de las **180 h** de HU1+HU2 (la mayoría de las tareas hechas son "parciales": mecanismo de código presente y testeado con datos sintéticos, pero sin ejecución sobre datos reales ni cobertura completa de la tarea). Ninguna tarea de HU3 a HU8 tiene avance.

**Riesgo identificado:** los PRs anteriores (#1-#8) pueden haber transmitido una sensación de avance más rápida de lo real, porque cada PR fue un artefacto concreto (ADR, spec, código con tests) — pero "artefacto creado" no es lo mismo que "tarea del plan de tesis completada". A partir de ahora conviene que cada PR indique explícitamente a qué tarea(s) de la sección 9 del plan corresponde y si la deja completa o parcial, para que este documento se mantenga preciso sin tener que re-auditar todo el historial.
