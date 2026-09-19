## ADDED Requirements

### Requirement: sc-03-stage-a evidencia verificable del cambio

El sistema SHALL ejecutar sc-03-stage-a únicamente con dependencias satisfechas,
aprobación de alcance y autorización científica separada cuando corresponda.
Aplica SC-GOV-010, SC-GOV-011, SC-GOV-015 de la capacidad scientific-closure.

#### Scenario: Cambio aceptable

- **GIVEN** dependencias con PASS y permisos suficientes
- **WHEN** se completan las tareas y se aportan los artefactos de proposal.md
- **THEN** el auditor verifica Artefactos íntegros de A y auditor PASS sobre protocolo; gate A transferible o terminal negativo/insuficiencia documentado.

#### Scenario: Cambio bloqueado

- **GIVEN** Sin autorización A, soporte insuficiente para avanzar a B, error técnico o procedencia inválida.
- **WHEN** el orquestador intenta programar el cambio
- **THEN** registra BLOCKED y no ejecuta acciones dependientes
