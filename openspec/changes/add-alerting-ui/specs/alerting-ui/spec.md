# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Ejecución de pronóstico desde la interfaz

El sistema DEBE poder ejecutar el pipeline completo (calidad, modelado, alertas) sobre el dataset consolidado configurado, y devolver un veredicto por fecha (alerta sí/no, probabilidad) sin exponer qué modelo lo generó.

#### Scenario: Correr un pronóstico produce alertas y persiste el feedback inicial

- **GIVEN** un dataset consolidado disponible bajo el nombre configurado por variable de entorno
- **WHEN** se invoca el endpoint de ejecución de pronóstico
- **THEN** se devuelve una lista de veredictos por fecha (fecha, alerta, probabilidad), y el registro de retroalimentación queda persistido con esas fechas en estado `pendiente` (o conservando su estado previo si ya existían)

### Requirement: Consulta y validación humana de alertas

El sistema DEBE poder listar el registro de retroalimentación persistido, y permitir confirmar o rechazar una alerta puntual identificada por fecha.

#### Scenario: Confirmar una alerta vía la API

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se invoca el endpoint de confirmación para esa fecha
- **THEN** el registro persistido queda con esa fecha en estado `confirmada`

#### Scenario: Rechazar una alerta con corrección vía la API

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se invoca el endpoint de rechazo para esa fecha, con una etiqueta corregida y una observación
- **THEN** el registro persistido queda con esa fecha en estado `rechazada`, con la corrección y la observación guardadas
