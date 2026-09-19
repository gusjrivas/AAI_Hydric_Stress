# Evaluar holdout final bajo custodia

## Why

Abrir una sola vez 2024–2025 luego de B validada y autorización adicional.

## What Changes

Trabajo futuro: planificado, sujeto a aprobación y dependencias.
No se ejecuta durante la sesión de preparación. HU7/HU8, Épica 4;
scientific-closure/experiment-runner.
CRISP-DM: preparación, modelado y evaluación. Configuraciones v3
base/+sintéticos/+anomalías/completa preservadas; no modifica hipótesis,
alcance ni arquitectura. Impacto futuro: gobernanza o ejecución del protocolo v4 ya fijado.

## Dependencias

sc-04-stage-b
Requiere PASS de cada dependencia y aprobación del objetivo acotado.


## Archivos autorizados

Administración exclusiva del orquestador: openspec/scientific-closure/changes.json,
solo transiciones justificadas con actor, fecha, autorización, evidencia y snapshot.
Esta ruta no pertenece al implementador; no puede autoaprobar ni editar auditorías.
Gate adicional obligatorio: sc-04 PASS AND B CANDIDATE_VALIDATED AND authorization C recorded AND ledger initialization separately authorized AND custody admissible; CANDIDATE_NOT_VALIDATED blocks C


Ningún archivo de código/configuración del checkout.
- Este directorio OpenSpec: tasks.md y registros de revisión nuevos identificados.
- Gobernanza externa futura: evidence/governance/<campaign-id>/sc-05-stage-c/, solo con autorización de campaña.
- Salida científica de su etapa A/B/C y registro persistente correspondiente únicamente según runbook y autorización específica.


## Archivos excluidos

Todos los no listados; especialmente frontend/, backend/, data/, evidencia
histórica, controlled_daily_v3, fuentes raw, main, protocolos y grillas congeladas.
No modificar runners v4 en un change de ejecución. Un bug demostrado requiere
otro change aprobado antes de campaña; después de abrir B/C no reinicia derechos.

## Tareas y pruebas

Ver tasks.md. Requisitos: SC-GOV-014.
- `tests/test_controlled_daily_v4_stage_c_admissibility.py`
- `tests/test_controlled_daily_v4_holdout_ledger.py`
- `tests/test_controlled_daily_v4_stage_c_recovery.py`
- `tests/test_controlled_daily_v4_stage_c_integration.py`

## Evidencia esperada

- `C/holdout-review.json`: SC-GOV-014
Guardar comando, salida, identidad y limitaciones; no convertir prueba sintética
en evidencia científica. Revisión checker, crítico y auditor por snapshot.

## Aceptación

Apertura trazada, resultados íntegros conservados cualquiera sea su signo y auditor PASS; ninguna selección posterior.

## Bloqueo

B no validada; falta autorización C/inicialización; ledger ausente sin autorización, indeterminado o intento previo.

## Riesgos

Apertura irreversible o restauración de backup para repetir holdout.

## Rollback

No existe rollback de conocimiento adquirido; custodiar intento. Recuperación idempotente solo resultado completo íntegro y ledger original.
No reset --hard, checkout destructivo, cambio de ramas ni eliminación de evidencia.
Un commit de checkpoint no marca este change cerrado.

## Impact

Capacidad scientific-closure. La capacidad experiment-runner conserva sus contratos.
Memoria: capítulo 2 método/limitaciones, capítulo 3 trazabilidad/implementación.
