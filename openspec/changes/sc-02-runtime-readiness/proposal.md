# Calificar entorno, custodia y autoridad

## Why

Resolver prerrequisitos operativos y normativos antes de autorizar cualquier campaña.

## What Changes

Trabajo futuro: planificado, sujeto a aprobación y dependencias.
No se ejecuta durante la sesión de preparación. HU7/HU8, Épica 4;
scientific-closure/experiment-runner.
CRISP-DM: preparación, modelado y evaluación. Configuraciones v3
base/+sintéticos/+anomalías/completa preservadas; no modifica hipótesis,
alcance ni arquitectura. Impacto futuro: gobernanza o ejecución del protocolo v4 ya fijado.

## Dependencias

sc-01-evidence-scope
Requiere PASS de cada dependencia y aprobación del objetivo acotado.


## Archivos autorizados

Administración exclusiva del orquestador: openspec/scientific-closure/changes.json,
solo transiciones justificadas con actor, fecha, autorización, evidencia y snapshot.
Esta ruta no pertenece al implementador; no puede autoaprobar ni editar auditorías.
Gate adicional obligatorio: sc-01 PASS AND preparation approved; verify authorization mechanism, not future B/C permissions; unresolved runtime/provenance/ADR/backup blocks campaign


- `openspec/scientific-closure/decisions.md`
- `openspec/scientific-closure/risks.md`
- `openspec/scientific-closure/preparation-validation.md`
- Este directorio OpenSpec: tasks.md y registros de revisión nuevos identificados.
- Gobernanza externa futura: evidence/governance/<campaign-id>/sc-02-runtime-readiness/, solo con autorización de campaña.



## Archivos excluidos

Todos los no listados; especialmente frontend/, backend/, data/, evidencia
histórica, controlled_daily_v3, fuentes raw, main, protocolos y grillas congeladas.
No modificar runners v4 en un change de ejecución. Un bug demostrado requiere
otro change aprobado antes de campaña; después de abrir B/C no reinicia derechos.

## Tareas y pruebas

Ver tasks.md. Requisitos: SC-GOV-002, SC-GOV-006, SC-GOV-007, SC-GOV-009, SC-GOV-017, SC-GOV-018, SC-GOV-019, SC-GOV-020.
- `tests/test_scientific_closure_governance.py`
- `tests/test_controlled_daily_v4_environment_validation.py`
- `tests/test_controlled_daily_v4_reproducibility_artifacts.py`
- `tests/test_controlled_daily_v4_stage_c_recovery.py`

## Evidencia esperada

- `authorizations.json`: SC-GOV-002
- `agent-capabilities.json`: SC-GOV-006
- `workflow-events.jsonl`: SC-GOV-007
- `execution-manifest.json`: SC-GOV-009
- `provenance-assessment.json`: SC-GOV-017
- `recovery-rehearsal.json`: SC-GOV-018
- `checkpoints.json`: SC-GOV-019
- `structural-validation.json`: SC-GOV-020
Guardar comando, salida, identidad y limitaciones; no convertir prueba sintética
en evidencia científica. Revisión checker, crítico y auditor por snapshot.

## Aceptación

Mecanismo de permisos por etapa verificado (B/ledger/C pueden seguir pendientes), identidad verificada, procedencia admisible, copia independiente y ensayo sintético; agentes efectivos y PASS auditor. Autorización A se exige recién al despachar A.

## Bloqueo

Sandbox/modelo/autoridad/backup insuficientes, tensión ADR-0011 sin resolver, hash o identidad divergente.

## Riesgos

Inicializar ledger prematuramente o tratar un SHA documental como ejecutable.

## Rollback

Descartar solo fixtures propios tras registrar hashes; nunca restaurar estado científico anterior ni borrar registros.
No reset --hard, checkout destructivo, cambio de ramas ni eliminación de evidencia.
Un commit de checkpoint no marca este change cerrado.

## Impact

Capacidad scientific-closure. La capacidad experiment-runner conserva sus contratos.
Memoria: capítulo 2 método/limitaciones, capítulo 3 trazabilidad/implementación.
