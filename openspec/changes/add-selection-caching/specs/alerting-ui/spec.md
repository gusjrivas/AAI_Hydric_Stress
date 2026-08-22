# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Reutilización del modelo auto-seleccionado mientras el dataset no cambie

El sistema DEBE reutilizar, sin volver a seleccionar, el último modelo auto-seleccionado mientras el dataset consolidado no haya cambiado; DEBE volver a seleccionar cuando el dataset cambie o cuando todavía no exista un modelo cacheado. Este comportamiento solo aplica cuando no hay un modelo recalibrado registrado — la prioridad de un modelo recalibrado sobre la selección automática no cambia.

#### Scenario: El dataset no cambió entre dos corridas

- **GIVEN** un modelo ya auto-seleccionado en una corrida anterior, sin modelo recalibrado registrado, y el dataset consolidado sin cambios
- **WHEN** se ejecuta una nueva corrida
- **THEN** se reutiliza el mismo modelo cacheado sin volver a seleccionar

#### Scenario: El dataset cambió entre dos corridas

- **GIVEN** un modelo ya auto-seleccionado en una corrida anterior, sin modelo recalibrado registrado, y el dataset consolidado modificado desde esa corrida
- **WHEN** se ejecuta una nueva corrida
- **THEN** se vuelve a seleccionar el mejor candidato, y el resultado reemplaza al modelo cacheado

#### Scenario: Un modelo recalibrado sigue teniendo prioridad sobre el caché

- **GIVEN** un modelo recalibrado registrado en MLflow y, además, un modelo auto-seleccionado ya cacheado
- **WHEN** se ejecuta una nueva corrida
- **THEN** se usa el modelo recalibrado, ignorando el caché de selección automática
