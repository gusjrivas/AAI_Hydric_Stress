# Spec: predictive-modeling

Capacidad implementada (Épica 2, HU4 — completa, los tres sub-proyectos: definición del problema/ingeniería de variables, modelos base/candidatos, y alertas tempranas). Orígenes: `openspec/changes/add-feature-engineering/`, `openspec/changes/add-baseline-and-candidate-models/`, `openspec/changes/add-early-warning-alerts/`. Este documento es la fuente de verdad vigente de la capacidad; los *changes* que la originaron quedan como registro histórico de la decisión, no se actualizan en paralelo a este archivo.

## Requirements

### Requirement: Variable objetivo de estrés hídrico por umbral relativo, congelado en entrenamiento

El sistema DEBE poder etiquetar cada fila de un dataset con una variable objetivo binaria: si la humedad de suelo cae por debajo de un umbral (percentil de la distribución histórica observada de esa misma variable) dentro de un horizonte de anticipación dado, medido en días. El umbral DEBE calcularse únicamente sobre el conjunto de entrenamiento y reutilizarse, congelado, para etiquetar también el conjunto de evaluación — nunca recalcularse sobre un conjunto que incluya datos de evaluación.

**Actualización (2026-09-04):** el requirement original calculaba el percentil sobre el DataFrame completo (antes de la partición temporal), lo que dejaba el umbral informado por la distribución del período de evaluación — fuga temporal confirmada en la auditoría metodológica de la memoria técnica (ver `docs/seguimiento-tareas.md`, fila "Corrección de fuga temporal en imputación y umbral de estrés"). El umbral corregido, calculado solo sobre entrenamiento, resultó más alto que el umbral anterior (0.3223 vs. 0.3115 en el dataset real), y el período de evaluación (última porción del año, con humedad de suelo sistemáticamente menor que el resto del año) pasó de ~51% a ~65% de filas etiquetadas como estrés — un desplazamiento de distribución real entre entrenamiento y evaluación que el umbral anterior ocultaba al calibrarse parcialmente con el propio período de evaluación. Ver `docs/research/hu8-analisis-resultados.md` para el análisis completo del impacto sobre los resultados experimentales.

#### Scenario: Etiquetado de una serie con un evento de estrés futuro

- **GIVEN** una serie temporal de humedad de suelo donde el valor de un día, `horizonte` días después del día actual, cae por debajo del umbral configurado
- **WHEN** se etiqueta esa serie con el horizonte y el umbral configurados
- **THEN** el día actual queda etiquetado como estrés (1)

#### Scenario: Días sin información futura suficiente no se etiquetan

- **GIVEN** una serie temporal cuyos últimos `horizonte` días no tienen datos posteriores suficientes para conocer el valor futuro
- **WHEN** se etiqueta esa serie
- **THEN** esos últimos días quedan sin etiqueta (no se inventa un valor)

#### Scenario: El umbral se calcula solo sobre entrenamiento y se reutiliza en evaluación

- **GIVEN** un conjunto de entrenamiento y un conjunto de evaluación con distribuciones distintas de humedad de suelo
- **WHEN** se calcula el umbral sobre el conjunto de entrenamiento y se etiquetan ambos conjuntos con ese mismo umbral
- **THEN** el umbral usado para etiquetar evaluación es idéntico al calculado sobre entrenamiento, nunca uno recalculado sobre la distribución de evaluación

Implementado en `src/predictive_modeling/labeling.py` (`fit_stress_threshold` + `add_stress_label`), testeado en `tests/test_labeling.py` (incluye una prueba específica de que el umbral se reutiliza congelado y nunca se recalcula sobre el segundo conjunto). Parámetros elegidos: horizonte de 3 días, percentil 20 (justificación en el *change* de origen: sin datos de capacidad de campo/punto de marchitez calibrados, un umbral agronómico absoluto no es calculable con rigor todavía — este es un proxy relativo, no una validación agronómica definitiva, y sigue sin serlo tras esta corrección). Verificado sobre el dataset real, con el pipeline corregido: umbral de entrenamiento 0.3223, ~20.5% de filas de entrenamiento etiquetadas como estrés, ~64.8% de filas de evaluación etiquetadas como estrés (71 filas con horizonte completo).

### Requirement: Variables predictoras con retardos y ventanas móviles sin fuga temporal

El sistema DEBE poder construir variables predictoras de retardo (*lag*) y ventana móvil (*rolling*) a partir de las columnas numéricas del esquema, usando únicamente información disponible hasta el día de la predicción (inclusive), nunca información de días posteriores.

#### Scenario: Una variable de retardo no contiene información futura

- **GIVEN** una serie temporal con variables climáticas y de humedad de suelo
- **WHEN** se construyen variables de retardo y ventana móvil para el día `t`
- **THEN** todas esas variables se calculan exclusivamente con datos de días `t` o anteriores

Implementado en `src/predictive_modeling/feature_engineering.py` (`add_lag_features`, `add_rolling_features`), testeado en `tests/test_feature_engineering.py`. Retardos usados: 1, 2, 3 días; ventanas móviles: 3, 7 días, sobre variables climáticas y humedad de suelo.

### Requirement: Evaluación de relevancia de variables

El sistema DEBE poder reportar la relevancia de cada variable predictora respecto de la variable objetivo (correlación), para orientar la selección de variables antes del modelado.

#### Scenario: Reporte de relevancia sobre una matriz de variables ya construida

- **GIVEN** una matriz de variables predictoras y su variable objetivo correspondiente
- **WHEN** se genera el reporte de relevancia
- **THEN** se obtiene, para cada variable predictora, su correlación con la variable objetivo

Implementado en `src/predictive_modeling/relevance.py` (`feature_relevance`), testeado en `tests/test_relevance.py`. Verificado sobre el dataset real: las variables más correlacionadas con el objetivo tienen sentido físico — radiación solar acumulada (ventanas de 3 y 7 días) correlacionada positivamente (~0.50, más sol implica más evapotranspiración y mayor probabilidad de estrés futuro), humedad relativa y humedad de suelo (ventanas móviles) correlacionadas negativamente (~-0.46 a -0.48).

Además, `tests/test_no_leakage.py` verifica explícitamente, de punta a punta (etiqueta + variables juntas), que modificar un valor futuro de humedad de suelo no altera ninguna variable de días anteriores.

### Requirement: Modelo de referencia por persistencia

El sistema DEBE poder predecir la variable objetivo mediante un modelo de referencia (baseline) que no requiere entrenamiento: predice estrés futuro si el valor actual de humedad de suelo ya está por debajo del umbral de estrés.

#### Scenario: Predicción de referencia sobre un valor actual bajo

- **GIVEN** una fila cuyo valor actual de humedad de suelo está por debajo del umbral de estrés configurado
- **WHEN** se aplica el modelo de referencia a esa fila
- **THEN** la predicción es estrés (1)

Implementado en `src/predictive_modeling/models.py` (`predict_persistence_baseline`), testeado en `tests/test_models.py`. Verificado sobre el dataset real (72 filas de test, umbral 0.3126): precisión 0.500, recall 0.474, F1 0.486.

**Actualización (2026-09-04):** re-verificado tras la corrección de fuga temporal del umbral (ver "Variable objetivo de estrés hídrico por umbral relativo, congelado en entrenamiento" más arriba). Con el umbral corregido (0.3223, calculado solo sobre entrenamiento) y las 71 filas de evaluación con horizonte completo: precisión 0.6087, recall 0.6087, F1 0.6087 — más alto que el valor anterior, pero por el mismo motivo que el resto de las configuraciones (ver `docs/research/hu8-analisis-resultados.md`): la tasa base de estrés en evaluación subió de ~51% a ~65%, por lo que F1 ya no es comparable directamente entre el antes y el después sin tener en cuenta ese desplazamiento de la clase base.

### Requirement: Entrenamiento de modelos candidatos

El sistema DEBE poder entrenar modelos candidatos (regresión logística y Random Forest) sobre un conjunto de entrenamiento con variables predictoras y la variable objetivo.

#### Scenario: Entrenamiento de ambos candidatos sobre el mismo conjunto

- **GIVEN** un conjunto de entrenamiento con variables predictoras y la variable objetivo, sin valores faltantes
- **WHEN** se entrenan los modelos candidatos sobre ese conjunto
- **THEN** ambos modelos quedan entrenados y pueden generar predicciones sobre datos nuevos con las mismas columnas

Implementado en `src/predictive_modeling/models.py` (`build_candidate_models`) y `src/predictive_modeling/training.py` (`train_models`), testeado en `tests/test_models.py` y `tests/test_training.py`. Verificado sobre el dataset real: 285 filas de entrenamiento, 72 de test (split cronológico 80/20 tras ingeniería de variables e interpolación).

### Requirement: Ajuste de hiperparámetros con validación temporal

El sistema DEBE poder ajustar los hiperparámetros de un modelo candidato usando validación cruzada que respete el orden temporal (cada fold de validación posterior a su fold de entrenamiento correspondiente).

#### Scenario: Ajuste de hiperparámetros sin mezclar fechas entre folds

- **GIVEN** un conjunto de entrenamiento ordenado cronológicamente y una grilla de hiperparámetros para un modelo candidato
- **WHEN** se ajustan los hiperparámetros con validación cruzada temporal
- **THEN** en cada fold de validación cruzada, todas las fechas del fold de validación son posteriores a todas las fechas del fold de entrenamiento correspondiente

Implementado en `src/predictive_modeling/training.py` (`tune_hyperparameters`, con `sklearn.model_selection.TimeSeriesSplit` + `GridSearchCV`), testeado en `tests/test_training.py`. Verificado sobre el dataset real (5 folds, conjunto de entrenamiento de 285 filas): mejores parámetros `C=0.1` (regresión logística) y `max_depth=5, n_estimators=100` (Random Forest).

**Actualización (2026-09-05):** `tune_hyperparameters` ahora acepta `gap: int = 0`, reenviado a `TimeSeriesSplit(n_splits=n_splits, gap=gap)`, para dejar un margen entre cada fold de entrenamiento y su fold de validación correspondiente — sin este margen, el objetivo de una fila de entrenamiento (calculado con horizonte hacia adelante) podía solaparse temporalmente con el fold de validación. Se agregó también `diagnose_time_series_folds(y, n_splits, gap)`, que reporta positivos/negativos por fold sin necesidad de entrenar ningún modelo, usado para el diagnóstico empírico de la sección 12.4 de `docs/research/hu8-analisis-resultados.md`.

### Requirement: Selección automática del mejor modelo candidato

El sistema DEBE poder elegir automáticamente, entre un conjunto de modelos candidatos, el de mejor desempeño de validación cruzada temporal, y devolver ese modelo ya ajustado junto con su nombre y su puntaje de validación.

#### Scenario: Selección entre candidatos con desempeño distinto

- **GIVEN** un conjunto de entrenamiento y un conjunto de modelos candidatos con sus grillas de hiperparámetros
- **WHEN** se ejecuta la selección automática
- **THEN** se devuelve el modelo candidato con mayor `cv_mean_score` (F1 medio entre folds de `TimeSeriesSplit`), ya ajustado sobre el conjunto de entrenamiento completo, junto con su nombre y su `cv_mean_score`/`cv_std_score`

#### Scenario: Selección usa los candidatos y grillas por defecto si no se especifican otros

- **GIVEN** solo un conjunto de entrenamiento, sin candidatos ni grillas explícitos
- **WHEN** se ejecuta la selección automática
- **THEN** se usan `build_candidate_models` y `DEFAULT_HYPERPARAMETER_GRIDS` (los mismos ya existentes de HU4) como candidatos y grillas por defecto

Implementado en `src/predictive_modeling/model_selection.py` (`select_best_candidate`), testeado en `tests/test_model_selection.py`. Verificado sobre el dataset real (Melchor Romero 2024): `logistic_regression` y `random_forest` empataron en `cv_mean_score=0.0` para ambos (mismo fenómeno de folds sin ejemplos de la clase de estrés que afecta a `tune_hyperparameters` con este tamaño de muestra, ver "Limitaciones conocidas" más abajo). ~~El desempate original... se endureció para preferir `random_forest` en caso de empate...~~

**Actualización (2026-09-05):** una segunda auditoría metodológica cuestionó ese desempate hacia `random_forest` por no tener justificación estadística (era una preferencia por nombre, no por desempeño). Rediseñado: en caso de empate de `cv_mean_score`, ahora se prefiere el candidato con menor `cv_std_score` (más estable entre folds); si el empate persiste, el desempate es alfabético y explícito, nunca implícito hacia un modelo en particular. Además, `select_best_candidate` ahora acepta `gap: int = 0` (reenviado a `TimeSeriesSplit`, ver el requirement de ajuste de hiperparámetros) y devuelve `fold_diagnostics` (positivos/negativos por fold de validación) y `selection_warning` (texto explícito cuando algún fold de validación carece de ejemplos positivos) — en vez de ocultar la ausencia de evidencia suficiente para elegir un modelo detrás de un promedio de F1, el sistema la declara. Sobre el dataset real, con `gap=horizon_days=3`, `select_best_candidate` sigue eligiendo `random_forest`, ahora por desempeño observado y no por el desempate anterior. Ver `docs/research/hu8-analisis-resultados.md`, sección 12.4, para el diagnóstico empírico de `n_splits`/`gap` que sustenta mantener `n_splits=5` como valor por defecto. Ver también `openspec/specs/alerting-ui/spec.md`.

### Requirement: Comparación de desempeño, estabilidad y complejidad

El sistema DEBE poder comparar el modelo de referencia y los modelos candidatos entrenados, reportando para cada uno: métricas de desempeño de la clase de estrés (precisión, recall, F1, ROC-AUC), estabilidad (desvío de la métrica entre folds de validación cruzada) y un indicador de complejidad del modelo.

#### Scenario: Comparación de tres modelos sobre el mismo conjunto de evaluación

- **GIVEN** el modelo de referencia y dos modelos candidatos ya entrenados, y un conjunto de evaluación común
- **WHEN** se comparan los tres modelos
- **THEN** se obtiene, para cada uno, sus métricas de desempeño, su estabilidad y su indicador de complejidad, en una tabla comparable

Implementado en `src/predictive_modeling/evaluation.py` (`evaluate_classifier`, `compare_models`), testeado en `tests/test_evaluation.py`. Verificado sobre el dataset real (72 filas de test, tasa positiva 52.8%):

| Modelo | Precisión | Recall | F1 | ROC-AUC | `cv_std_score` | Complejidad |
|---|---|---|---|---|---|---|
| Persistencia (referencia) | 0.500 | 0.474 | 0.486 | — | — | — |
| Regresión logística | 0.500 | 0.342 | 0.406 | 0.533 | ~0.0 | 1 (lineal) |
| Random Forest | 0.667 | 0.368 | 0.475 | 0.554 | ~0.0 | 100 árboles, profundidad 5 |

En este dataset, ninguno de los dos candidatos supera al modelo de referencia en F1; el Random Forest tiene mejor precisión y ROC-AUC. Ver "Limitaciones conocidas".

**Actualización (2026-09-05):** el protocolo de evaluación se amplió con dos baselines triviales adicionales — clase mayoritaria (`predict_majority_class_baseline`) y "siempre estrés" (`predict_always_stress_baseline`), junto al ya existente de persistencia — y con tres métricas robustas al desbalance de clases: balanced accuracy, MCC (`matthews_corrcoef`) y average precision/PR-AUC (`average_precision_score` cuando hay probabilidades disponibles), sin reemplazar precisión/recall/F1/ROC-AUC ya existentes. Implementado en `src/predictive_modeling/models.py` y `src/predictive_modeling/evaluation.py` (`evaluate_classifier`), testeado en `tests/test_models.py`/`tests/test_evaluation.py`. Estos baselines y métricas se registran automáticamente en MLflow para cada configuración experimental (ver `openspec/specs/experiment-runner/spec.md`). Motivación concreta: sobre el dataset real, un F1 alto de una configuración experimental resultó explicado por desbalance de clases y no por capacidad de discriminación real — un MCC cercano a 0 o negativo lo revela donde F1 no lo hace (ver `docs/research/hu8-analisis-resultados.md`, sección 12.3).

### Requirement: Generación de alertas tempranas por umbral de probabilidad

El sistema DEBE poder convertir la probabilidad predicha de estrés de un modelo entrenado en una alerta binaria, usando un umbral de decisión configurable.

#### Scenario: Emisión de alerta cuando la probabilidad supera el umbral

- **GIVEN** un modelo entrenado con `predict_proba` y un conjunto de datos con variables predictoras
- **WHEN** se generan alertas con un umbral de decisión configurado
- **THEN** cada fila con probabilidad de estrés mayor o igual al umbral queda marcada con alerta (1), y el resto sin alerta (0)

Implementado en `src/predictive_modeling/alerts.py` (`generate_alerts`), testeado en `tests/test_alerts.py`. Configuración final: modelo Random Forest (mejor precisión y ROC-AUC de los tres modelos comparados), umbral 0.5 (no calibrado contra el propio conjunto de validación, ver "Limitaciones conocidas"). Verificado sobre el dataset real: 21 alertas de 72 filas de test (29.2%).

### Requirement: Análisis de errores de predicción por fecha

El sistema DEBE poder identificar, sobre un conjunto de evaluación con fechas, las fechas concretas de falsos positivos (alerta sin estrés real) y falsos negativos (estrés real sin alerta).

#### Scenario: Identificación de una alerta incorrecta puntual

- **GIVEN** un conjunto de evaluación con fecha, etiqueta real y alerta generada, donde una fila tiene alerta pero la etiqueta real es "sin estrés"
- **WHEN** se analiza los errores de predicción
- **THEN** la fecha de esa fila aparece listada como falso positivo

Implementado en `src/predictive_modeling/alerts.py` (`analyze_prediction_errors`), testeado en `tests/test_alerts.py`. Verificado sobre el dataset real: 7 falsos positivos (ej. 2024-11-15, 2024-12-10 a 2024-12-13) y 24 falsos negativos (ej. 2024-10-18 a 2024-10-20, 2024-11-17 a 2024-11-22) — consistente con la precisión (0.667) y recall (0.368) reportados para Random Forest en la comparación de modelos.

## Limitaciones conocidas

- El umbral de estrés es relativo (percentil 20 de la distribución observada en un único punto/año), no un umbral agronómico validado con datos de capacidad de campo/punto de marchitez reales. Reevaluar si se consiguen esos datos.
- Verificado con un único dataset real (Melchor Romero 2024). No se validó con datos de otros puntos geográficos o años — el umbral relativo, en particular, cambiaría al incorporar más datos.
- El horizonte de anticipación (3 días) y los retardos/ventanas elegidos (1-3 días, 3-7 días) son una elección razonada pero no la única posible; no se comparó contra otros horizontes o ventanas todavía.
- La evaluación de relevancia usa correlación lineal simple; no captura relaciones no lineales entre variables y objetivo, que un modelo de los sub-proyectos siguientes de HU4 sí podría aprovechar.
- Con ~285 filas de entrenamiento y ~20% de tasa positiva, algunos folds tempranos de `TimeSeriesSplit` quedan con pocos o ningún ejemplo de la clase de estrés, lo que hace que `cv_mean_score`/`cv_std_score` (F1 promedio entre folds) resulten en 0.0 aunque el modelo final sí discrimine razonablemente sobre el conjunto de test completo (ver tabla de comparación). Esto es una limitación del tamaño de muestra, no un defecto de la implementación de `TimeSeriesSplit`; se espera que mejore con más años/puntos de datos.
- Ni la regresión logística ni el Random Forest superan claramente al modelo de referencia por persistencia en F1 sobre este dataset — señal de que, con los datos actuales, el valor de humedad de suelo actual ya captura la mayor parte de la información predictiva disponible a 3 días.
- El umbral de alerta (0.5) no se ajustó contra el conjunto de validación por riesgo de sobreajuste con ~285 filas de entrenamiento; queda documentado como punto de recalibración cuando haya más datos o retroalimentación humana real (HU5). El recall relativamente bajo (0.368 sobre Random Forest) implica que, con este umbral, la mayoría de los eventos de estrés reales (24 de 38 en el conjunto de test) no generan alerta — una limitación a comunicar explícitamente si esta capa se usa para decisiones operativas antes de recalibrar.
- ET0 (evapotranspiración de referencia) no es una variable predictiva de ningún experimento de HU7/HU8: `estimate_et0`/`reference_et0` (`src/data_ingestion/mock_sensor.py`) solo se usa para generar datos sintéticos de sensores simulados (HU2). En el dataset experimental real (`melchor_romero_2024_consolidado`), la columna `et0` está presente en el esquema pero con 0 de 366 valores no nulos, y `FEATURE_COLUMNS` no la incluye en ningún punto del código. Confirmado por auditoría (2026-09-05); no se agregó automáticamente como variable, por instrucción explícita — de considerarse valiosa, debe evaluarse como un experimento controlado separado, no como una modificación silenciosa de las 4 configuraciones existentes.
