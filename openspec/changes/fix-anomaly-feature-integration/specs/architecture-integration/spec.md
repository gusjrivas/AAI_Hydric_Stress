# Spec delta: architecture-integration

## ADDED Requirements

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
