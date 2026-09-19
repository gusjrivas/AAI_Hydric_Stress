## ADDED Requirements

### Requirement: sc-07-aux-regression evidencia verificable del cambio

El sistema SHALL ejecutar sc-07-aux-regression únicamente con dependencias satisfechas,
aprobación de alcance y autorización científica separada cuando corresponda.
Aplica SC-GOV-021 de la capacidad scientific-closure.

#### Scenario: Cambio aceptable

- **GIVEN** dependencias con PASS y permisos suficientes
- **WHEN** se completan las tareas y se aportan los artefactos de proposal.md
- **THEN** el auditor verifica Necesidad R=REQUIRED anterior a ejecución, diseño congelado respetado, fixtures aprobados y evidencia auditada. Si NOT_REQUIRED: solo decisión motivada, sin implementación.

#### Scenario: Cambio bloqueado

- **GIVEN** UNRESOLVED/NOT_REQUIRED impide ejecutar; falta autorización o runner validado; intento de consumir 2023–2025/Balcarce.
- **WHEN** el orquestador intenta programar el cambio
- **THEN** registra BLOCKED y no ejecuta acciones dependientes
