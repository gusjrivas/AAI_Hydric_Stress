# Spec delta: architecture-integration

## ADDED Requirements

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
