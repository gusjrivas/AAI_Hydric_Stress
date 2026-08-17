# Spec delta: data-quality

## ADDED Requirements

### Requirement: Flujo integrado y parametrizable por configuración experimental

El sistema DEBE poder ejecutar, en un único procedimiento reproducible, el reporte de calidad, la imputación de faltantes, la partición entrenamiento/evaluación, la detección de anomalías (opcional) y la generación de datos sintéticos (opcional), de forma que las 4 configuraciones experimentales de la Épica 4 (base, +sintéticos, +anomalías, completa) se puedan seleccionar sin reescribir código. Los parámetros de estandarización DEBEN ajustarse únicamente sobre el conjunto de entrenamiento y aplicarse, sin recalcular, al conjunto de evaluación y a los datos sintéticos.

#### Scenario: Configuración base sin anomalías ni datos sintéticos

- **GIVEN** un dataset real con valores faltantes en alguna columna
- **WHEN** se ejecuta el flujo integrado con detección de anomalías y datos sintéticos desactivados
- **THEN** el conjunto de entrenamiento resultante no tiene valores faltantes, no tiene columna de anomalías, y todas sus filas tienen procedencia `real`

#### Scenario: Configuración completa con anomalías y datos sintéticos

- **GIVEN** el mismo dataset real
- **WHEN** se ejecuta el flujo integrado con detección de anomalías y datos sintéticos activados
- **THEN** el conjunto de entrenamiento resultante tiene una columna de anomalías y contiene tanto filas con procedencia `real` como filas con procedencia `sintético`

#### Scenario: Los parámetros de escalado no usan estadísticos del conjunto de evaluación

- **GIVEN** un dataset real particionado en entrenamiento y evaluación
- **WHEN** se ejecuta el flujo integrado
- **THEN** los parámetros de estandarización devueltos coinciden con la media y el desvío calculados únicamente sobre el conjunto de entrenamiento
