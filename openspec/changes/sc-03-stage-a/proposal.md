# Ejecutar y auditar A autorizada

## Why

Producir comparación interna 2015–2022 y candidato congelado o terminal NO_VALID_SELECTION.

## What Changes

Trabajo futuro: planificado, sujeto a aprobación y dependencias.
No se ejecuta durante la sesión de preparación. HU7/HU8, Épica 4;
scientific-closure/experiment-runner.
CRISP-DM: preparación, modelado y evaluación. Configuraciones v3
base/+sintéticos/+anomalías/completa preservadas; no modifica hipótesis,
alcance ni arquitectura. Impacto futuro: gobernanza o ejecución del protocolo v4 ya fijado.

## Dependencias

sc-02-runtime-readiness
Requiere PASS de cada dependencia y aprobación del objetivo acotado.


## Archivos autorizados

Administración exclusiva del orquestador: openspec/scientific-closure/changes.json,
solo transiciones justificadas con actor, fecha, autorización, evidencia y snapshot.
Esta ruta no pertenece al implementador; no puede autoaprobar ni editar auditorías.
Gate adicional obligatorio: sc-02 PASS AND G1 satisfied AND authorization A recorded AND fixed executable/image verified


Ningún archivo de código/configuración del checkout.
- Este directorio OpenSpec: tasks.md y registros de revisión nuevos identificados.
- Gobernanza externa futura: evidence/governance/<campaign-id>/sc-03-stage-a/, solo con autorización de campaña.
- Salida científica de su etapa A/B/C y registro persistente correspondiente únicamente según runbook y autorización específica.


## Archivos excluidos

Todos los no listados; especialmente frontend/, backend/, data/, evidencia
histórica, controlled_daily_v3, fuentes raw, main, protocolos y grillas congeladas.
No modificar runners v4 en un change de ejecución. Un bug demostrado requiere
otro change aprobado antes de campaña; después de abrir B/C no reinicia derechos.

## Tareas y pruebas

Ver tasks.md. Requisitos: SC-GOV-010, SC-GOV-011, SC-GOV-015.
- `tests/test_controlled_daily_v4_stage_a_integration.py`
- `tests/test_controlled_daily_v4_selection.py`
- `tests/test_controlled_daily_v4_freezing.py`
- `tests/test_controlled_daily_v4_bootstrap.py`
- `tests/test_controlled_daily_v4_stage_window.py`

## Evidencia esperada

- `temporal-contract-check.json`: SC-GOV-010
- `A/gate-review.json`: SC-GOV-011
- `statistical-review.json`: SC-GOV-015
Guardar comando, salida, identidad y limitaciones; no convertir prueba sintética
en evidencia científica. Revisión checker, crítico y auditor por snapshot.

## Aceptación

Artefactos íntegros de A y auditor PASS sobre protocolo; gate A transferible o terminal negativo/insuficiencia documentado.

## Bloqueo

Sin autorización A, soporte insuficiente para avanzar a B, error técnico o procedencia inválida.

## Riesgos

Usar datos posteriores a 2022 o congelar hiperparámetros con resultados de B/C.

## Rollback

Preservar salida parcial y bitácora; no sobrescribir. Falla técnica requiere diagnóstico predeclarado, no repetición oportunista.
No reset --hard, checkout destructivo, cambio de ramas ni eliminación de evidencia.
Un commit de checkpoint no marca este change cerrado.

## Impact

Capacidad scientific-closure. La capacidad experiment-runner conserva sus contratos.
Memoria: capítulo 2 método/limitaciones, capítulo 3 trazabilidad/implementación.
