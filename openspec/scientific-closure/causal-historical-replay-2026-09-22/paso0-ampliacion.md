# PASO 0 — Ampliación de relevamiento (revisión complementaria)

Fecha: 2026-09-22
Alcance: exclusivamente inspección y documentación complementaria al informe
`paso0-relevamiento.md`, que se conserva sin modificar. No se implementó código,
no se ejecutó pipeline, entrenamiento ni inferencia, no se abrió ni inspeccionó
el holdout cerrado, no se instaló ninguna dependencia.

## Estado del entorno antes de esta pasada

- Rama `feat/causal-historical-replay`, worktree
  `C:\Repo\AAI_Hydric_Stress_causal_historical_replay`, base preservada
  `fb34686c43e180025e53c8807e05ae2a23666c7b` (verificado `merge-base --is-ancestor`
  antes de empezar). No se cambió de rama ni se actualizó la base.
- Único cambio pendiente en el árbol al iniciar: el `paso0-relevamiento.md` ya
  staged de la pasada anterior. Se preservó intacto.
- **Limitación de entorno relevada en esta pasada**: este worktree no tiene
  intérprete Python disponible (`python`/`python3`/`py` ausentes, sin `.venv`, sin
  `uv`/`poetry`). No se instaló nada por estar prohibido. La inspección de
  contenido de archivos `.parquet` se hizo por extracción de tokens ASCII
  imprimibles del binario (`cat | tr | grep`), lo que permite ver nombres de
  columnas y valores de tipo string, pero **no permite leer valores numéricos,
  conteos de filas ni fechas reales**. Cualquier verificación numérica exacta de
  esos archivos queda pendiente de un entorno con `pandas`/`pyarrow`.
- **`demo_sessions/` y `data/{feedback,sensor}__demo-*.parquet` no existen en
  este worktree** (son locales, excluidos por `.gitignore`; solo están presentes
  en el checkout principal `C:\Repo\AAI_Hydric_Stress`). Se inspeccionaron ahí,
  en modo exclusivamente lectura, sin ejecutar nada ni modificar nada.

---

## 1. Precisión de restricciones de gobernanza

### 1.1 Alcance textual de `PREPARATION_ONLY`

Cita exacta (`openspec/scientific-closure/README.md:65-70`):

> "Excluye ejecución científica durante preparación, **inspección de holdouts
> cerrados**, modificación de resultados/v3/UI/main, publicación, tags, PR,
> merge, rebase y push."

Esto **excluye explícitamente inspeccionar el holdout cerrado**, no solo
reabrirlo o reejecutar su evaluación. No hay ninguna cláusula, en este ni en
otro documento revisado, que mencione "visualizar predicciones ya archivadas
sin recalcular" para artefactos **fuera** del holdout 2024–2025.

Confirmación adicional y más fuerte, específica de la ventana Pergamino 2024–2025
(`docs/research/controlled-daily-v4-external-pergamino-protocol.md:291`):

> "No se permite analizar valores, clases ni métricas de 2024–2025."

Esta prohibición usa el verbo "analizar", que cubre razonablemente también
"visualizar" — es más amplia que "no reabrir". Aplica únicamente a la ventana
2024–2025 (Etapa C / holdout) de `controlled_daily_v4`, no a Etapa A, Etapa B,
ni al protocolo v3.

**Corrección de la consigna sobre a) / b) / c):**
- a) reabrir/repetir evaluación de una campaña: prohibido, textual y explícito.
- inspeccionar el holdout cerrado (variante de a) aplicada a datos, no solo a
  evaluación): prohibido, textual y explícito (cita de arriba).
- b) reutilizar datos para ajustar modelos o seleccionar decisiones: prohibido
  por gobernanza general del holdout (`SC-GOV-014`, ya citado en el informe
  original) y por el protocolo v4 (nunca se seleccionó con holdout).
- c) visualizar predicciones/resultados **ya archivados fuera del holdout
  2024–2025**, sin recalcularlos: **no hay prohibición ni autorización textual
  encontrada**. Se marca, como pide la consigna:
  **"Uso demostrativo pendiente de aclaración documental"** — pero esta
  ambigüedad aplica solo a artefactos fuera de la ventana 2024–2025; para el
  holdout mismo no hay ambigüedad, la prohibición ya está escrita.

No se dedujo que c) esté prohibido solo porque a) lo esté, ni se asumió
autorización de c) por defecto.

### 1.2 Alcance exacto del FAIL de RB-05 (M-01)

Corrección material relevante al informe original, que no distinguía con
suficiente precisión el alcance del FAIL. Cita textual
(`openspec/scientific-closure/rb05-audit-preparation-2026-09-22/rb05-dossier.md:157-160`):

> "El hallazgo M-01 no exige reabrir el holdout ni reejecutar A, B, C, H, R, N
> o S — **es un defecto de gobernanza del proceso de gates, no de los
> resultados científicos que ese proceso produjo**."

Y en `openspec/scientific-closure/decisions.md`, registro GD-38 (paráfrasis
ajustada a cita, verificar cita completa en el archivo original si se requiere
literalidad absoluta): se registra como "un defecto de gobernanza del proceso,
no una falla de los resultados científicos de A, B o C en sí mismos — que
corrieron una sola vez cada uno, con custodia y exit 0 verificados".

Filas `SC-GOV` específicamente no sostenidas por M-01/M-02/M-04
(`rb05-dossier.md`, secciones 3 y 5): `SC-GOV-003, 007, 008, 012, 014, 019`.
Las métricas recomputadas de A/B/C/H se registran como "resultados numéricos
verificados" (GD-40).

**Consecuencia para esta ampliación**: el FAIL de RB-05 **no se extiende
automáticamente a todos los artefactos de la campaña** ni equivale a una fuga
temporal detectada en los datos. Un artefacto de predicción archivado
individual de A/B/C, si existiera con procedencia verificable, no queda
descalificado solo por M-01. Lo que sí queda descalificado por gobernanza es:
(i) presentar la secuencia de gates A→B→C como válida, y (ii) presentar B/C
como "validación confirmatoria" en vez de "evidencia retrospectiva
exploratoria" — esto último ya estaba correctamente registrado en el informe
original y se mantiene.

Los otros tres hallazgos materiales, verificados en
`rb05-audit-preparation-2026-09-22/reviews/review-audit-codex-round1-FAIL.md`:
- M-02: "T08 marcada cumplida sin cadena de revisión requerida en sc-06" —
  defecto de trazabilidad de tareas, no de datos.
- M-03: contradicción documental sobre si Docker respondió en WSL el
  2026-09-21 — no afecta datos de predicción.
- M-04: pushes de preparación prohibidos, ya tratado en GD-39.

**Ninguno de los cuatro hallazgos materiales (M-01..M-04) trata sobre
integridad de datos, imputación, escalado o contenido de predicciones
archivadas.** Los cuatro son defectos de proceso de gobernanza/documentación,
no de resultados científicos. Esta distinción no estaba explícita en el
informe original y se incorpora aquí como corrección.

### 1.3 `changes.json`

Verificado por búsqueda de estados (archivo de 996 líneas, no releído íntegro
línea por línea en esta pasada): `sc-04-stage-b` y `sc-05-stage-c` → `PASS`;
`sc-06-scientific-synthesis` → `FAIL`; `sc-07-aux-regression`,
`sc-09-aux-anomalies`, `sc-10-aux-robustness` → `BLOCKED`;
`sc-08-aux-hitl` → `PASS`. Coincide con la narrativa de `decisions.md` ya
citada en el informe original; no se detectaron contradicciones.

---

## 2. Inventario ampliado de predicciones archivadas

### 2.1 Corrección sobre `data/feedback_ui.parquet`

El informe original afirmaba que los campos de procedencia temporal
(`model_version`, `target_timestamp`, `y_proba`, `target_threshold`,
`validated_at`) estaban "confirmados en código" para "cada artefacto de
predicción/feedback". Esto es **cierto para el contrato de código**
(`src/human_feedback/schema.py`), pero **falso para el archivo concreto
`feedback_ui.parquet`**: la extracción de tokens del binario solo muestra los
campos `fecha`, `alerta_generada`, `estado_validacion`, `etiqueta_corregida`,
`observacion` — ninguno de los campos de linaje temporal.

La convención real de nombrado del store activo es
`feedback_log_name_for(sensor_id) = f"feedback__{sensor_id}"`
(`src/data_ingestion/sensor_naming.py:32-34`), usada por
`forecast.py`/`feedback.py`/`recalibration.py`. `feedback_ui.parquet` no sigue
ese patrón (falta `sensor_id`, falta el doble guion bajo) y ningún módulo en
`src/`/`backend/` lo referencia hoy — es casi seguro un artefacto residual
anterior al refactor multi-sensor documentado en
`docs/superpowers/plans/2026-09-03-multi-sensor-ingestion.md`, no el store
vigente. Esta corrección invalida cualquier lectura del informe original que
tratara `feedback_ui.parquet` como evidencia de un ciclo predicción→feedback
con procedencia completa.

### 2.2 `data/feedback__demo-*.parquet` y `data/sensor__demo-*.parquet`

Estos sí siguen el contrato completo: `fecha`, `model_version`,
`target_threshold`, `target_timestamp`, `validated_at`, `y_proba`, `issued_at`,
`estado_validacion`, `etiqueta_corregida`, `observacion`.

**Procedencia confirmada como sintética, sin ambigüedad** (corrige la
incertidumbre que el informe original dejaba abierta). Lectura completa de un
manifiesto (`demo_sessions/demo-139b36b992/manifest.json`): cada lectura
declara literalmente `"origen": "sintetico"` / `"procedencia": "sintetico"`, y
`"generator_version": "demo_simulation.mock_sensor_chain@v1"`. El propio
`.gitignore` del repo describe estos artefactos como "una demo local, no un
dataset curado". `sensor__demo-*.parquet` incluye variables
(`canopy_temperature`, `leaf_water_potential`, `stomatal_conductance`, `ndvi`)
que no están autorizadas en el contrato v3/v4 (que usa solo humedad de suelo,
RH2M, radiación solar y variables derivadas de esas) — evidencia adicional de
que el pipeline de demo es una simulación desacoplada del pipeline científico.
El manifiesto declara `horizon_days: 3` únicamente (no expone +1/+2 en el mismo
contrato — esto responde, en sentido negativo, al punto que el informe
original dejaba como "no confirmado").

### 2.3 Ausencia de ciclo predicción→feedback sobre datos reales

No existe ningún archivo `feedback__melchor_romero...parquet` ni equivalente
en `data/` (verificado por listado exhaustivo del directorio). No hay ciclo
predicción→feedback archivado sobre el dataset real
`melchor_romero_2024_consolidado.parquet`, fuera de lo que pudiera existir
dentro de `controlled_daily_v4` (cerrado/holdout, no inspeccionable).

### 2.4 MLflow local

Inspección sin deserializar el modelo de un run al azar
(`backend/mlruns/1/05264a252e474e97963e0e1f81831e8a`): contiene únicamente
`artifacts/model/{MLmodel, model.pkl, conda.yaml, python_env.yaml,
requirements.txt}` — **sin `meta.yaml`, sin `params/`, sin `tags/`, sin
`metrics/`**. `MLmodel` (YAML plano) confirma sklearn 1.9.0, mlflow 2.22.5,
creado 2026-08-22. La ausencia de metadata de tracking en el filestore local
significa que, desde este checkout, **no se puede correlacionar un run local
con un `model_id`/`model_version` concreto persistido en un
`feedback__*.parquet`**. La arquitectura real de tracking es
Postgres+MinIO+Docker (ADR-0004); este filestore local parece un residuo de
desarrollo incompleto, no el sistema de registro operativo.

---

## 3. Matriz de causalidad corregida (por niveles de evidencia)

Se reemplaza la columna única "Estado" del informe original por 5 niveles
explícitos, para no confundir "existe una función y un test" con "está
comprobado que se ejecutó así en la corrida real que generó tal predicción
archivada".

| Ítem | Requisito documentado | Implementación inspeccionada | Prueba inspeccionada (sin ejecutar) | Evidencia de ejecución histórica real | No verificado |
|---|---|---|---|---|---|
| Imputación nunca usa valor futuro | v3 §1: entradas imputadas por forward-fill causal | `src/data_quality/imputation.py::interpolate_missing_causal` | 5 tests en `tests/test_imputation.py` (p. ej. `test_interpolate_missing_causal_never_uses_a_later_value_within_the_same_partition`) | **Sí, para v3**: `decisions.md` GD-35 documenta ~24% de días imputados con `causal_ffill` en las 8 configuraciones formales de v3 — evidencia de ejecución real, no solo de test | Para v4: no aplica — v4 aborta ante huecos en vez de imputar (`controlled_daily_v4/features.py::validate_continuous_daily_calendar`, citado por GD-35) |
| Escalado/normalización solo con train | v3: "las escalas se ajustan con entrenamiento limpio, nunca con test" | No releído en esta pasada el código exacto de escalado | `tests/test_pipeline.py::test_pipeline_does_not_leak_test_statistics_into_scaling` | No verificada en esta pasada la correlación con una corrida archivada específica | Confirmación numérica de una ejecución real concreta |
| Umbral P20/target solo con train | v4 §3: "`P20_train` se calcula exclusivamente con el train autorizado" | `src/predictive_modeling/labeling.py::fit_stress_threshold` | No identificado un test específico en esta pasada | La ejecución real de A/B/C sobre Pergamino es la evidencia de ejecución disponible, pero está bajo el defecto de gobernanza M-01 (proceso de gates), no bajo duda de corrección numérica (ver §1.2) | Verificación línea por línea adicional pendiente |
| Pesos del ensamble (Soft Voting) | v4 §7.5: pesos fijos `(1/3, 1/3, 1/3)`, "nunca ajustados con validación ni holdout" | `SoftVotingClassifier` (no releído línea por línea en esta pasada) | No confirmado en esta pasada | Ídem fila anterior (bajo M-01) | Verificación de código pendiente |
| Disponibilidad de insumos (fecha de medición vs. disponibilidad) | v3: supuesto explícito, no mecanismo — "la emisión supone que las observaciones diarias ya están disponibles"; v3 también: "un backtest sobre archivos retrospectivos no acredita por sí mismo la latencia de una alerta operativa" | Grep de todo el repo (`src/`, `openspec/specs/data-ingestion/`) por `ingested_at`/`available_at`/`fetched_at`/`retrieved_at`: **cero resultados** | — | — | **Confirmado ausente** (no solo "no hallado"): es un supuesto documentado, sin mecanismo de verificación por fila. Habilita afirmar que el modelo no usó el valor futuro de la propia serie objetivo; **no** habilita afirmar que el dato estaba efectivamente disponible en tiempo real ese día. No se propone crear `available_at` como solución — un campo nuevo no reconstruye disponibilidad histórica ya perdida |

---

## 4. Vinculación histórica: corrección sobre "reutilizable tal cual"

El informe original presentaba `lineage.py` como "reutilizable tal cual" para
"consultar qué modelo produjo una predicción histórica dada". Esta afirmación
se corrige:

`GET /lineage/{sensor_id}` (`backend/app/routers/lineage.py:20-50`) expone la
**cadena de eventos de recalibración** de un sensor
(`source_model_id → successor_model_id`), cada uno con sus
`feedback_references`. **No identifica el modelo que produjo una predicción
histórica arbitraria**: solo lista modelos que participaron en un evento de
recalibración real. Si una predicción archivada nunca disparó una
recalibración (feedback aún no maduro, o sin corrección que la ameritara), no
aparece en este linaje en absoluto.

El endpoint que emite la predicción
(`POST /forecast/{sensor_id}/run`, `backend/app/routers/forecast.py:71-79`)
construye la respuesta con `fecha`, `alerta`, `probabilidad`, `fecha_objetivo`
— **no incluye `model_version` ni `model_id` en la respuesta al cliente**. El
`model_id` se pasa internamente a `init_prediction_feedback(...)` y queda
persistido únicamente como columna en `feedback__<sensor_id>.parquet`.

Conclusión corregida: el eslabón "qué modelo produjo esta predicción
archivada" existe como dato (columna en el parquet de feedback, si el archivo
existe), pero no se expone vía API, y no está garantizado que ese `model_id`
sea resoluble hoy contra un run de MLflow concreto (ver §2.4: el filestore
local carece de metadata de tracking). `lineage.py` resuelve la cadena de
recalibraciones de un sensor, no la resolución puntual predicción→modelo; no
corresponde presentarlo como "reutilizable tal cual" para ese propósito
específico sin verificación adicional del contrato.

---

## 5. Caso concreto

**No se puede acreditar ningún ejemplo completo con datos reales.** Eslabones
concretos que faltan, con evidencia de por qué faltan (no solo "no
verificado"):

1. **Dataset real disponible** (`melchor_romero_2024_consolidado.parquet`) →
   no tiene ninguna predicción archivada asociada (§2.3).
2. **Único ciclo predicción→feedback con esquema completo**
   (`feedback__demo-*.parquet`) → está atado a `sensor__demo-*.parquet`,
   sintético por declaración explícita del propio manifiesto (§2.2).
3. **Único dato real con ciclo predicción→feedback→holdout**
   (`controlled_daily_v4`, Etapa C 2024–2025, Pergamino) → prohibido analizar
   sus valores/clases/métricas por el protocolo v4 §16 (§1.1), y su gate de
   auditoría está en FAIL por defecto de gobernanza de proceso (M-01),
   independientemente de que los números en sí no estén objetados (§1.2).

**Naturaleza del bloqueo**: no es una carencia de implementación. El único
punto donde coexisten dato real + predicción archivada + observación posterior
vinculada es exactamente el holdout cerrado de `controlled_daily_v4`, que la
gobernanza vigente prohíbe tocar (inspeccionar, analizar o reutilizar). Fuera
de ese holdout, hay datos reales sin ciclo de predicción, o hay ciclo de
predicción completo sin datos reales (demo sintético). Con lo relevado hasta
ahora, no hay una tercera categoría con ambas propiedades a la vez.

No se creó ninguna predicción para completar el caso. No se generó dato
faltante por inferencia.

---

## 6. Separación explícita: viabilidad potencial vs. disponibilidad acreditada ahora

**(a) Viabilidad potencial de construir la funcionalidad**: existe en
principio. El contrato de `human_feedback` (schema/registry/lineage) ya
modela predicción con procedencia temporal (`model_version`,
`target_timestamp`, `validated_at`) para el store activo
(`feedback__<sensor_id>.parquet`). Construir el recorrido demostrativo
requeriría: (i) que exista o se genere operativamente un ciclo real
predicción→observación→feedback sobre datos no protegidos, y (ii) reforzar la
vinculación predicción↔modelo, hoy solo persistida como columna interna y no
expuesta por la API de forecast.

**(b) Disponibilidad acreditada de evidencia para implementarla ahora, con
datos reales, sin tocar gobernanza restringida**: **no acreditada**. No existe
hoy, en este repositorio, ningún artefacto que combine dato real + predicción
archivada + observación posterior + feedback, fuera del holdout prohibido de
`controlled_daily_v4`.

Esta separación no constituye una decisión sobre qué dataset usar para el
Paso 1; solo documenta el estado de evidencia disponible tras esta pasada
complementaria.

---

## Veredicto actualizado

Se mantiene **VIABILIDAD CONDICIONADA**, con las condiciones precisadas y
endurecidas respecto del informe original:

- El uso demostrativo de predicciones ya archivadas **fuera** del holdout
  2024–2025 no está prohibido textualmente, pero tampoco autorizado — queda
  como "uso demostrativo pendiente de aclaración documental" (§1.1).
- El FAIL de RB-05 (M-01) es un defecto de gobernanza de proceso, no de
  integridad de datos; no descalifica per se un artefacto de predicción
  individual, pero sí impide presentar B/C de `controlled_daily_v4` como
  validación confirmatoria (§1.2), y el protocolo v4 prohíbe expresamente
  analizar valores de la ventana 2024–2025 (§1.1).
- No se acreditó, con lo relevado hasta ahora, ningún caso concreto completo
  con datos reales (§5): el único punto con las tres propiedades a la vez
  (dato real, predicción archivada, observación+feedback vinculados) coincide
  exactamente con el holdout cerrado.
- `feedback_ui.parquet` deja de ser candidato válido de evidencia (§2.1); el
  candidato con esquema completo (`feedback__demo-*`) es sintético, confirmado
  sin ambigüedad (§2.2); el dataset real disponible carece de ciclo de
  predicción propio (§2.3).
- `lineage.py` no resuelve, tal como está, la pregunta "qué modelo produjo
  esta predicción archivada específica" (§4); ese dato depende de una columna
  interna no expuesta por API, sobre un parquet cuya existencia no está
  garantizada para el dataset elegido.

Este veredicto actualizado se refiere solo a la viabilidad de la demostración
histórica con la evidencia hoy disponible y accesible; no constituye una nueva
aprobación científica del trabajo, no reabre ni reinterpreta el estado de
cierre de `controlled_daily_v4`, y no decide todavía sobre qué dataset o
mecanismo usar para el Paso 1.

---

## Cierre

Diff de esta tarea: exclusivamente este archivo nuevo
(`openspec/scientific-closure/causal-historical-replay-2026-09-22/paso0-ampliacion.md`),
que convive con `paso0-relevamiento.md` sin modificarlo, en la rama
`feat/causal-historical-replay`. No se modificó ningún archivo existente, no
se ejecutó entrenamiento/inferencia, no se abrió ni inspeccionó el holdout, no
se instaló ninguna dependencia, no se hizo commit, push, PR ni merge. Se
detiene aquí para revisión antes de cualquier Paso 1.
