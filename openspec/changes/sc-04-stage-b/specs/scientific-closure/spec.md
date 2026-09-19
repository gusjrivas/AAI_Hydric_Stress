## ADDED Requirements

### Requirement: sc-04-stage-b evidencia verificable del cambio

El sistema SHALL ejecutar sc-04-stage-b únicamente con dependencias satisfechas,
aprobación de alcance y autorización científica separada cuando corresponda.
Aplica SC-GOV-012, SC-GOV-013 de la capacidad scientific-closure.

#### Scenario: Cambio aceptable

- **GIVEN** dependencias con PASS y permisos suficientes
- **WHEN** se completan las tareas y se aportan los artefactos de proposal.md
- **THEN** el auditor verifica Reserva y artefactos íntegros; PASS auditor sobre ejecución; C solo si CANDIDATE_VALIDATED.

#### Scenario: Cambio bloqueado

- **GIVEN** Gate A sin candidato, sin autorización B, intento previo/incierto, identidad distinta; negativo bloquea C.
- **WHEN** el orquestador intenta programar el cambio
- **THEN** registra BLOCKED y no ejecuta acciones dependientes
