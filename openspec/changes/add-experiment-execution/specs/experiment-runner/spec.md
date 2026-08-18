# Spec delta: experiment-runner

## ADDED Requirements

### Requirement: Ejecución real de las 4 configuraciones contra el servidor MLflow

El sistema DEBE poder ejecutar las 4 configuraciones experimentales (base, +sintéticos, +anomalías, completa) con 5 semillas cada una sobre el dataset real, registrando los resultados en el servidor MLflow real (`http://localhost:5000`, ADR-0004).

#### Scenario: Las 4 configuraciones quedan registradas como runs padre distintos

- **GIVEN** el servidor MLflow real levantado (docker-compose) y el dataset consolidado real
- **WHEN** se ejecutan las 4 configuraciones experimentales con sus 5 semillas
- **THEN** el servidor MLflow tiene 4 runs padre distintos, cada uno con 5 runs hijos anidados

### Requirement: Reproducibilidad verificada entre corridas

El sistema DEBE producir métricas idénticas al re-ejecutar la misma configuración con las mismas semillas.

#### Scenario: Dos corridas de la misma configuración con las mismas semillas coinciden

- **GIVEN** una configuración experimental ya ejecutada con un conjunto de semillas
- **WHEN** se re-ejecuta esa misma configuración con las mismas semillas
- **THEN** las métricas de cada semilla son idénticas entre ambas corridas
