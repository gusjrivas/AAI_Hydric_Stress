# Spec delta: human-feedback

## ADDED Requirements

### Requirement: Esquema de registro de retroalimentación

El sistema DEBE poder representar, por cada alerta generada, un registro de retroalimentación con: fecha, valor de la alerta, estado de validación (`pendiente`, `confirmada` o `rechazada`), una etiqueta corregida opcional, y una observación textual opcional.

#### Scenario: Inicialización de un registro de retroalimentación a partir de alertas generadas

- **GIVEN** un conjunto de alertas generadas con sus fechas
- **WHEN** se inicializa el registro de retroalimentación a partir de esas alertas
- **THEN** cada alerta queda representada con estado de validación `pendiente` y sin corrección ni observación

### Requirement: Actualización del estado de validación de una alerta

El sistema DEBE poder actualizar el estado de validación de una alerta puntual, identificada por su fecha, agregando opcionalmente una etiqueta corregida y una observación.

#### Scenario: Confirmar una alerta

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se confirma esa alerta
- **THEN** su estado de validación pasa a `confirmada`

#### Scenario: Rechazar una alerta con corrección

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se rechaza esa alerta indicando una etiqueta corregida y una observación
- **THEN** su estado de validación pasa a `rechazada`, y la etiqueta corregida y la observación quedan guardadas en esa fila
