# Spec delta: experiment-runner

## ADDED Requirements

### Requirement: Escenario de escasez de datos

El sistema DEBE poder simular escasez de datos conservando solo una fracción configurable del período de entrenamiento (las fechas más recientes antes del corte), sin alterar el período de evaluación.

#### Scenario: Reducir el entrenamiento a la mitad más reciente

- **GIVEN** un dataset con un período de entrenamiento y uno de evaluación ya definidos por una fecha de corte
- **WHEN** se aplica el escenario de escasez con una fracción de 0.5
- **THEN** el período de entrenamiento resultante contiene solo la mitad más reciente de las fechas de entrenamiento originales, y el período de evaluación no cambia

### Requirement: Escenario de ruido de datos

El sistema DEBE poder simular ruido de sensor agregando ruido gaussiano de media cero a las variables predictoras, con desvío proporcional al desvío observado de cada variable.

#### Scenario: El ruido inyectado no altera la forma del dataset

- **GIVEN** un dataset con variables predictoras numéricas
- **WHEN** se inyecta ruido gaussiano con una proporción de desvío mayor a cero
- **THEN** el dataset resultante tiene la misma forma que el original, con los valores de las variables predictoras modificados
