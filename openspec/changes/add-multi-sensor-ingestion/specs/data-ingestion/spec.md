# Spec delta: data-ingestion

## ADDED Requirements

### Requirement: Convención de nombres de recursos por sensor

El sistema DEBE derivar, a partir de un `sensor_id` validado, nombres de recursos únicos y determinísticos para el dataset, el registro de retroalimentación y el modelo registrado de ese sensor, de forma que dos `sensor_id` distintos nunca produzcan el mismo nombre de recurso, y ningún `sensor_id` válido pueda producir el nombre del dataset histórico de investigación (`melchor_romero_2024_consolidado`). `sensor_id` DEBE validarse contra `^[a-zA-Z0-9_-]{1,64}$` antes de derivar cualquier nombre.

#### Scenario: Derivar nombres de recurso para un sensor válido

- **GIVEN** un `sensor_id` que cumple `^[a-zA-Z0-9_-]{1,64}$`
- **WHEN** se derivan sus nombres de dataset, feedback log y modelo registrado
- **THEN** los tres nombres incluyen ese `sensor_id` y ninguno coincide con el nombre del dataset histórico

#### Scenario: Rechazar un sensor_id inválido antes de derivar nombres

- **GIVEN** un `sensor_id` que no cumple `^[a-zA-Z0-9_-]{1,64}$` (por ejemplo, con `/`, `..` o caracteres fuera del patrón)
- **WHEN** se intenta derivar cualquiera de sus nombres de recurso
- **THEN** se levanta un error explícito, sin producir ningún nombre
