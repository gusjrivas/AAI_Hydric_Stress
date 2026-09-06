# HU3 — Auditoría de revalidación del cierre

HU3 (issue #12) ya había sido cerrada formalmente en GitHub, con sus 14 issues hijos (#44 a #57) cerrados como `completed`. Con posterioridad a ese cierre se realizaron correcciones metodológicas (imputación causal, integración real de `is_anomaly`, separación fit/apply del detector de anomalías, prevención de fuga temporal) que afectaron componentes cubiertos por HU3. Esta auditoría revalida el cierre contra el estado **vigente** del código y de las specs, no solo contra la evidencia histórica de los PR originales de cierre.

Conclusión adelantada: HU3 **no se reabre**. Sus cuatro criterios de aceptación continúan satisfechos contra el código actual.

## 1. Objetivo y alcance

Esta auditoría revalida:

- procesamiento básico de datos (distribuciones, rangos, reporte de calidad);
- imputación;
- partición temporal;
- escalado;
- detección de anomalías;
- generación de datos sintéticos;
- integración del pipeline (`data_quality.pipeline` y su consumo desde `architecture_integration.pipeline`);
- compatibilidad de la salida con `predictive-modeling`.

Esta auditoría no evalúa si la hipótesis de investigación queda confirmada: esa contrastación corresponde a HU7/HU8 y no se modifica ni se reinterpreta aquí.

## 2. Criterios de aceptación

### CA1 — Procesamiento correcto de datos

**Estado: CUMPLE**

- `quality_report` (`src/data_quality/quality_report.py`) reporta faltantes, duplicados y valores fuera de rango.
- Imputación causal (`src/data_quality/imputation.py::interpolate_missing_causal`): forward-fill exclusivamente, sin `bfill` en ningún punto; cada fila imputada queda marcada en una columna `_imputado`.
- La partición de evaluación recibe como `warm_start` únicamente la última observación válida de la partición de entrenamiento — nunca observaciones del propio período de evaluación ni observaciones futuras.
- Partición temporal (`src/data_quality/splitting.py::temporal_train_test_split`): corte cronológico simple, sin mezcla de fechas entre entrenamiento y evaluación.
- Escalado (`src/data_quality/scaling.py`): los parámetros se ajustan únicamente sobre entrenamiento y se aplican sin reajustar sobre evaluación y sobre los datos sintéticos.

La implementación original de este componente usaba interpolación bidireccional (`limit_direction="both"`), que permitía que la imputación de una fila de entrenamiento usara información de fechas posteriores. Esa implementación fue reemplazada por la versión causal descrita arriba; el reemplazo está efectivamente vigente en el código, no solo documentado en un registro histórico.

### CA2 — Detección de anomalías

**Estado: CUMPLE**

- Isolation Forest (`src/data_quality/anomaly_detection.py`), método no supervisado, con `contamination` y `random_state` parametrizables.
- `fit_anomaly_detector` se invoca únicamente sobre el conjunto de entrenamiento; `apply_anomaly_detector` aplica ese mismo detector, sin reajustar, tanto sobre entrenamiento como sobre evaluación.
- `is_anomaly` llega efectivamente como variable predictora al modelo cuando `include_anomaly_detection=True` (`architecture_integration.pipeline`) o cuando se solicita explícitamente en `data_quality.pipeline`.
- Correcciones posteriores al cierre original de HU3, verificadas como vigentes en el código actual:
  - PR #155: corrigió que `is_anomaly` se calculaba pero no llegaba realmente como predictor a la integración experimental.
  - PR #166: corrigió que `data_quality.pipeline` ajustaba un detector de anomalías de evaluación sobre la propia distribución de evaluación, en vez de reusar el detector ajustado sobre entrenamiento.

### CA3 — Generación de datos sintéticos integrada

**Estado: CUMPLE**

- Distribución normal multivariada (`src/data_quality/synthetic_data.py::generate_synthetic`) como implementación formal de referencia, ajustada mediante media y covarianza reales.
- El ajuste y la generación se realizan únicamente a partir del conjunto de entrenamiento; los datos sintéticos generados se escalan reutilizando los parámetros ya ajustados sobre entrenamiento real, sin generarse nunca a partir de evaluación.
- Cada fila sintética queda marcada con procedencia `sintetico`, preservando la trazabilidad exigida por `data-ingestion`.
- Deep Learning (GAN, VAE, TimeGAN, modelos de difusión) no es un requisito de HU3: permanece documentado como alternativa metodológica a evaluar cuando exista mayor volumen de datos reales disponibles, consistente con `docs/research/hu1-estado-del-arte.md`.

### CA4 — Salida apta para modelado predictivo

**Estado: CUMPLE**

"Apta para modelado" significa aquí:

- estructura compatible con el contrato de `predictive-modeling` (mismas columnas, mismo esquema);
- causalidad temporal preservada (ninguna transformación que aprende parámetros usa información de evaluación o del futuro);
- transformaciones reproducibles a partir de los scripts y funciones versionados;
- procedencia trazable (`real`/`sintetico`) desde la ingesta hasta la salida de HU3;
- entrenamiento y evaluación correctamente separados en todo el flujo.

"Apta para modelado" **no** significa:

- buen desempeño predictivo del modelo final;
- que los datos sintéticos mejoren las métricas del modelo;
- que la detección de anomalías mejore las métricas del modelo;
- que la hipótesis de investigación quede confirmada;
- generalización científica externa del conjunto experimental.

## 3. Correcciones metodológicas posteriores al cierre original

Cronológicamente:

1. **Reemplazo de imputación bidireccional por imputación causal.** La interpolación original (`limit_direction="both"`) permitía que una fila de entrenamiento se completara con una observación de evaluación. Reemplazada por `interpolate_missing_causal`, exclusivamente forward-fill, con partición previa a la imputación y semilla (`warm_start`) tomada únicamente de la cola de entrenamiento.
2. **Corrección de integración de `is_anomaly` (PR #155).** `is_anomaly` se calculaba pero no llegaba como predictor real al modelo entrenado por la integración experimental; corregido para que `feature_columns` la incluya efectivamente cuando `include_anomaly_detection=True` (ver `openspec/specs/architecture-integration/spec.md`, requirement "Uso de `is_anomaly` como variable predictora").
3. **Separación fit/apply del detector de anomalías, con ajuste exclusivo sobre entrenamiento (PR #166).** `data_quality.pipeline` ajustaba un detector de evaluación sobre la propia distribución de evaluación, contaminando esa partición con su propia estadística; corregido para que el mismo detector ajustado sobre entrenamiento se reutilice, sin reajuste, sobre evaluación.
4. **Prevención de contaminación temporal en el umbral de estrés y en la imputación (fuga corregida el 2026-09-04).** El umbral de la variable objetivo y la imputación se calculaban sobre el dataset completo antes de partir en entrenamiento/evaluación; corregido partiendo primero y calculando ambos únicamente sobre entrenamiento.
5. **Mecanismo vigente de purga por `target_timestamp` (segunda auditoría, 2026-09-05).** Ver sección 4.
6. **`gap=horizon_days` en la validación cruzada temporal de selección de modelo**, para que ningún fold de entrenamiento incluya un objetivo que se solape temporalmente con su fold de validación (`predictive_modeling.model_selection.select_best_candidate`).

No se reproducen aquí métricas experimentales (F1, ROC-AUC, MCC): esos valores pertenecen a la evidencia de HU7/HU8 y ya están documentados en `docs/research/hu8-analisis-resultados.md`.

## 4. Mecanismo real de purga

La implementación vigente en `src/architecture_integration/pipeline.py::run_end_to_end_pipeline` **no invoca** actualmente `data_quality.splitting.purge_target_horizon(...)`.

El código construye, para cada fila, `target_timestamp = timestamp + horizon_days`, y conserva para entrenamiento únicamente las filas que cumplen `target_timestamp < cutoff` (la evaluación, en cambio, se define por `timestamp >= cutoff`, sobre la fecha de observación, no sobre la fecha objetivo).

Este mecanismo:

- es una purga basada en la fecha real del objetivo de cada fila, no en eliminar ciegamente las últimas `horizon_days` filas de entrenamiento;
- evita problemas cuando existen filas excluidas previamente por targets faltantes (`target_observed`), donde un conteo fijo de filas podría purgar de más o de menos;
- mantiene la intención metodológica del requirement original: ninguna fila de entrenamiento retiene una etiqueta cuya fecha objetivo caiga dentro del período de evaluación;
- coexiste con `gap=horizon_days` en la validación cruzada temporal de selección de modelo, que resuelve el mismo problema dentro de los folds de entrenamiento.

`purge_target_horizon` continúa existiendo como capacidad testeada en `data-quality` (`openspec/specs/data-quality/spec.md`, `tests/test_splitting.py`), pero ya no es el mecanismo invocado por este orquestador. La spec de `architecture-integration` fue actualizada en este mismo cambio para reflejar el mecanismo vigente (ver PR de esta iteración).

## 5. Datos sintéticos: limitación preservada

La generación mediante distribución normal multivariada no impone restricciones físicas posteriores al muestreo. Por lo tanto, puede generar valores físicamente inverosímiles en variables acotadas o sesgadas, como precipitación o velocidad del viento. Esta limitación no invalida el cumplimiento funcional de HU3, pero restringe la interpretación científica de los datos sintéticos generados.

Adicionalmente:

- la similitud estadística (`statistical_similarity`) evalúa principalmente momentos (media, desvío) y correlaciones agregadas; no garantiza plausibilidad agronómica completa de cada fila sintética individual;
- la utilidad predictiva interna (`evaluate_predictive_utility`, regresión lineal simple sobre humedad de suelo a partir de variables climáticas) constituye una prueba funcional de que los datos sintéticos preservan señal predictiva básica;
- esta prueba interna no equivale a la comparación experimental formal de HU7/HU8 (que evalúa el efecto de los datos sintéticos sobre el problema real de clasificación de estrés hídrico, con Random Forest/regresión logística, y encontró un efecto negativo). Ambas evaluaciones miden cosas distintas y no se contradicen entre sí.

No se implementa clipping ni ninguna otra restricción física en esta iteración.

## 6. Detección de anomalías: limitación preservada

- La prueba de evaluación del detector (`evaluate_with_injected_anomalies`) inyecta anomalías sintéticas como perturbaciones extremas, y confirma que el mecanismo de detección funciona y está correctamente conectado al flujo.
- Una tasa de detección alta sobre esas anomalías inyectadas no demuestra desempeño sobre anomalías reales sutiles (por ejemplo, una falla de sensor con desviación moderada respecto de la distribución habitual).
- No existen etiquetas reales de anomalía en este dominio para estimar un desempeño supervisado del detector; esta es una limitación estructural del dominio, no una omisión de HU3.

No se modifica la prueba ni el detector en esta iteración.

## 7. Auditoría de issues hijos (#44 a #57)

| Issue | Estado revalidado | Evidencia vigente |
|---|---|---|
| #44 — Analizar distribuciones, rangos y tipos de las variables | RATIFICADO | `src/data_quality/distributions.py::describe_variables`, sin cambios desde el cierre original |
| #45 — Definir reglas de calidad y rangos agronómicos esperados | RATIFICADO | `src/data_quality/rules.py::AGRONOMIC_RANGES`, sin cambios |
| #46 — Implementar el reporte de valores faltantes, duplicados y atípicos | RATIFICADO | `src/data_quality/quality_report.py`, sin cambios funcionales |
| #47 — Implementar el tratamiento de valores faltantes | RATIFICADO CON LIMITACIÓN | Mecanismo original (interpolación bidireccional) reemplazado por `interpolate_missing_causal`; el mecanismo vigente cumple el requirement actual (causal, sin `bfill`, `warm_start` desde entrenamiento) |
| #48 — Implementar normalización, codificación y alineación temporal | RATIFICADO | `src/data_quality/scaling.py`, sin cambios desde la integración original |
| #49 — Preparar particiones sin contaminación entre entrenamiento y evaluación | RATIFICADO CON LIMITACIÓN | `temporal_train_test_split` sin cambios; se agregó protección adicional contra fuga de frontera de horizonte, hoy implementada como filtro por `target_timestamp` (ver sección 4) en vez de `purge_target_horizon` |
| #50 — Seleccionar métodos candidatos para detección de anomalías | RATIFICADO | Isolation Forest seleccionado y documentado, sin cambios |
| #51 — Implementar el método base de detección de anomalías | RATIFICADO CON LIMITACIÓN | `fit_anomaly_detector`/`apply_anomaly_detector` separados desde el origen; corregido en PR #166 el ajuste indebido de un detector de evaluación sobre la propia evaluación |
| #52 — Evaluar el comportamiento del detector de anomalías | RATIFICADO CON LIMITACIÓN | `evaluate_with_injected_anomalies` sin cambios; limitación estructural (sin anomalías reales etiquetadas) ya reconocida en la spec |
| #53 — Seleccionar técnicas candidatas para generación de datos sintéticos | RATIFICADO | Normal multivariada seleccionada, GAN/VAE documentado como alternativa futura |
| #54 — Implementar un prototipo de generación de datos sintéticos | RATIFICADO | `src/data_quality/synthetic_data.py::generate_synthetic`, sin cambios |
| #55 — Evaluar similitud estadística y utilidad predictiva de los datos sintéticos | RATIFICADO CON LIMITACIÓN | `statistical_similarity`/`evaluate_predictive_utility` sin cambios en el código; su interpretación no debe confundirse con el hallazgo experimental posterior de HU7/HU8 (ver sección 5) |
| #56 — Integrar las transformaciones en un flujo reproducible | RATIFICADO | `src/data_quality/pipeline.py::run_quality_pipeline` absorbió las correcciones de imputación (punto 1) y anomalías (punto 3) sin requerir un rediseño |
| #57 — Documentar decisiones, parámetros y limitaciones del componente | RATIFICADO | `openspec/specs/data-quality/spec.md` refleja el estado actual del código, incluidas ambas correcciones |

Todos los issues #44 a #57 continúan **CLOSED / completed**. Ninguno requiere reapertura: en los casos donde el mecanismo original cambió, el mecanismo vigente satisface el requirement actual correspondiente.

## 8. Conclusión

Los cuatro criterios de aceptación de HU3 (CA1-CA4) permanecen en estado CUMPLE contra el código y las specs vigentes, incluidas las correcciones metodológicas posteriores al cierre original. No se detectaron gaps técnicos bloqueantes. El issue #12 y sus 14 issues hijos (#44-#57) permanecen cerrados; esta auditoría no reabre ni modifica ninguno de ellos.

Limitaciones que se preservan explícitamente, sin convertirse en trabajo pendiente:

- evaluación del detector de anomalías únicamente con anomalías sintéticas extremas, sin evidencia de desempeño sobre fallas reales sutiles;
- ausencia de etiquetas reales de anomalía en este dominio;
- generación sintética sin restricciones físicas posteriores al muestreo;
- utilidad predictiva interna de los datos sintéticos evaluada con un modelo simple (regresión lineal), distinta de la evidencia experimental formal de HU7/HU8.
