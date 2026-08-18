# Spec delta: experiment-runner

## ADDED Requirements

### Requirement: Ejecución automatizada de una configuración experimental con múltiples semillas

El sistema DEBE poder ejecutar una configuración experimental (detección de anomalías y/o aumento sintético) sobre un dataset, repitiendo la ejecución con distintas semillas aleatorias, y devolver las métricas de desempeño de cada semilla.

#### Scenario: Una configuración con 3 semillas produce 3 filas de métricas

- **GIVEN** un dataset consolidado, una configuración experimental, y una lista de 3 semillas
- **WHEN** se ejecuta el procedimiento automatizado con esa configuración
- **THEN** el resultado tiene exactamente 3 filas, una por semilla, cada una con sus métricas de desempeño

### Requirement: Registro de parámetros, versiones y resultados en MLflow

El sistema DEBE poder registrar en MLflow los resultados de una configuración ya ejecutada: un run padre con los parámetros de la configuración y las métricas agregadas, y un run hijo anidado por cada semilla con sus propios parámetros y métricas.

#### Scenario: Registro de una configuración con sus semillas como runs anidados

- **GIVEN** los resultados de una configuración experimental ejecutada con varias semillas
- **WHEN** se registran esos resultados en MLflow
- **THEN** se crea un run padre con las métricas agregadas de la configuración, y un run hijo por cada semilla anidado bajo ese run padre
