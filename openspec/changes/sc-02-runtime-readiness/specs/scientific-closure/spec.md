## ADDED Requirements

### Requirement: sc-02-runtime-readiness evidencia verificable del cambio

El sistema SHALL ejecutar sc-02-runtime-readiness únicamente con dependencias satisfechas,
aprobación de alcance y autorización científica separada cuando corresponda.
Aplica SC-GOV-002, SC-GOV-006, SC-GOV-007, SC-GOV-009, SC-GOV-017, SC-GOV-018, SC-GOV-019, SC-GOV-020 de la capacidad scientific-closure.

#### Scenario: Cambio aceptable

- **GIVEN** dependencias con PASS y permisos suficientes
- **WHEN** se completan las tareas y se aportan los artefactos de proposal.md
- **THEN** el auditor verifica Mecanismo de permisos por etapa verificado (B/ledger/C pueden seguir pendientes), identidad verificada, procedencia admisible, copia independiente y ensayo sintético; agentes efectivos y PASS auditor. Autorización A se exige recién al despachar A.

#### Scenario: Cambio bloqueado

- **GIVEN** Sandbox/modelo/autoridad/backup insuficientes, tensión ADR-0011 sin resolver, hash o identidad divergente.
- **WHEN** el orquestador intenta programar el cambio
- **THEN** registra BLOCKED y no ejecuta acciones dependientes
