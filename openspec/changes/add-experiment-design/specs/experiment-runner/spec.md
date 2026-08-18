# Spec delta: experiment-runner

## ADDED Requirements

### Requirement: Aumento sintético del conjunto de entrenamiento sobre variables ya construidas

El sistema DEBE poder generar filas sintéticas adicionales para el conjunto de entrenamiento muestreando conjuntamente las variables predictoras ya construidas (retardos, ventanas móviles) y la variable objetivo, sin requerir una fecha ni continuidad temporal real.

#### Scenario: Las filas sintéticas quedan marcadas y con etiqueta binaria válida

- **GIVEN** un conjunto de entrenamiento con variables predictoras ya construidas y su variable objetivo binaria
- **WHEN** se generan filas sintéticas adicionales a partir de ese conjunto
- **THEN** las filas resultantes quedan marcadas con procedencia `sintetico`, y su variable objetivo toma únicamente los valores 0 o 1

### Requirement: Configuraciones comparativas de la Épica 4

El sistema DEBE poder identificar las 4 configuraciones experimentales resultantes de cruzar detección de anomalías (on/off) y aumento sintético (on/off): base, +sintéticos, +anomalías, completa.

#### Scenario: Las 4 configuraciones quedan documentadas con su combinación de factores

- **GIVEN** los dos factores de evaluación (detección de anomalías, aumento sintético)
- **WHEN** se documentan las configuraciones comparativas
- **THEN** existen exactamente 4 configuraciones, cada una con una combinación distinta de ambos factores
