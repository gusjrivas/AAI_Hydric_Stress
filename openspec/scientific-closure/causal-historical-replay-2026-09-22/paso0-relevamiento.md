# PASO 0 — Relevamiento de viabilidad para reproducción histórica causal

Fecha: 2026-09-22
Alcance: exclusivamente inspección y documentación. No se implementó código, no se
entrenó ni ejecutó ningún modelo, no se abrió holdout, no se generó predicción nueva.

## A. Rama, worktree y SHA base

- Repositorio: `C:\Repo\AAI_Hydric_Stress`, remoto `origin` =
  `https://github.com/gusjrivas/AAI_Hydric_Stress.git`.
- Antes de crear la rama: rama `main`, árbol de trabajo limpio, `HEAD` = `fb34686`.
- `git fetch origin --prune` no trajo cambios: `origin/main` = `fb34686`
  (idéntico al `main` local; no había desactualización que reportar).
- Rama creada: `feat/causal-historical-replay`, desde `origin/main`, SHA base
  **`fb34686c43e180025e53c8807e05ae2a23666c7b`** (commit: "Merge pull request #210
  from gusjrivas/feat/hu6-productor-ui-renovada").
- Worktree dedicado: `C:\Repo\AAI_Hydric_Stress_causal_historical_replay`
  (no se reutilizó el checkout principal ni ninguno de los worktrees existentes;
  se verificó previamente la lista completa de worktrees para evitar colisión).
- No se usó `reset --hard`, `clean`, checkout forzado ni stash automático. No existía
  una rama o directorio previo con este nombre.

## B. Documentación y restricciones revisadas

Leídos o referenciados (ver detalle de huecos en sección G):

- `openspec/scientific-closure/README.md`
- `openspec/specs/scientific-closure/spec.md` (requisitos SC-GOV-001..025)
- `openspec/scientific-closure/operations.md`
- `openspec/scientific-closure/changes.json` (parcial, ver huecos)
- `openspec/scientific-closure/decisions.md` (vía citas de la síntesis)
- `docs/research/protocolo-experimental-v3.md` (parcial, ~150 líneas de un archivo mayor)
- `docs/research/scientific-closure-synthesis-2026-09-22.md`
- `docs/adr/0004-orquestacion-experimentos-mlflow-postgres-minio.md`
- `docs/adr/0009-contratos-temporales-y-experimentos-controlados.md`
- `openspec/specs/data-ingestion/spec.md`
- `openspec/specs/human-feedback/spec.md`

Restricciones vigentes confirmadas textualmente:

- Estado declarado del propio documento de gobernanza: **`PREPARATION_ONLY`**, que
  "no constituye autorización para A/B/C, apertura de holdout ni inicialización de
  ledger" (`openspec/scientific-closure/README.md`).
- El holdout 2024–2025 **ya fue abierto**, una única vez, de forma irreversible:
  "El holdout se abrió una única vez, de forma nominal, durable e irreversible, el
  2026-09-21T04:06:11Z... (`attempt_id 2121cdc9…`, estado `CONFIRMADA`)"
  (`docs/research/scientific-closure-synthesis-2026-09-22.md`, sección 5). Cita
  adicional: "El holdout 2024–2025 no se reabre por esta corrección ni por ninguna
  otra razón — sigue siendo una apertura única, nominal e irreversible."
- El cierre científico de `controlled_daily_v4` terminó con **no conformidad
  declarada**, no con PASS: la auditoría independiente Codex (dossier RB-05) dio
  **veredicto FAIL** sobre `88ced62` por "una contradicción cronológica en la
  secuencia de gates A→B→C" (auditoría independiente registrada *después* de que
  Etapa B ya había corrido). El cierre administrativo (decisions.md, GD-40,
  2026-09-22) aceptó "M-01/RK-20 como desviación histórica permanente e
  irreparable, sin convertirla en cumplimiento": `SC-GOV-025`, `GF` y
  `sc-06-scientific-synthesis` cierran en **FAIL**. B y C quedan reclasificados como
  "evidencia retrospectiva exploratoria", no como validación confirmatoria.
- Esto es gobernanza **vigente y restrictiva**, no un antecedente meramente
  histórico: cualquier trabajo futuro sobre `controlled_daily_v4` (incluida una
  demostración histórica) debe presentar B/C como exploratorio, y el holdout de esa
  campaña no puede reabrirse ni reutilizarse para nada, incluida una demo.
- No se infirió autorización de la mera existencia de archivos: el estado
  `PREPARATION_ONLY` se tomó como restrictivo por defecto.

## C. Inventario de artefactos con rutas verificables

| Artefacto | Ruta | Evidencia |
|---|---|---|
| Clima NASA POWER (2024/2025, 2 sitios) | `data/nasa_power_la_plata_2024.parquet`, `data/nasa_power_la_plata_2025.parquet`, `data/nasa_power_melchor_romero_2024.parquet` (+ `_coverage.csv` por archivo) | comprobada (listado de archivos) |
| Humedad de suelo ESA CCI | `data/esa_cci_soil_moisture_melchor_romero_2024.parquet` + `_coverage.csv` | comprobada |
| Dataset consolidado multi-fuente | `data/melchor_romero_2024_consolidado.parquet` + `_coverage.csv` | comprobada |
| Diccionarios de datos versionados | `data/dictionaries/*.json` (4 archivos) | comprobada |
| Feedback + predicción (demo) | `data/feedback_ui.parquet`, `data/feedback__demo-*.parquet` (6), `data/sensor__demo-*.parquet` (6), `demo_sessions/demo-*/manifest.json` (6) | comprobada la existencia; **contenido interno de los `.parquet` no inspeccionado** (inferencia pendiente de confirmar sobre columnas exactas) |
| MLflow tracking (local) | `backend/mlruns/`, `mlruns/` (raíz) | comprobada |
| MLflow tracking (arquitectura real: Postgres+MinIO+servidor Docker) | `docs/adr/0004-orquestacion-experimentos-mlflow-postgres-minio.md` | comprobada (ADR) |
| Reporte de síntesis científica v4 (resultados sustantivos) | `docs/research/scientific-closure-synthesis-2026-09-22.md` | comprobada |
| Protocolo v3 | `docs/research/protocolo-experimental-v3.md` | comprobada (lectura parcial) |
| Protocolo v4 | `docs/research/controlled-daily-v4-external-pergamino-protocol.md` | existencia comprobada, contenido no releído en detalle |
| Esquema/persistencia de feedback | `src/human_feedback/schema.py`, `registry.py`, `recalibration.py` | comprobada |
| Endpoint de linaje | `backend/app/routers/lineage.py` | comprobada (leído completo) |
| Endpoint de forecast | `backend/app/routers/forecast.py` | comprobada (leído completo) |
| Etiquetado de estrés hídrico | `src/predictive_modeling/labeling.py` | comprobada (leído completo) |
| Tests de causalidad/imputación | `tests/test_imputation.py`, `tests/test_pipeline.py` | comprobada (nombres y aserciones citados) |

Para cada artefacto de predicción/feedback, los campos de procedencia temporal
confirmados en código (no en datos) son: `model_version`, `target_timestamp`,
`y_proba`, `target_threshold`, `validated_at`, y en el linaje además
`dataset_sha256`, `mlflow_model_version`, `trained_through` (frontera monótona).

Horizontes +1/+2/+3: **no confirmados explícitamente** en el código relevado en esta
pasada (el protocolo v3 describe el objetivo como `t+3 días`, umbral único; no se
verificó si el sistema operativo expone también +1/+2 en el mismo contrato). Dato
ausente de esta pasada, no descartado.

Clasificación científica y restricciones de uso del `controlled_daily_v4`:
B (Etapa 2023) y C (holdout 2024–2025) — **evidencia retrospectiva exploratoria**,
no confirmatoria (ver sección B). El holdout de esa campaña está cerrado e
irreversible; no reutilizable.

## D. Matriz de causalidad

| Requisito | Evidencia | Estado | Limitación |
|---|---|---|---|
| Imputación nunca usa valor futuro | `src/data_quality/imputation.py::interpolate_missing_causal`, 7 tests en `tests/test_imputation.py` (p.ej. `test_interpolate_missing_causal_never_uses_a_later_value_within_the_same_partition`) | Comprobada | ninguna detectada en esta pasada |
| Normalización/escalado ajustado solo con train | `tests/test_pipeline.py::test_pipeline_does_not_leak_test_statistics_into_scaling`; v3: "las escalas se ajustan con entrenamiento limpio, nunca con test" | Comprobada | no se releyó el código de escalado en sí |
| Umbral de etiqueta calculado solo sobre train | `src/predictive_modeling/labeling.py::fit_stress_threshold` | Comprobada, con nota histórica: el código documenta una fuga temporal ya corregida ("el umbral anterior se calculaba sobre el DataFrame completo, antes de la partición") | corrección referenciada en comentario de código, no se ubicó el ADR/registro formal exacto en esta pasada |
| Selección de modelo/hiperparámetros sin usar holdout | SC-GOV-014 ("jamás seleccionar con holdout"); v3: 20% cronológico inicial de train reservado como calibración previa a folds | Comprobada a nivel de spec/protocolo | no se verificó el código de selección de hiperparámetros directamente |
| Uso del holdout | Apertura única confirmada, `attempt_id 2121cdc9…`, `CONFIRMADA`, irreversible | Comprobada y **cerrada** | cualquier reutilización para esta demo estaría prohibida por gobernanza vigente |
| Fecha de disponibilidad vs fecha de medición (datos crudos de entrada) | v3 declara el supuesto ("la emisión supone que las observaciones diarias ya están disponibles"); no se halló campo tipo `ingested_at`/`available_at` en `data-ingestion/spec.md` ni en el código de ingesta relevado | **No confirmado / probable ausencia** | supuesto documentado, no mecanismo verificable por fila; requiere confirmación adicional antes de afirmar causalidad estricta de los insumos |
| Fecha objetivo vs fecha de validación del feedback | `human_feedback` spec: "Feedback aún no maduro no puede incorporarse... GIVEN una corrección cuya fecha objetivo todavía no ha madurado..." + campos `target_timestamp`/`validated_at` | Comprobada | ninguna detectada |
| Linaje modelo↔dataset↔recalibración | `backend/app/routers/lineage.py`: `dataset_sha256`, `mlflow_model_version`, `trained_through`, `source_trained_through`/`successor_trained_through` | Comprobada | no se verificó si el hash cubre también los insumos de predicción individual, o solo el dataset de entrenamiento del modelo |
| Traducción "humedad" → "riesgo de estrés hídrico" | `src/predictive_modeling/labeling.py` docstring: umbral es "percentil de la distribución histórica... no un umbral agronómico absoluto... no calibrado todavía por falta de datos de suelo específicos" | Comprobada (y es una **limitación reconocida por el propio código**, no un criterio validado) | no existe ADR/spec que certifique la equivalencia humedad↔riesgo agronómico; el propio sistema la declara como proxy relativo |

## E. Componentes reutilizables

- `backend/app/routers/forecast.py`: emite predicción, es inmutable por
  sensor/día ("Re-running does not replace the prediction a human has already
  reviewed"), fusiona con feedback existente sin sobrescribir validaciones previas.
- `backend/app/routers/lineage.py`: expone linaje completo de recalibraciones vía
  `GET /lineage/{sensor_id}`, solo lectura — reutilizable tal cual para consultar
  qué modelo/dataset produjo una predicción histórica dada.
- `src/human_feedback/{schema,registry,recalibration}.py`: contrato de feedback
  con `target_timestamp` separado de `validated_at`, reutilizable para vincular
  observación posterior a predicción.
- Limitación transversal: ninguno de estos componentes fue diseñado explícitamente
  para "reproducir" un recorrido histórico completo con fines demostrativos; son
  el sustrato operativo del sistema en producción/demo, no un modo de replay.

## F. Períodos candidatos

Un candidato preliminar, **no confirmado en profundidad**, son las sesiones de
demo bajo `demo_sessions/demo-*/manifest.json` con sus pares
`data/sensor__demo-*.parquet` / `data/feedback__demo-*.parquet` (6 sesiones): estas
sí exponen el ciclo predicción→feedback en artefactos separados y con metadata de
manifiesto. No se inspeccionó el contenido de esos parquet ni de los manifiestos
para confirmar que cubren fecha histórica real con datos reales (podrían ser datos
sintéticos de demo — el propio nombre `demo_sessions` es una señal de alerta que
requiere verificación antes de usarlos como evidencia real).

El dataset `melchor_romero_2024_consolidado.parquet` (real, multi-fuente,
diccionario versionado) es un candidato más creíble como *fuente de datos*, pero no
hay evidencia todavía de que exista un pronóstico histórico archivado y su
observación posterior ya vinculados sobre exactamente ese dataset fuera del ciclo
de `controlled_daily_v4` (cuyo holdout está cerrado y restringido).

No se puede, con lo relevado, justificar un período candidato único y completo sin
verificación adicional de contenido de datos (ver sección G).

## G. Faltantes y bloqueos

**Implementación pendiente** (no existe hoy, requeriría diseño/código nuevo):
- Ningún componente actual arma explícitamente el recorrido completo "fecha
  histórica → info disponible al corte → predicción → avance temporal →
  observación → feedback separado" como una vista/demo unificada; hoy son piezas
  separadas (forecast, feedback, lineage) sin una capa de "replay".
- No se confirmó un mecanismo de "fecha de disponibilidad del dato crudo" distinto
  de su fecha de medición en la ingesta — si se requiere causalidad estricta de
  insumos (no solo de target/feedback), esto probablemente debe construirse o
  documentarse explícitamente.

**Evidencia ausente** (no verificada en esta pasada, puede o no existir):
- Contenido real de los `.parquet` de datasets y de demo (esquema exacto de
  columnas, si existen +1/+2/+3, si `demo_sessions` usa datos reales o sintéticos).
- Lectura completa de `protocolo-experimental-v3.md` (cortada en ~150 líneas) y de
  `controlled-daily-v4-external-pergamino-protocol.md`.
- `openspec/scientific-closure/changes.json` completo (sc-05 a sc-10 no
  confirmados).
- Informes de auditoría RB-05 (`review-audit-codex-round1-FAIL.md`),
  `reconciliation-2026-09-22/`, `sufficiency-review-2026-09-22/`.
- Contenido de `backend/app/routers/{feedback,recalibration,models,producer_v2,
  quality,sensors}.py` y de `frontend/src/features/forecast`.

**Restricción científica o de gobernanza** (bloqueos activos, no evidencia
faltante):
- El holdout de `controlled_daily_v4` (2024–2025) está cerrado de forma
  irreversible; no puede reabrirse ni reutilizarse, tampoco con fines
  demostrativos.
- B y C de `controlled_daily_v4` deben presentarse siempre como "evidencia
  retrospectiva exploratoria", nunca como validación confirmatoria, por el FAIL de
  auditoría RB-05 y el cierre con no conformidad declarada.
- El estado de gobernanza vigente es `PREPARATION_ONLY`: esto por sí solo no
  bloquea una demostración histórica *fuera* de `controlled_daily_v4` (p. ej. sobre
  datos ya observados, sin tocar A/B/C/H de esa campaña), pero sí bloquea cualquier
  intento de usarla para reabrir o suplementar esa campaña específica.

## H. Impacto potencial

- Hipótesis, propósito, alcance y arquitectura del Trabajo Final: **sin impacto
  identificado** por este relevamiento; no se propone ningún cambio de alcance.
- Riesgo principal si se avanza sin más verificación: presentar B/C de
  `controlled_daily_v4` (o datos de `demo_sessions`) como si fueran una
  demostración causal confirmatoria, cuando la gobernanza vigente exige tratarlos
  como exploratorios o, en el caso del holdout, prohíbe tocarlos.
- Riesgo secundario: si `demo_sessions` usa datos sintéticos, un recorrido
  histórico construido sobre esos datos no cumpliría el requisito explícito de
  "datos reales" del pedido original.
- Cronograma/entregables: este informe no modifica el plan aprobado; solo aporta
  insumo para decidir si el Paso 1 es viable y bajo qué condiciones.

## I. Recomendación para el Paso 1

Antes de redactar el Paso 1, se recomienda cerrar los huecos de mayor impacto en
este orden: (1) confirmar si `demo_sessions/*` usa datos reales o sintéticos
inspeccionando manifiestos y contenido de parquet; (2) confirmar el esquema exacto
de `data/feedback_ui.parquet` (¿expone target_timestamp, model_version, horizonte,
y observación posterior en el mismo registro?); (3) leer completo
`protocolo-experimental-v3.md` y el protocolo v4 para fijar con precisión qué
período, fuera del holdout cerrado de `controlled_daily_v4`, podría usarse sin
tocar gobernanza restringida; (4) decidir explícitamente con el responsable
científico si el Paso 1 se apoya en `melchor_romero_2024_consolidado.parquet` (dato
real, sin ciclo de predicción archivado) o en el ciclo predicción+feedback ya
existente (con menor certeza sobre representatividad de "datos reales" si proviene
de `demo_sessions`).

## Veredicto

**VIABILIDAD CONDICIONADA.**

Existen candidatos de datos reales (`melchor_romero_2024_consolidado.parquet` y
componentes de predicción/feedback/linaje con procedencia temporal parcial), y la
gobernanza vigente no prohíbe per se una demostración histórica fuera de
`controlled_daily_v4`. Pero faltan comprobaciones concretas (contenido real de
datos, confirmación de horizontes, esquema exacto de feedback) y condiciones
explícitas (evitar tocar el holdout cerrado, presentar cualquier resultado de
`controlled_daily_v4` como exploratorio, confirmar si `demo_sessions` es dato real).
Este veredicto se refiere solo a la viabilidad de la demostración histórica; no
constituye una nueva aprobación científica del trabajo, ni valida ni invalida el
estado de cierre de `controlled_daily_v4`.

## Cierre

Diff de esta tarea: exclusivamente este archivo nuevo
(`openspec/scientific-closure/causal-historical-replay-2026-09-22/paso0-relevamiento.md`)
en la rama `feat/causal-historical-replay`. No se modificó ningún archivo
existente, no se ejecutó entrenamiento/inferencia, no se tocó A/B/C/H, no se hizo
push, PR ni merge. Se detiene aquí para revisión antes de cualquier Paso 1.
