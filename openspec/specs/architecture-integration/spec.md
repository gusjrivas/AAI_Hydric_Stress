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

El sistema DEBE calcular las variables de retardo y ventana móvil sobre la serie completa imputada, antes de partir en entrenamiento/evaluación, para que los primeros días de la partición de evaluación tengan historia disponible.

#### Scenario: Las variables de los primeros días de evaluación no quedan vacías por la partición

- **GIVEN** un dataset consolidado cuya partición de evaluación comienza inmediatamente después de la de entrenamiento
- **WHEN** se ejecuta el orquestador de punta a punta
- **THEN** las variables de retardo y ventana móvil de los primeros días de la partición de evaluación se calculan con datos de la partición de entrenamiento, sin quedar en NaN por la partición

Implementado en `src/architecture_integration/pipeline.py` (`run_end_to_end_pipeline`), testeado en `tests/test_architecture_integration_pipeline.py`. Encadena: `data_quality.imputation.interpolate_missing` → `predictive_modeling.labeling.add_stress_label` + `feature_engineering` (sobre la serie completa) → `data_quality.splitting.temporal_train_test_split` → `data_quality.anomaly_detection.detect_anomalies` (opcional, después de partir) → entrenamiento del modelo candidato → `predictive_modeling.alerts.generate_alerts` → `human_feedback.schema.init_feedback_log`.

Verificado sobre el dataset real (Melchor Romero 2024, modelo Random Forest, umbral 0.5, corte 2024-10-19): 286 filas de entrenamiento, 71 de test, 0 valores NaN en las variables predictoras del conjunto de test, 22 alertas generadas, registro de retroalimentación inicializado con 71 filas en estado `pendiente`, 15 filas marcadas `is_anomaly` en el conjunto de entrenamiento.

### Requirement: Ejecución configurable del orquestador desde línea de comandos

El sistema DEBE poder ejecutar el orquestador de punta a punta desde línea de comandos, configurando dataset, columnas, fecha de corte, modelo, umbral de alerta y detección de anomalías.

#### Scenario: Ejecución exitosa reporta un resumen del resultado

- **GIVEN** un dataset ya consolidado y disponible bajo el contrato de acceso a datos
- **WHEN** se ejecuta el script de línea de comandos con los parámetros de ese dataset
- **THEN** se reporta un resumen con al menos: filas de entrenamiento, filas de evaluación, cantidad de alertas generadas, y estados del registro de retroalimentación

Implementado en `scripts/run_end_to_end_pipeline.py`, siguiendo la misma convención que `scripts/run_data_quality_pipeline.py`. Verificado sobre el dataset real (Melchor Romero 2024, Random Forest, corte 2024-10-19): 286 filas de entrenamiento, 71 de evaluación, 22 alertas generadas, 71 filas de retroalimentación `pendiente`, 15 filas anómalas en entrenamiento — coincide exactamente con la verificación por función directa del *change* anterior.

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
