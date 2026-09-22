# Inventario y suficiencia por afirmación

## Why

Contrastar el inventario permitido y fijar afirmaciones/obligaciones de evidencia sin abrir B/C.

## What Changes

Trabajo futuro: planificado, sujeto a aprobación y dependencias.
No se ejecuta durante la sesión de preparación. HU7/HU8, Épica 4;
scientific-closure/experiment-runner.
CRISP-DM: preparación, modelado y evaluación. Configuraciones v3
base/+sintéticos/+anomalías/completa preservadas; no modifica hipótesis,
alcance ni arquitectura. Impacto futuro: gobernanza o ejecución del protocolo v4 ya fijado.

## Dependencias

Ninguna; verificar identidad y autorización de trabajo.
Requiere PASS de cada dependencia y aprobación del objetivo acotado.


## Archivos autorizados

Administración exclusiva del orquestador: openspec/scientific-closure/changes.json,
solo transiciones justificadas con actor, fecha, autorización, evidencia y snapshot.
Esta ruta no pertenece al implementador; no puede autoaprobar ni editar auditorías.
Gate adicional obligatorio: Identity verified AND preparation scope authorized; do not read closed holdouts


- `openspec/scientific-closure/inventory.md`
- `openspec/scientific-closure/claims.md`
- `openspec/scientific-closure/decisions.md`
- Este directorio OpenSpec: tasks.md y registros de revisión nuevos identificados.
- Gobernanza externa futura: evidence/governance/<campaign-id>/sc-01-evidence-scope/, solo con autorización de campaña.



## Archivos excluidos

Todos los no listados; especialmente frontend/, backend/, data/, evidencia
histórica, controlled_daily_v3, fuentes raw, main, protocolos y grillas congeladas.
No modificar runners v4 en un change de ejecución. Un bug demostrado requiere
otro change aprobado antes de campaña; después de abrir B/C no reinicia derechos.

## Tareas y pruebas

Ver tasks.md. Requisitos: SC-GOV-001, SC-GOV-003, SC-GOV-004, SC-GOV-005.
- `tests/test_scientific_closure_governance.py`

## Evidencia esperada

- `session-identity.json`: SC-GOV-001
- `preservation.json`: SC-GOV-003
- `inventory.json`: SC-GOV-004
- `claims-assessment.json`: SC-GOV-005
Guardar comando, salida, identidad y limitaciones; no convertir prueba sintética
en evidencia científica. Revisión checker, crítico y auditor por snapshot.

## Aceptación

Inventario reproducible y evaluación CL-01..10; R/H/N/S justificados; ningún cambio tácito de alcance.

## Bloqueo

Datos de procedencia o criterio de suficiencia ausentes; afirmaciones UNRESOLVED no se dan por aceptadas.

## Riesgos

Confundir ausencia de beneficio con defecto o aceptar evidencia funcional como causal.

## Rollback

Revertir solo documentación nueva revisada; preservar historial, hash y decisiones anteriores.
No reset --hard, checkout destructivo, cambio de ramas ni eliminación de evidencia.
Un commit de checkpoint no marca este change cerrado.

## Impact

Capacidad scientific-closure. La capacidad experiment-runner conserva sus contratos.
Memoria: capítulo 2 método/limitaciones, capítulo 3 trazabilidad/implementación.
