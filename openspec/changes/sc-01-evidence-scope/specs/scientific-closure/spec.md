## ADDED Requirements

### Requirement: sc-01-evidence-scope evidencia verificable del cambio

El sistema SHALL ejecutar sc-01-evidence-scope únicamente con dependencias satisfechas,
aprobación de alcance y autorización científica separada cuando corresponda.
Aplica SC-GOV-001, SC-GOV-003, SC-GOV-004, SC-GOV-005 de la capacidad scientific-closure.

#### Scenario: Cambio aceptable

- **GIVEN** dependencias con PASS y permisos suficientes
- **WHEN** se completan las tareas y se aportan los artefactos de proposal.md
- **THEN** el auditor verifica Inventario reproducible y evaluación CL-01..10; R/H/N/S justificados; ningún cambio tácito de alcance.

#### Scenario: Cambio bloqueado

- **GIVEN** Datos de procedencia o criterio de suficiencia ausentes; afirmaciones UNRESOLVED no se dan por aceptadas.
- **WHEN** el orquestador intenta programar el cambio
- **THEN** registra BLOCKED y no ejecuta acciones dependientes
