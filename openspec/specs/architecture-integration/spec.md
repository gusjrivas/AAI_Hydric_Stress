# Spec: architecture-integration

Capacidad implementada (Épica 3, HU6 — primer sub-proyecto: contratos entre componentes y orquestador de punta a punta). Origen: `openspec/changes/add-architecture-integration-pipeline/`. Este documento es la fuente de verdad vigente de la capacidad; el *change* que la originó queda como registro histórico de la decisión, no se actualiza en paralelo a este archivo.

El segundo sub-proyecto de HU6 (configuración de la ejecución completa, pruebas funcionales de integración, y ajustes/documentación de incidencias) todavía no comenzó y se documentará como *change* independiente que extiende esta spec.

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

## Limitaciones conocidas

- La generación de datos sintéticos (HU3) no está integrada en este orquestador: las filas sintéticas no tienen continuidad temporal real, y no está definido cómo calcular variables de retardo/ventana móvil para ellas. Queda como trabajo futuro para `experiment-runner` (HU7) si alguna configuración experimental lo requiere.
- El orquestador no estandariza/escala las variables predictoras, consistente con cómo se entrenaron y verificaron los modelos candidatos en HU4 (sin escalar).
- No dispara automáticamente la recalibración supervisada de HU5; eso queda como una decisión de ejecución explícita, no parte del contrato entre componentes.
- Este sub-proyecto cubre el orquestador y sus contratos, pero no incluye todavía la configuración de una ejecución completa parametrizada (ej. desde línea de comandos o configuración externa), pruebas funcionales de integración más amplias, ni el registro de incidencias/ajustes encontrados al integrar — eso corresponde al segundo *change* de HU6.
