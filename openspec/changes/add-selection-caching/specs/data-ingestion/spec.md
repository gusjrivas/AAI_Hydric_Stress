# Spec delta: data-ingestion

## ADDED Requirements

### Requirement: Huella del dataset para detectar cambios sin leer su contenido

El sistema DEBE poder obtener una huella (fingerprint) barata de un dataset ya guardado, que cambie si y solo si el archivo fue reescrito, sin necesidad de leer su contenido.

#### Scenario: La huella cambia cuando el dataset se reescribe

- **GIVEN** un dataset ya guardado con `save_dataset`
- **WHEN** se reescribe ese mismo dataset con `save_dataset` (mismos o distintos datos) y se calcula la huella antes y después
- **THEN** las dos huellas son distintas

#### Scenario: La huella es estable si el dataset no cambia

- **GIVEN** un dataset ya guardado
- **WHEN** se calcula la huella dos veces sin modificar el archivo entre medio
- **THEN** las dos huellas son idénticas
