# Spec: architecture-integration

Capacidad implementada (Épica 3, HU6 — completa, los dos sub-proyectos: contratos entre componentes/orquestador de punta a punta, y configuración de la ejecución completa/pruebas funcionales/ajustes de integración). Orígenes: `openspec/changes/add-architecture-integration-pipeline/`, `openspec/changes/add-architecture-integration-execution/`. Este documento es la fuente de verdad vigente de la capacidad; los *changes* que la originaron quedan como registro histórico de la decisión, no se actualizan en paralelo a este archivo.

## Requirements

### Requirement: Orquestación de punta a punta de las capacidades del núcleo de IA

El sistema DEBE poder ejecutar, con una única función, el flujo completo desde un dataset consolidado ya imputable hasta un registro de retroalimentación inicializado: imputación, etiquetado, ingeniería de variables, partición temporal, entrenamiento de un modelo, generación de alertas e inicialización del registro de retroalimentación.

#### Scenario: Ejecución completa produce todos los artefactos esperados

- **GIVEN** un dataset consolidado con columnas climáticas y de humedad de suelo, una fecha de corte para la partición temporal, y un modelo candidato sin entrenar
- **WHEN** se ejecuta el orquestador de punta a punta sobre ese dataset
- **THEN** el resultado incluye el reporte de calidad, las particiones de entrenamiento y evaluación con variables predictoras, el modelo entrenado, las alertas generadas sobre la partición de evaluación, y un registro de retroalimentación inicializado con esas alertas

### Requirement: Orden de etapas sin fuga temporal entre calidad y modelado

El sistema DEBE partir el dataset crudo en entrenamiento/evaluación antes de imputar y antes de calcular el umbral de la variable objetivo — ninguna de las dos operaciones puede usar información del período de evaluación. Las variables de retardo y ventana móvil, en cambio, SÍ pueden calcularse sobre la concatenación de ambas particiones ya imputadas (nunca sobre datos crudos sin partir): por construcción, solo miran hacia atrás en el tiempo (`shift`/`rolling` con ventana retrospectiva), así que los primeros días de evaluación pueden apoyarse legítimamente en la historia real de entrenamiento sin que eso constituya fuga.

**Actualización (2026-09-04):** este requirement describía, hasta esta corrección, un orden que en realidad contenía fuga temporal: la imputación (interpolación lineal bidireccional) y el umbral de la variable objetivo (percentil) se calculaban sobre el dataset completo *antes* de partir, permitiendo que ambas operaciones usaran observaciones del período de evaluación. Confirmado por auditoría metodológica de la memoria técnica y corregido sin alterar el resto de la arquitectura (ver `docs/seguimiento-tareas.md`, fila "Corrección de fuga temporal en imputación y umbral de estrés", y `docs/research/hu8-analisis-resultados.md` para el impacto sobre los resultados ya reportados en HU7/HU8).

#### Scenario: Las variables de los primeros días de evaluación no quedan vacías por la partición

- **GIVEN** un dataset consolidado cuya partición de evaluación comienza inmediatamente después de la de entrenamiento
- **WHEN** se ejecuta el orquestador de punta a punta
- **THEN** las variables de retardo y ventana móvil de los primeros días de la partición de evaluación se calculan con datos (ya imputados) de la partición de entrenamiento, sin quedar en NaN por la partición

#### Scenario: La imputación y el umbral de entrenamiento nunca usan datos de evaluación

- **GIVEN** un dataset consolidado con valores faltantes cerca del borde entre entrenamiento y evaluación
- **WHEN** se ejecuta el orquestador de punta a punta
- **THEN** la imputación del período de entrenamiento se completa únicamente con observaciones estrictamente anteriores dentro de entrenamiento, y el umbral de la variable objetivo se calcula únicamente sobre el período de entrenamiento ya imputado, antes de etiquetar evaluación con ese mismo umbral congelado

Implementado en `src/architecture_integration/pipeline.py` (`run_end_to_end_pipeline`), testeado en `tests/test_architecture_integration_pipeline.py` y `tests/test_architecture_integration_functional.py`. Encadena: `data_quality.splitting.temporal_train_test_split` (sobre el dataset crudo) → `data_quality.imputation.interpolate_missing_causal` por partición (evaluación recibe la cola de entrenamiento como semilla) → `predictive_modeling.labeling.fit_stress_threshold` (solo sobre entrenamiento) + `add_stress_label` (sobre la concatenación, con el umbral congelado) → `feature_engineering` (sobre la concatenación) → `data_quality.splitting.temporal_train_test_split` (partición final, mismo corte) → `data_quality.anomaly_detection.fit_anomaly_detector`/`apply_anomaly_detector` (opcional, ajustado solo sobre entrenamiento) → entrenamiento del modelo candidato → `predictive_modeling.alerts.generate_alerts` → `human_feedback.schema.init_feedback_log`.

Verificado sobre el dataset real (Melchor Romero 2024, modelo Random Forest, corte 2024-10-19), con el pipeline ya corregido: 292 filas de entrenamiento crudas, 74 de evaluación crudas (0 filas de entrenamiento descartadas por falta de valor previo — no hubo huecos al comienzo de la serie), umbral de estrés 0.3223 (calculado solo sobre entrenamiento), 0 valores NaN en las variables predictoras del conjunto de evaluación tras la ingeniería de variables. Ver `docs/research/hu8-analisis-resultados.md` para las métricas de desempeño completas bajo el pipeline corregido, sustancialmente distintas de las reportadas antes de esta corrección por un cambio real en la proporción de filas etiquetadas como estrés en evaluación (de ~51% a ~65%).

### Requirement: Ejecución configurable del orquestador desde línea de comandos

El sistema DEBE poder ejecutar el orquestador de punta a punta desde línea de comandos, configurando dataset, columnas, fecha de corte, modelo, umbral de alerta y detección de anomalías.

#### Scenario: Ejecución exitosa reporta un resumen del resultado

- **GIVEN** un dataset ya consolidado y disponible bajo el contrato de acceso a datos
- **WHEN** se ejecuta el script de línea de comandos con los parámetros de ese dataset
- **THEN** se reporta un resumen con al menos: filas de entrenamiento, filas de evaluación, cantidad de alertas generadas, y estados del registro de retroalimentación

Implementado en `scripts/run_end_to_end_pipeline.py`, siguiendo la misma convención que `scripts/run_data_quality_pipeline.py`. Verificado sobre el dataset real (Melchor Romero 2024, Random Forest, corte 2024-10-19), antes de la corrección de fuga temporal: 286 filas de entrenamiento, 71 de evaluación, 22 alertas generadas, 71 filas de retroalimentación `pendiente`, 15 filas anómalas en entrenamiento.

**Nota (2026-09-04):** tras la corrección de fuga temporal (ver el requirement anterior), estos números concretos del script de línea de comandos no se re-verificaron directamente — sí se re-verificó el resultado equivalente vía `run_end_to_end_pipeline` (función directa, ver requirement anterior) y vía `scripts/run_hu7_experiments.py`. Queda pendiente correr `scripts/run_end_to_end_pipeline.py` una vez más para confirmar que reporta los nuevos números (292 filas de entrenamiento crudas, umbral 0.3223, proporción de alertas más alta por el cambio de tasa base de estrés en evaluación).

### Requirement: Comportamiento correcto ante valores faltantes intercalados

El sistema DEBE producir un resultado sin valores faltantes en las variables predictoras del conjunto de evaluación incluso cuando el dataset de entrada tiene valores faltantes intercalados en la variable de humedad de suelo.

#### Scenario: Valores faltantes se interpolan antes del etiquetado y la ingeniería de variables

- **GIVEN** un dataset con algunos valores faltantes intercalados en la columna de humedad de suelo
- **WHEN** se ejecuta el orquestador de punta a punta sobre ese dataset
- **THEN** ninguna variable predictora del conjunto de evaluación queda con valores faltantes

Implementado y testeado en `tests/test_architecture_integration_functional.py` (pruebas funcionales con datos sintéticos con valores faltantes intercalados). Se verificó además que desactivar la detección de anomalías omite correctamente la columna `is_anomaly`, y que el resultado es consistente entre `train`/`test`/`feedback_log` (mismo largo, valores válidos). Las 3 pruebas pasaron sin necesidad de ajustar `run_end_to_end_pipeline` — confirman que el diseño del primer sub-proyecto de HU6 ya cubre estos escenarios.

## Limitaciones conocidas

- La generación de datos sintéticos (HU3) no está integrada en este orquestador directamente: las filas sintéticas de `data_quality.synthetic_data.generate_synthetic` no tienen continuidad temporal real. **Resuelto en `experiment-runner` (HU7)**: `add_synthetic_rows` genera filas sintéticas muestreando sobre las variables ya construidas (retardos/ventanas móviles) en vez de las columnas físicas crudas, evitando el problema de la fecha ficticia.
- El orquestador no estandariza/escala las variables predictoras, consistente con cómo se entrenaron y verificaron los modelos candidatos en HU4 (sin escalar).
- No dispara automáticamente la recalibración supervisada de HU5; eso queda como una decisión de ejecución explícita, no parte del contrato entre componentes.
- Las pruebas funcionales usan datos sintéticos de test, no el dataset real de producción — la verificación con datos reales se hizo vía el script de línea de comandos y quedó documentada con números concretos. (El dataset real de Melchor Romero 2024 sí está versionado en el repositorio desde 2026-08-17, ver ADR-0002.)
- La ejecución no está programada/automatizada (no hay scheduler); tampoco corre todavía las 4 configuraciones experimentales de la Épica 4 en una sola invocación — eso es alcance de `experiment-runner` (HU7).
- Expuesto por primera vez a través de una interfaz de usuario en `openspec/specs/alerting-ui/spec.md` (`POST /forecast/run`).

### Requirement: Uso de `is_anomaly` como variable predictora cuando la detección de anomalías está habilitada

El sistema DEBE, cuando `include_anomaly_detection=True`, incluir la marca de anomalía (`is_anomaly`) entre las variables predictoras que recibe el modelo, ajustando el detector de anomalías solo sobre el conjunto de entrenamiento y aplicándolo (sin reajustar) al conjunto de evaluación.

#### Scenario: `is_anomaly` llega al modelo cuando la detección está habilitada

- **GIVEN** un dataset y `include_anomaly_detection=True`
- **WHEN** se ejecuta `run_end_to_end_pipeline`
- **THEN** `"is_anomaly"` está presente en `feature_columns`, y el modelo se entrena y predice usando esa columna

#### Scenario: El detector de anomalías no se reajusta sobre el conjunto de evaluación

- **GIVEN** un dataset y `include_anomaly_detection=True`
- **WHEN** se ejecuta `run_end_to_end_pipeline`
- **THEN** el detector de anomalías se ajusta únicamente sobre `train`, y se usa ese mismo detector (sin reajustar) para marcar `test`

#### Scenario: Sin detección de anomalías, el comportamiento no cambia

- **GIVEN** un dataset y `include_anomaly_detection=False`
- **WHEN** se ejecuta `run_end_to_end_pipeline`
- **THEN** `"is_anomaly"` no aparece en `feature_columns`, igual que antes de este *change*

Implementado en `src/architecture_integration/pipeline.py` (`run_end_to_end_pipeline`) y `src/data_quality/anomaly_detection.py` (`fit_anomaly_detector`/`apply_anomaly_detector`). Testeado en `tests/test_architecture_integration_pipeline.py` y `tests/test_anomaly_detection.py`. Verificado sobre el dataset real: ver `openspec/specs/experiment-runner/spec.md` para el efecto medido sobre las métricas de `+anomálias`/`completa`.

### Requirement: Uso del motor de selección automática cuando no se especifica un modelo

El sistema DEBE, cuando no se provee un modelo explícito, seleccionar automáticamente el mejor modelo candidato en vez de asumir un modelo fijo; cuando sí se provee un modelo explícito, el comportamiento no cambia respecto de antes de este *change*.

#### Scenario: Sin modelo explícito, se selecciona automáticamente

- **GIVEN** un dataset y ningún modelo pasado por parámetro (`model=None`)
- **WHEN** se ejecuta `run_end_to_end_pipeline`
- **THEN** el modelo usado para predecir es el resultado de la selección automática entre candidatos, y el resultado incluye el nombre del modelo elegido

#### Scenario: Con modelo explícito, el comportamiento no cambia

- **GIVEN** un dataset y un modelo pasado por parámetro (igual que antes de este *change*)
- **WHEN** se ejecuta `run_end_to_end_pipeline`
- **THEN** se usa ese modelo tal cual (respetando `skip_fit` como hasta ahora), sin pasar por la selección automática

Implementado en `src/architecture_integration/pipeline.py` (`run_end_to_end_pipeline`). Testeado en `tests/test_architecture_integration_pipeline.py`. Verificado sobre el dataset real: ver `openspec/specs/alerting-ui/spec.md`.
