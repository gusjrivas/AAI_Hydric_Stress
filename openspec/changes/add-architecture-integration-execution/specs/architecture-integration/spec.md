# Spec delta: architecture-integration

## ADDED Requirements

### Requirement: Ejecución configurable del orquestador desde línea de comandos

El sistema DEBE poder ejecutar el orquestador de punta a punta desde línea de comandos, configurando dataset, columnas, fecha de corte, modelo, umbral de alerta y detección de anomalías.

#### Scenario: Ejecución exitosa reporta un resumen del resultado

- **GIVEN** un dataset ya consolidado y disponible bajo el contrato de acceso a datos
- **WHEN** se ejecuta el script de línea de comandos con los parámetros de ese dataset
- **THEN** se reporta un resumen con al menos: filas de entrenamiento, filas de evaluación, cantidad de alertas generadas, y estados del registro de retroalimentación

### Requirement: Comportamiento correcto ante valores faltantes intercalados

El sistema DEBE producir un resultado sin valores faltantes en las variables predictoras del conjunto de evaluación incluso cuando el dataset de entrada tiene valores faltantes intercalados en la variable de humedad de suelo.

#### Scenario: Valores faltantes se interpolan antes del etiquetado y la ingeniería de variables

- **GIVEN** un dataset con algunos valores faltantes intercalados en la columna de humedad de suelo
- **WHEN** se ejecuta el orquestador de punta a punta sobre ese dataset
- **THEN** ninguna variable predictora del conjunto de evaluación queda con valores faltantes
