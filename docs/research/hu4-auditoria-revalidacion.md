# HU4 — Auditoría de revalidación del cierre

HU4 (issue #13) ya había sido cerrada formalmente, con sus 14 issues hijos (#58 a #71) cerrados como `completed`. Con posterioridad a ese cierre se realizaron correcciones metodológicas que afectaron la variable objetivo (umbral calculado sobre todo el dataset), la validación temporal (ausencia de `gap` entre folds) y la selección automática de modelos (desempate arbitrario hacia Random Forest). Por ese motivo se revalidó el cierre contra el código y las specs vigentes, no solo contra la evidencia histórica de los PR originales. Los cuatro criterios de aceptación continúan satisfechos. No se requiere reapertura de #13 ni de ningún issue hijo.

## 1. Objetivo y alcance

Esta auditoría revalida:

- variable objetivo;
- horizonte de anticipación;
- ingeniería de variables;
- modelo de referencia (baseline);
- modelos candidatos;
- entrenamiento;
- ajuste de hiperparámetros;
- validación temporal;
- selección automática de modelo;
- métricas registradas;
- alertas tempranas;
- análisis de errores;
- inferencia futura.

La contrastación científica de la hipótesis de investigación corresponde a HU7/HU8, no a HU4. Esta auditoría no reinterpreta ni evalúa esa contrastación.

## 2. Criterios de aceptación

### CA1 — Ingeniería de variables

**Estado: CUMPLE**

- Lags de 1, 2 y 3 días; ventanas móviles (rolling) de 3 y 7 días (`src/predictive_modeling/feature_engineering.py::add_lag_features`/`add_rolling_features`).
- Cálculo exclusivamente retrospectivo: sin `center=True`, sin shifts negativos en la construcción de features.
- El uso de historia de entrenamiento para construir features causales de los primeros días de evaluación es legítimo (retrospectivo por diseño) y no constituye fuga.

Se distingue explícitamente la ingeniería de variables (features) del etiquetado (labeling): `shift(-horizon_days)` es válido para construir retrospectivamente el target observado a partir de la humedad de suelo futura real, pero no se usa para construir ninguna variable predictora — las features nunca miran hacia adelante.

### CA2 — Entrenamiento

**Estado: CUMPLE**

- Modelos candidatos: regresión logística y Random Forest (`src/predictive_modeling/models.py::build_candidate_models`).
- `train_models` (`src/predictive_modeling/training.py`) y `tune_hyperparameters` reciben, estructuralmente, únicamente el conjunto de entrenamiento.
- `tune_hyperparameters` usa `TimeSeriesSplit` (validación cruzada temporal); el conjunto de evaluación final no participa en ningún punto del tuning ni de la selección de modelo.

### CA3 — Predicciones y alertas tempranas

**Estado: CUMPLE**

- `predict_proba` de los modelos entrenados alimenta `generate_alerts`, que convierte la probabilidad en una alerta binaria con `alert_threshold = 0.5`.
- Horizonte formal de 3 días, consistente entre etiquetado, features y alertas.
- `predict_available` (`src/architecture_integration/pipeline.py`) implementa inferencia futura real, sin requerir el target futuro (que aún no existe en ese momento), sin reajustar modelo, detector de anomalías ni threshold durante la inferencia.

### CA4 — Métricas registradas

**Estado: CUMPLE**

Métricas actualmente soportadas: precisión, recall, F1, ROC-AUC, balanced accuracy, MCC (`matthews_corrcoef`) y average precision/PR-AUC (`src/predictive_modeling/evaluation.py::evaluate_classifier`, `compare_models`).

CA4 exige registrar métricas para su evaluación posterior. **No exige**: un valor mínimo de F1; un MCC positivo; superar todos los baselines; confirmar la hipótesis de investigación; ni generalización científica externa. Esta distinción se preserva explícitamente para no sobreinterpretar el criterio.

## 3. Definición formal vigente

- Problema: clasificación binaria.
- Variable de referencia: humedad de suelo.
- Target: condición futura de humedad de suelo por debajo de un umbral, a horizonte `horizon_days`.
- Umbral de estrés: percentil 20 de la distribución de humedad de suelo observada.
- Ajuste del umbral: exclusivamente sobre el conjunto de entrenamiento/calibración; congelado y reutilizado, sin recalcularse, para etiquetar evaluación.
- Horizonte: 3 días.
- Lags: 1, 2, 3 días. Ventanas móviles (rolling): 3 y 7 días.
- Modelos candidatos: regresión logística y Random Forest.
- Validación: temporal (`TimeSeriesSplit`, con `gap` parametrizable).
- Umbral de alerta (`alert_threshold`): 0.5, fijo.

El percentil 20 constituye un **proxy relativo** de estrés hídrico. No representa capacidad de campo, punto de marchitez, ni ningún umbral agronómico universal calibrado: la justificación explícita, documentada desde el origen de este componente, es que no existen datos de esos parámetros calibrados para este suelo.

## 4. Correcciones metodológicas posteriores al cierre

Cronológicamente, sin reproducir métricas experimentales innecesarias:

1. **Umbral de estrés calculado sobre todo el dataset → corregido para ajustarse solo con entrenamiento.** El requirement original calculaba el percentil sobre el DataFrame completo antes de partir en entrenamiento/evaluación, dejando el umbral informado por la distribución del período de evaluación.
2. **Protección de la frontera temporal del target.** Se incorporó el filtrado por `target_timestamp < cutoff`, de modo que ninguna fila de entrenamiento retiene una etiqueta cuya fecha objetivo caiga dentro del período de evaluación.
3. **Incorporación de `gap=horizon_days` en la validación temporal**, para que ningún fold de entrenamiento incluya un objetivo que se solape con su fold de validación correspondiente.
4. **Eliminación del desempate arbitrario hacia Random Forest.** El desempate original, ante un empate de `cv_mean_score`, favorecía a Random Forest por nombre, sin justificación estadística.
5. **Selección automática actual**, basada en: mayor `cv_mean_score`; ante empate, menor `cv_std_score`; si el empate persiste, desempate alfabético explícito y determinista.
6. **Folds sin ambas clases: la selección automática se considera no evaluable y falla explícitamente**, en lugar de producir silenciosamente un modelo aparentemente válido a partir de una comparación no informativa.

Estas correcciones fortalecen la validez metodológica del estado actual de HU4; no debilitan ni reabren ninguno de sus criterios de aceptación.

## 5. Control de selección post hoc

En el código vigente no se encontró evidencia de:

- elegir Random Forest por desempeño observado en el conjunto de evaluación;
- ajustar el umbral de estrés con datos de evaluación;
- ajustar `alert_threshold` con datos de evaluación;
- modificar `horizon_days` a partir de resultados de evaluación;
- modificar lags o ventanas móviles por desempeño de evaluación;
- elegir `n_splits` para mejorar resultados de evaluación;
- elegir hiperparámetros utilizando el conjunto de evaluación;
- excluir semillas desfavorables de la comparación experimental.

La selección automática de modelo (`select_best_candidate`) se describe correctamente como un procedimiento **previo a la evaluación final**, basado exclusivamente en validación cruzada temporal sobre entrenamiento. No se afirma que Random Forest sea intrínsecamente superior a la regresión logística: es, en la configuración experimental vigente, el modelo que resulta seleccionado por ese procedimiento formal, no por preferencia ni por observación de test.

## 6. Folds de validación y evidencia insuficiente

`TimeSeriesSplit` se usa con `gap` temporal; `diagnose_time_series_folds` reporta la cantidad de positivos/negativos por fold sin necesidad de entrenar ningún modelo. La implementación vigente de `select_best_candidate` produce un `ValueError` explícito cuando existen folds sin ambas clases bajo la política común, en vez de presentar como válida una comparación cuyo F1 no es informativo.

Esta protección evita ocultar la ausencia de evidencia suficiente detrás de un promedio de métrica, pero **no transforma la disponibilidad limitada de datos en una muestra estadísticamente amplia**: la disponibilidad limitada de datos (un único sitio, un único año) sigue siendo una limitación real de HU4, documentada explícitamente en la sección 8.

## 7. Limitaciones a preservar

- Dataset de un único sitio y un único año (Melchor Romero, 2024).
- Umbral de estrés relativo (percentil 20), no calibrado agronómicamente contra capacidad de campo o punto de marchitez reales.
- Cantidad reducida de observaciones, con folds tempranos de `TimeSeriesSplit` potencialmente degenerados.
- Relevancia de variables evaluada mediante correlación lineal simple, no causalidad.
- Regresión logística y Random Forest como candidatos formales acotados; Deep Learning permanece como alternativa experimental, no como requisito.
- `alert_threshold` fijo en 0.5, no calibrado contra el conjunto de validación ni contra retroalimentación humana real (HU5).
- Posible sensibilidad de la regresión logística a la escala de las variables predictoras (el orquestador no estandariza variables, consistente con cómo se entrenaron y verificaron los modelos candidatos en HU4).
- ET0 no utilizada como predictor en el protocolo formal vigente (decisión deliberada, no un descuido).
- Inferencia futura implementada y verificada funcionalmente, pero no validada todavía como sistema agronómico productivo.

Ninguna de estas limitaciones se convierte en una tarea obligatoria nueva de HU4.

## 8. Auditoría de issues hijos (#58 a #71)

| Issue | Estado revalidado | Evidencia vigente |
|---|---|---|
| #58 — Definir la variable objetivo y el horizonte de anticipación | RATIFICADO CON LIMITACIÓN | `labeling.py` sin cambios en su definición (percentil 20, horizonte 3 días); la fuga corregida posteriormente estaba en el *uso* del threshold en el orquestador, no en la definición original de este issue |
| #59 — Identificar variables predictoras, retardos y ventanas temporales | RATIFICADO | `feature_engineering.py`, sin cambios |
| #60 — Implementar la ingeniería de variables temporales y agronómicas | RATIFICADO | Mismo módulo, sin cambios |
| #61 — Evaluar relevancia de variables y posibles fugas de información | RATIFICADO CON LIMITACIÓN | `relevance.py`/`test_no_leakage.py` sin cambios; la fuga real (threshold/imputación calculados antes de partir) fue detectada por una auditoría posterior más profunda, no por el mecanismo original de este issue. El mecanismo vigente (purga por `target_timestamp` + `gap`) sí cubre hoy ese caso |
| #62 — Definir modelos de referencia y modelos candidatos | RATIFICADO | `models.py`, sin cambios |
| #63 — Implementar el modelo de referencia | RATIFICADO CON LIMITACIÓN | Código sin cambios; los valores reportados originalmente (F1=0.486) fueron superados por el recálculo posterior a la corrección de fuga (F1=0.6087), ya documentado con nota de actualización en la spec |
| #64 — Implementar el flujo de entrenamiento para los modelos candidatos | RATIFICADO | `train_models`, sin cambios |
| #65 — Implementar el esquema de validación temporal o cruzada | RATIFICADO CON LIMITACIÓN | `TimeSeriesSplit` sin `gap` en la implementación original; se agregó `gap: int = 0` posteriormente para evitar solape de target con fold de validación — mecanismo vigente correcto, distinto del auditado al momento del cierre original |
| #66 — Ejecutar el entrenamiento inicial de los modelos candidatos | RATIFICADO CON LIMITACIÓN | Cifras originales (285/72 filas) superadas por el recálculo posterior a la corrección de fuga; la spec ahora marca esa evidencia como histórica |
| #67 — Ejecutar el ajuste de hiperparámetros | RATIFICADO CON LIMITACIÓN | Mecanismo (`tune_hyperparameters`) vigente y correcto con `gap`; los valores concretos (`C=0.1`, `max_depth=5`, `n_estimators=100`) fueron obtenidos sobre el dataset previo a la corrección de fuga, ahora marcados como evidencia histórica en la spec |
| #68 — Comparar desempeño, estabilidad y complejidad de los modelos | RATIFICADO CON LIMITACIÓN | `evaluate_classifier`/`compare_models` con más métricas hoy (MCC, balanced accuracy, AP); la tabla comparativa histórica de la spec ahora está marcada explícitamente como evidencia previa a las correcciones metodológicas |
| #69 — Definir e implementar la lógica de generación de alertas tempranas | RATIFICADO CON LIMITACIÓN | `generate_alerts` sin cambios de código; el texto de la spec que describía "configuración final: Random Forest por mejor precisión y ROC-AUC" fue corregido en esta iteración para distinguir la evidencia histórica del mecanismo vigente de selección automática |
| #70 — Analizar errores de predicción y alertas incorrectas | RATIFICADO | `analyze_prediction_errors`, sin cambios; los valores concretos (FP/FN) siguen siendo evidencia histórica válida de su momento |
| #71 — Documentar configuración, métricas y limitaciones del modelo | RATIFICADO CON LIMITACIÓN | El documento exigido por este issue (`predictive-modeling/spec.md`) existe y, tras esta iteración, distingue explícitamente la evidencia histórica del mecanismo vigente en los requirements de entrenamiento, tuning, comparación y alertas |

Todos los issues #58 a #71 continúan **CLOSED / completed**. Ninguno se reabre: en los casos donde el mecanismo original cambió, el mecanismo vigente satisface el requirement actual correspondiente.

## 9. Conclusión

Los cuatro criterios de aceptación de HU4 (CA1-CA4) permanecen en estado CUMPLE contra el código y las specs vigentes, incluidas las correcciones metodológicas posteriores al cierre original. No se detectaron gaps técnicos bloqueantes, fuga temporal ni evidencia de selección post hoc. El issue #13 y sus 14 issues hijos (#58-#71) permanecen cerrados; esta auditoría no reabre ni modifica ninguno de ellos. `openspec/specs/predictive-modeling/spec.md` fue sincronizada en esta misma iteración para distinguir explícitamente la evidencia histórica del mecanismo formal vigente, sin modificar ningún requirement, escenario ni comportamiento formal.
