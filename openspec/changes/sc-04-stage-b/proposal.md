# Evaluar candidato único en B

## Why

Reservar y evaluar una vez 2023 con candidato primario congelado de A.

## What Changes

Trabajo futuro: planificado, sujeto a aprobación y dependencias.
No se ejecuta durante la sesión de preparación. HU7/HU8, Épica 4;
scientific-closure/experiment-runner.
CRISP-DM: preparación, modelado y evaluación. Configuraciones v3
base/+sintéticos/+anomalías/completa preservadas; no modifica hipótesis,
alcance ni arquitectura. Impacto futuro: gobernanza o ejecución del protocolo v4 ya fijado.

## Dependencias

sc-03-stage-a
Requiere PASS de cada dependencia y aprobación del objetivo acotado.


## Archivos autorizados

Administración exclusiva del orquestador: openspec/scientific-closure/changes.json,
solo transiciones justificadas con actor, fecha, autorización, evidencia y snapshot.
Esta ruta no pertenece al implementador; no puede autoaprobar ni editar auditorías.
Gate adicional obligatorio: sc-03 PASS AND A scientific_run AND primary_selection AND candidate_produced AND support valid AND authorization B recorded AND custody unused; NO_VALID_SELECTION blocks B


Ningún archivo de código/configuración del checkout.
- Este directorio OpenSpec: tasks.md y registros de revisión nuevos identificados.
- Gobernanza externa futura: evidence/governance/<campaign-id>/sc-04-stage-b/, solo con autorización de campaña.
- Salida científica de su etapa A/B/C y registro persistente correspondiente únicamente según runbook y autorización específica.


## Archivos excluidos

Todos los no listados; especialmente frontend/, backend/, data/, evidencia
histórica, controlled_daily_v3, fuentes raw, main, protocolos y grillas congeladas.
No modificar runners v4 en un change de ejecución. Un bug demostrado requiere
otro change aprobado antes de campaña; después de abrir B/C no reinicia derechos.

## Tareas y pruebas

Ver tasks.md. Requisitos: SC-GOV-012, SC-GOV-013.
- `tests/test_controlled_daily_v4_stage_b_runner.py`
- `tests/test_controlled_daily_v4_stage_b_integration.py`
- `tests/test_controlled_daily_v4_scientific_closure.py`

## Evidencia esperada

- `B/gate-review.json`: SC-GOV-012
- `B/custody-review.json`: SC-GOV-013
Guardar comando, salida, identidad y limitaciones; no convertir prueba sintética
en evidencia científica. Revisión checker, crítico y auditor por snapshot.

## Aceptación

Reserva y artefactos íntegros; PASS auditor sobre ejecución; C solo si CANDIDATE_VALIDATED.

## Bloqueo

Gate A sin candidato, sin autorización B, intento previo/incierto, identidad distinta; negativo bloquea C.

## Riesgos

Cambiar output/candidato para eludir intento único o confundir FAIL técnico y no validación científica.

## Rollback

SOLO recuperación de artefactos completos con hashes y motivo; nunca reentrenar, liberar reserva ni repetir con otro candidato.
No reset --hard, checkout destructivo, cambio de ramas ni eliminación de evidencia.
Un commit de checkpoint no marca este change cerrado.

## Impact

Capacidad scientific-closure. La capacidad experiment-runner conserva sus contratos.
Memoria: capítulo 2 método/limitaciones, capítulo 3 trazabilidad/implementación.
