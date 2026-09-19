## ADDED Requirements

### Requirement: sc-06-scientific-synthesis evidencia verificable del cambio

El sistema SHALL ejecutar sc-06-scientific-synthesis únicamente con dependencias satisfechas,
aprobación de alcance y autorización científica separada cuando corresponda.
Aplica SC-GOV-008, SC-GOV-016, SC-GOV-025 de la capacidad scientific-closure.

#### Scenario: Cambio aceptable

- **GIVEN** dependencias con PASS y permisos suficientes
- **WHEN** se completan las tareas y se aportan los artefactos de proposal.md
- **THEN** el auditor verifica Terminal A/B/C auditado, todas obligaciones aplicables resueltas, matriz requisito→evidencia completa y PASS independiente de cierre científico.

#### Scenario: Cambio bloqueado

- **GIVEN** Terminal sin auditar, complemento REQUIRED pendiente, afirmación sin respaldo o alcance UNRESOLVED.
- **WHEN** el orquestador intenta programar el cambio
- **THEN** registra BLOCKED y no ejecuta acciones dependientes
