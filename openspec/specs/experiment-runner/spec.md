# Spec: experiment-runner

Capacidad implementada (Épica 4, HU7 — completa, los tres sub-proyectos: diseño experimental, procedimiento automatizado con registro en MLflow, y ejecución real). Orígenes: `openspec/changes/add-experiment-design/`, `openspec/changes/add-experiment-automation/`, `openspec/changes/add-experiment-execution/`. Este documento es la fuente de verdad vigente de la capacidad; los *changes* que la originaron quedan como registro histórico de la decisión, no se actualizan en paralelo a este archivo.

## Requirements

### Requirement: Aumento sintético del conjunto de entrenamiento sobre variables ya construidas

El sistema DEBE poder generar filas sintéticas adicionales para el conjunto de entrenamiento muestreando conjuntamente las variables predictoras ya construidas (retardos, ventanas móviles) y la variable objetivo, sin requerir una fecha ni continuidad temporal real.

#### Scenario: Las filas sintéticas quedan marcadas y con etiqueta binaria válida

- **GIVEN** un conjunto de entrenamiento con variables predictoras ya construidas y su variable objetivo binaria
- **WHEN** se generan filas sintéticas adicionales a partir de ese conjunto
- **THEN** las filas resultantes quedan marcadas con procedencia `sintetico`, y su variable objetivo toma únicamente los valores 0 o 1

Implementado en `src/experiment_runner/synthetic_augmentation.py` (`add_synthetic_rows`), testeado en `tests/test_synthetic_augmentation.py`. Resuelve el bloqueo documentado en `openspec/specs/architecture-integration/spec.md` (HU6): a diferencia de `data_quality.synthetic_data.generate_synthetic` (que muestrea columnas físicas crudas y no puede usarse junto con las variables de retardo/ventana móvil sin inventar una fecha), esta función muestrea directamente sobre el espacio de variables ya construidas por `predictive_modeling.feature_engineering`, evitando el problema por completo.

Verificado sobre el dataset real (Melchor Romero 2024): partiendo de un conjunto de entrenamiento de 286 filas, se agregaron 100 filas sintéticas sin valores faltantes en las variables predictoras, con etiqueta binaria válida (0/1), y un modelo Random Forest reentrenado sobre el conjunto aumentado predijo sin error sobre las 71 filas del conjunto de evaluación.

### Requirement: Configuraciones comparativas de la Épica 4

El sistema DEBE poder identificar las 4 configuraciones experimentales resultantes de cruzar detección de anomalías (on/off) y aumento sintético (on/off): base, +sintéticos, +anomalías, completa.

#### Scenario: Las 4 configuraciones quedan documentadas con su combinación de factores

- **GIVEN** los dos factores de evaluación (detección de anomalías, aumento sintético)
- **WHEN** se documentan las configuraciones comparativas
- **THEN** existen exactamente 4 configuraciones, cada una con una combinación distinta de ambos factores

Documentado en `proposal.md`. Las 4 configuraciones:

| Configuración | Detección de anomalías | Aumento sintético |
|---|---|---|
| Base | No | No |
| +Sintéticos | No | Sí |
| +Anomalías | Sí | No |
| Completa | Sí | Sí |

## Diseño experimental

- **Preguntas experimentales**: ¿la detección de anomalías (HU3) mejora el desempeño del modelo predictivo (HU4) frente a la configuración base? ¿aportan los datos sintéticos (HU3) valor predictivo cuando se combinan con las variables de retardo/ventana móvil ya diseñadas (HU4)?
- **Escenarios de escasez y variabilidad**: escasez de datos se aproxima reduciendo el tamaño del conjunto de entrenamiento real (subconjunto de las filas más recientes antes del corte); variabilidad se aproxima ejecutando cada configuración con 5 semillas aleatorias distintas y reportando media/desvío de cada métrica entre corridas. No se inyecta ruido sintético artificial: no hay una caracterización real del ruido de sensor esperado más allá de los gaps ya observados y documentados en ESA CCI Soil Moisture (HU2).
- **Métricas y criterios de evaluación**: se reutilizan sin cambios las de `predictive_modeling.evaluation` (precisión, recall, F1 y ROC-AUC de la clase de estrés), más estabilidad (desvío entre repeticiones) y complejidad del modelo — mismos criterios ya usados para comparar los modelos candidatos en HU4.
- **Particiones, semillas y repeticiones**: partición temporal simple (`data_quality.splitting.temporal_train_test_split`, ya verificada sin fuga en HU3); 5 semillas aleatorias por configuración experimental.

### Requirement: Ejecución automatizada de una configuración experimental con múltiples semillas

El sistema DEBE poder ejecutar una configuración experimental (detección de anomalías y/o aumento sintético) sobre un dataset, repitiendo la ejecución con distintas semillas aleatorias, y devolver las métricas de desempeño de cada semilla.

#### Scenario: Una configuración con 3 semillas produce 3 filas de métricas

- **GIVEN** un dataset consolidado, una configuración experimental, y una lista de 3 semillas
- **WHEN** se ejecuta el procedimiento automatizado con esa configuración
- **THEN** el resultado tiene exactamente 3 filas, una por semilla, cada una con sus métricas de desempeño

Implementado en `src/experiment_runner/runner.py` (`run_configuration`), testeado en `tests/test_experiment_runner.py`. Ejecuta el orquestador de HU6 (`run_end_to_end_pipeline`) una vez por semilla, aplicando `add_synthetic_rows` cuando la configuración incluye aumento sintético. Verificado sobre el dataset real (configuración base, 3 semillas): F1 entre 0.400 y 0.500 según la semilla, ROC-AUC entre 0.533 y 0.558.

### Requirement: Registro de parámetros, versiones y resultados en MLflow

El sistema DEBE poder registrar en MLflow los resultados de una configuración ya ejecutada: un run padre con los parámetros de la configuración y las métricas agregadas, y un run hijo anidado por cada semilla con sus propios parámetros y métricas.

#### Scenario: Registro de una configuración con sus semillas como runs anidados

- **GIVEN** los resultados de una configuración experimental ejecutada con varias semillas
- **WHEN** se registran esos resultados en MLflow
- **THEN** se crea un run padre con las métricas agregadas de la configuración, y un run hijo por cada semilla anidado bajo ese run padre

Implementado en `src/experiment_runner/mlflow_logging.py` (`log_configuration_results`), testeado en `tests/test_mlflow_logging.py`. Se agregó `mlflow` como dependencia del proyecto (`mlflow>=2.14,<3`, mismo rango que el servidor de ADR-0004, para evitar incompatibilidades de API cliente/servidor). Verificado sobre los resultados reales de la configuración base (3 semillas): run padre con `f1_mean=0.449`, `f1_std=0.050` (y equivalentes para precisión/recall/ROC-AUC), y 3 runs hijos anidados recuperables por `tags.mlflow.parentRunId`.

### Requirement: Ejecución real de las 4 configuraciones contra el servidor MLflow

El sistema DEBE poder ejecutar las 4 configuraciones experimentales (base, +sintéticos, +anomalías, completa) con 5 semillas cada una sobre el dataset real, registrando los resultados en el servidor MLflow real (`http://localhost:5000`, ADR-0004).

#### Scenario: Las 4 configuraciones quedan registradas como runs padre distintos

- **GIVEN** el servidor MLflow real levantado (docker-compose) y el dataset consolidado real
- **WHEN** se ejecutan las 4 configuraciones experimentales con sus 5 semillas
- **THEN** el servidor MLflow tiene 4 runs padre distintos, cada uno con 5 runs hijos anidados

Ejecutado y registrado contra el servidor real (`http://localhost:5000`, Postgres + MinIO). Resultado real (dataset Melchor Romero 2024, modelo Random Forest, 5 semillas):

| Configuración | F1 (media ± desvío) | ROC-AUC (media ± desvío) | Precisión (media) | Recall (media) |
|---|---|---|---|---|
| Base | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| +Sintéticos | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |
| +Anomalías | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| Completa | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |

**Hallazgo importante**: `+Anomalías` produce métricas *idénticas* a `Base`, y `Completa` idénticas a `+Sintéticos`. La causa es que `is_anomaly` (la columna que agrega la detección de anomalías) nunca se incluye entre las variables predictoras (`feature_columns`) que recibe el modelo en `run_end_to_end_pipeline` — la detección de anomalías corre y marca filas, pero esa marca no llega a influir la predicción. Con el pipeline actual, el factor "detección de anomalías" no tiene ningún efecto medible en el desempeño del modelo. Además, el aumento sintético empeora el desempeño frente a la configuración base (F1 0.312 vs. 0.459) en este dataset.

### Requirement: Reproducibilidad verificada entre corridas

El sistema DEBE producir métricas idénticas al re-ejecutar la misma configuración con las mismas semillas.

#### Scenario: Dos corridas de la misma configuración con las mismas semillas coinciden

- **GIVEN** una configuración experimental ya ejecutada con un conjunto de semillas
- **WHEN** se re-ejecuta esa misma configuración con las mismas semillas
- **THEN** las métricas de cada semilla son idénticas entre ambas corridas

Verificado re-ejecutando la configuración `base` con las mismas 5 semillas contra el dataset real: `pandas.testing.assert_frame_equal` confirmó que las métricas de ambas corridas son idénticas fila por fila, sin ninguna diferencia — el procedimiento es completamente determinista dadas las semillas.

## Limitaciones conocidas

- El escenario de "ruido" queda sin implementar por falta de una fuente real que lo caracterice; se reevaluará si surge una necesidad concreta durante el análisis de resultados (HU8).
- El escenario de "escasez" (subconjunto del entrenamiento real) no se ejecutó en esta ronda de experimentos; el procedimiento automatizado ya soporta variar semillas y configuración, pero no todavía un parámetro de tamaño de muestra reducido.
- **La detección de anomalías no afecta actualmente el desempeño del modelo**: `is_anomaly` no se incluye entre las variables predictoras en `run_end_to_end_pipeline` (HU6). Para que el factor "detección de anomalías" sea comparable de verdad en HU8, esto debería resolverse (ej. incluyendo `is_anomaly` como variable predictora, o filtrando filas anómalas del entrenamiento en vez de solo marcarlas) — se documenta como hallazgo para el análisis de HU8, no se corrige en este *change* para no alterar retroactivamente los resultados ya registrados.
- El aumento sintético sobre variables ya construidas empeoró el desempeño frente a la configuración base en este dataset — consistente con la limitación ya documentada de que el muestreo por normal multivariada no captura relaciones no lineales ni la estructura temporal real de las variables de retardo/ventana móvil.
- El aumento sintético es estadísticamente equivalente al de HU3 (normal multivariada); no fue validado con similitud estadística/utilidad predictiva formal como se hizo en HU3 para los datos sintéticos crudos.
