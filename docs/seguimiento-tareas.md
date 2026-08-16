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
| Buscar antecedentes agronómicos en AGRIS, SciELO y Horticultura Argentina | 🟡 | `docs/research/hu1-antecedentes-argentina.md` releva 4 antecedentes verificables en SciELO Argentina, Horticultura Argentina e INTA, pero AGRIS todavía no se consultó mediante su interfaz de búsqueda sistemática. |
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

**Balance HU1:** de 16 tareas, 3 completas (protocolo de revisión bibliográfica), 8 parciales (todas acotadas y explícitamente marcadas como preliminares), 5 no iniciadas. El entregable formal de HU1 (estado del arte redactado, sección 7 del plan) existe como documento (`docs/research/hu1-estado-del-arte.md`) pero **no está cumplido en su versión definitiva**, dado que se basa en búsqueda dirigida acotada y no en el protocolo sistemático. Las búsquedas en Scopus/WoS/IEEE Xplore siguen bloqueadas por falta de acceso institucional; el protocolo ya está listo para ejecutarlas en cuanto haya acceso.

## HU2 — Preparación del conjunto experimental de datos (70 h planificadas)

| Tarea | Estado | Evidencia / motivo |
|---|---|---|
| Definir variables agronómicas, climáticas y temporales requeridas | ✅ | `src/data_ingestion/schema.py` fija columnas obligatorias/opcionales, derivadas del borrador de HU1. |
| Identificar conjuntos de datos asociados a publicaciones científicas | ⬜ | No se hizo este relevamiento específico. |
| Relevar datos disponibles en SMN, NASA POWER y Copernicus | 🟡 | Documentado en `docs/research/hu2-fuentes-datos-acceso.md`; **NASA POWER** tiene conector implementado, testeado y ahora **con descarga real ejecutada** (365 días, La Plata, 2025); **SMN** relevado en profundidad y encontrado **bloqueado por acceso técnico** (dataset de datos.gob.ar removido, `smn.gob.ar/descarga-de-datos` con protección anti-bot — no es solo falta de registro, ver checklist); **Copernicus** bloqueado por falta de registro del responsable del proyecto. |
| Evaluar metadatos, licencias, procedencia y restricciones de uso | 🟡 | Existe un diccionario de datos real poblado para NASA POWER (`data/dictionaries/nasa_power_la_plata_2025.json`, con licencia y limitaciones reales, no de ejemplo), pero SMN y Copernicus siguen solo a nivel de checklist. |
| Descargar y organizar muestras representativas de las fuentes candidatas | 🟡 | **Primera descarga real ejecutada**: NASA POWER, La Plata (-34.92, -57.95), 2025-01-01 a 2025-12-31, vía `scripts/ingest_nasa_power.py`, guardada en `data/nasa_power_la_plata_2025.parquet` (365 filas, `origen: real`). Falta repetir para al menos una fuente adicional (SMN) para que "fuentes candidatas" (plural) esté cubierto. |
| Homogeneizar formatos, unidades, frecuencias y zonas horarias | 🟡 | Mecanismo implementado (`normalize_to_schema`, `aggregation.to_daily`) y ahora ejercitado con datos reales de NASA POWER (no solo sintéticos), pero **todavía no validado con más de una fuente real** — no hay evidencia de que homogeneice fuentes distintas entre sí. |
| Analizar cobertura temporal, granularidad e integridad de las fuentes | 🟡 | `coverage.py` corrido sobre el dataset real de NASA POWER: 100% de completitud en las 5 variables climáticas obligatorias que la fuente provee, 0% en humedad de suelo/ET0 (esperado, no las provee). Falta correrlo sobre una segunda fuente real para comparar cobertura entre fuentes. |
| Definir criterios de selección y descarte de fuentes de datos | 🟡 | El checklist usa "requiere o no registro" como criterio, pero no hay criterios de calidad/relevancia agronómica explícitos todavía. |
| Implementar procedimiento reproducible de ingestión y consolidación | 🟡 | `src/data_ingestion/ingest.py` (`run_ingestion`) + `scripts/ingest_nasa_power.py` implementan un procedimiento reproducible de extremo a extremo (descarga → guardado → cobertura → diccionario) para una fuente, testeado con inyección de dependencias y ejecutado realmente. Sigue faltando la **consolidación multi-fuente** (combinar varias fuentes en un conjunto único), que es el objetivo pleno de la tarea. |
| Documentar diccionario de datos, procedencia y limitaciones | 🟡 | Se generó el primer diccionario de datos real (NASA POWER, licencia y limitaciones reales, no de ejemplo). Falta para SMN/Copernicus y para cualquier fuente adicional que se incorpore. |

**Balance HU2:** de 10 tareas, 1 completa, 9 parciales, 0 no iniciadas. El criterio de aceptación de HU2 ("se obtuvo un conjunto experimental apto para el desarrollo... el procedimiento puede reproducirse") **sigue sin cumplirse en su totalidad**: ya hay una descarga real y un procedimiento reproducible para NASA POWER, pero falta la consolidación multi-fuente (al menos una segunda fuente real, ej. SMN) para tener un conjunto experimental combinado.

## HU3 — HU8

Sin avance de código o documentación específica más allá del diseño conceptual ya cubierto por ADR-0001 (arquitectura) y la mención de HU3/HU5 en `openspec/project.md`. Estado: ⬜ no iniciado en las 4 historias (calidad/robustez de datos, modelado predictivo, retroalimentación humana, integración, evaluación experimental). Sin tareas técnicas ejecutadas de las Épicas 2, 3 y 4 (245 h planificadas entre HU3-HU8, más HU6 no contado aquí).

## Infraestructura de desarrollo (ADR-0003)

Esta sección no corresponde a una tarea del backlog de tesis (HU1-HU8), sino a infraestructura de ciclo de vida de desarrollo decidida en `docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md`. Se registra igual porque el diff que la introduce toca `src/` (reformateo con Black) y por eso queda alcanzado por la regla de trazabilidad que este mismo documento exige para cualquier PR.

| Tarea | Estado | Evidencia / motivo |
|---|---|---|
| Definir stack backend/frontend y gobernanza del ciclo de vida (ADR) | ✅ | `docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md`, aceptado 2026-08-16. |
| Integración continua (lint + formato + tests) | ✅ | `.github/workflows/ci.yml` corre `ruff check`, `black --check` y `pytest` sobre `src/`/`tests/` en cada PR contra `main`; `ruff` y `black` agregados como dependencias de desarrollo en `pyproject.toml`. |
| Formatear el código Python existente con Black | ✅ | Reformateo aplicado a `src/data_ingestion/aggregation.py` y `src/data_ingestion/schema.py` (Task 1 del plan de implementación); `black --check src tests` pasa limpio. |
| Hook de trazabilidad OpenSpec/ADR/seguimiento en `gh pr create` | ✅ | `.claude/hooks/check-pr-traceability.sh` (script) y `.claude/settings.json` (wiring del hook `PreToolUse`) bloquean la apertura de un PR que no referencie una HU/change de OpenSpec, o que toque `src/`/`docs/research/` sin actualizar este mismo documento; incluye bypass explícito vía `SKIP_PR_TRACEABILITY=1` para el caso de PR fuera de ese esquema. |

**Balance:** las 4 piezas de ADR-0003 quedan implementadas y verificadas (CI corriendo localmente en verde, hook con pipe-tests, bypass probado). Pendiente fuera del alcance de esta rama: confirmar en un PR real que el check `python-quality` aparece en GitHub (requiere push real, ver "Verificación final" del plan de implementación).

## Infraestructura de ML (ADR-0004)

Tampoco corresponde a una tarea del backlog de tesis (HU1-HU8): es infraestructura de orquestación de experimentos decidida en `docs/adr/0004-orquestacion-experimentos-mlflow-minio.md`, que reemplaza la decisión de "MLflow local sin servidor" de ADR-0002. Se registra por trazabilidad, aunque el diff no toca `src/` ni `docs/research/` (no activa la regla 2 del hook).

| Tarea | Estado | Evidencia / motivo |
|---|---|---|
| Definir orquestación de experimentos (servidor MLflow + backend Postgres + artefactos MinIO) | ✅ | `docs/adr/0004-orquestacion-experimentos-mlflow-minio.md`, aceptado 2026-08-16. Reemplaza la sección correspondiente de ADR-0002 (marcada ahí como superseded). |
| Levantar y verificar el stack de punta a punta | ✅ | `docker-compose.yml` + `docker/mlflow/Dockerfile` probados con `docker compose up -d --build`: los 3 servicios (`postgres`, `minio`, `mlflow`) quedan saludables; se registró un run de prueba real (parámetro, métrica y artefacto) y se confirmó el artefacto físicamente en MinIO vía `mc ls`. Sin código de modelado real todavía (HU3/HU4 no iniciadas) — la verificación fue un experimento de humo, no una corrida de un modelo real. |

**Balance:** infraestructura implementada y verificada de punta a punta con un experimento de prueba. Ningún código de HU3/HU4 depende de esto todavía porque esas historias no arrancaron; queda listo para cuando lo hagan. Docker Desktop pasa a ser un prerequisito de desarrollo desde ahora (ver "Consecuencias" del ADR).

## Conclusión

De las **600 h** planificadas en HU1-HU8, el trabajo real ejecutado en este repositorio equivale, en el mejor de los casos, a una fracción pequeña de las **180 h** de HU1+HU2 (la mayoría de las tareas hechas son "parciales": mecanismo de código presente y testeado, con una primera ejecución real sobre datos de NASA POWER, pero sin cobertura multi-fuente ni cobertura completa de la tarea). Ninguna tarea de HU3 a HU8 tiene avance.

**Riesgo identificado:** los PRs anteriores (#1-#8) pueden haber transmitido una sensación de avance más rápida de lo real, porque cada PR fue un artefacto concreto (ADR, spec, código con tests) — pero "artefacto creado" no es lo mismo que "tarea del plan de tesis completada". A partir de ahora conviene que cada PR indique explícitamente a qué tarea(s) de la sección 9 del plan corresponde y si la deja completa o parcial, para que este documento se mantenga preciso sin tener que re-auditar todo el historial.
