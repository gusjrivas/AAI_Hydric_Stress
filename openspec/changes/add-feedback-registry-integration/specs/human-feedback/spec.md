# Spec delta: human-feedback

## ADDED Requirements

### Requirement: Persistencia del registro de retroalimentación

El sistema DEBE poder guardar y recuperar un registro de retroalimentación en disco, reutilizando el contrato de acceso a datos ya establecido (`load_dataset`/`save_dataset`).

#### Scenario: Guardar y recuperar un registro sin pérdida de información

- **GIVEN** un registro de retroalimentación con alertas en distintos estados de validación
- **WHEN** se guarda y luego se recupera con el mismo nombre
- **THEN** el registro recuperado es igual al original, incluyendo estados, correcciones y observaciones

### Requirement: Actualización del registro sin pérdida de validaciones existentes

El sistema DEBE poder combinar un registro de retroalimentación existente con alertas recién generadas, agregando las fechas nuevas en estado `pendiente` y preservando el estado de validación, la corrección y la observación de las fechas ya presentes.

#### Scenario: Nuevas alertas se agregan sin afectar validaciones previas

- **GIVEN** un registro de retroalimentación existente con una fecha ya `confirmada`, y un conjunto de alertas recién generadas que incluye esa misma fecha (con un valor de alerta distinto) más una fecha nueva
- **WHEN** se combina el registro existente con las alertas nuevas
- **THEN** la fecha ya `confirmada` conserva su estado de validación sin cambios, y la fecha nueva queda `pendiente`

### Requirement: Integración de la retroalimentación con los registros de predicción

El sistema DEBE poder unir, por fecha, el registro de retroalimentación con la probabilidad predicha y la etiqueta real del modelo para esa misma fecha.

#### Scenario: Unión de retroalimentación con probabilidad predicha y etiqueta real

- **GIVEN** un registro de retroalimentación y un conjunto de predicciones con fecha, probabilidad predicha y etiqueta real
- **WHEN** se integran ambos conjuntos
- **THEN** cada fila del resultado contiene, para la misma fecha, el estado de validación, la corrección/observación (si existen), la probabilidad predicha y la etiqueta real
