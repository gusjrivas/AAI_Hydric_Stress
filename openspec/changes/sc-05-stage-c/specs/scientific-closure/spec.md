## ADDED Requirements

### Requirement: sc-05-stage-c evidencia verificable del cambio

El sistema SHALL ejecutar sc-05-stage-c únicamente con dependencias satisfechas,
aprobación de alcance y autorización científica separada cuando corresponda.
Aplica SC-GOV-014 de la capacidad scientific-closure.

#### Scenario: Cambio aceptable

- **GIVEN** dependencias con PASS y permisos suficientes
- **WHEN** se completan las tareas y se aportan los artefactos de proposal.md
- **THEN** el auditor verifica Apertura trazada, resultados íntegros conservados cualquiera sea su signo y auditor PASS; ninguna selección posterior.

#### Scenario: Cambio bloqueado

- **GIVEN** B no validada; falta autorización C/inicialización; ledger ausente sin autorización, indeterminado o intento previo.
- **WHEN** el orquestador intenta programar el cambio
- **THEN** registra BLOCKED y no ejecuta acciones dependientes
