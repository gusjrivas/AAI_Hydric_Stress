## ADDED Requirements

### Requirement: Contrato de datos comprensible para el productor
El soporte backend de UI MUST entregar fechas, unidades, nombres, procedencia,
faltantes y revisión por día. MUST NOT presentar ausencia como cero o sin alerta.

#### Scenario: Día sin estimación
- **WHEN** un slot tiene estado unavailable
- **THEN** el consumidor puede mostrar sin estimación y su motivo, sin inventar porcentaje.

#### Scenario: Datos antiguos
- **WHEN** la fecha de datos es anterior a hoy
- **THEN** la respuesta permite distinguir antigüedad y fechas reales pronosticadas.

#### Scenario: Revisión habilitada y atrasada
- **WHEN** una alerta pendiente ya alcanzó su fecha objetivo
- **THEN** review_open_at y reviewable permiten ofrecer confirmación o rechazo sin vencimiento.
