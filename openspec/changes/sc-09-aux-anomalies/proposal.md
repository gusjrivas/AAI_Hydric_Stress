# Complemento condicional de anomalías

## Why

Implementar y validar auxiliary_anomalies_v1 solo si N=REQUIRED; ejecutar luego únicamente con autorización científica específica.

## What Changes

Trabajo futuro: condicional, no aprobado automáticamente.
No se ejecuta durante la sesión de preparación. HU7/HU8, Épica 4;
scientific-closure/experiment-runner; vínculos HU3/HU4/HU5 según afirmación.
CRISP-DM: preparación, modelado y evaluación. Configuraciones v3
base/+sintéticos/+anomalías/completa preservadas; no modifica hipótesis,
alcance ni arquitectura. Impacto futuro: evidencia auxiliar separada.

## Dependencias

sc-01-evidence-scope, sc-02-runtime-readiness
Requiere PASS de cada dependencia y aprobación del objetivo acotado.


## Archivos autorizados

Administración exclusiva del orquestador: openspec/scientific-closure/changes.json,
solo transiciones justificadas con actor, fecha, autorización, evidencia y snapshot.
Esta ruta no pertenece al implementador; no puede autoaprobar ni editar auditorías.
Gate adicional obligatorio: N REQUIRED AND sc-01/sc-02 PASS AND implementation approved; scientific execution additionally requires validated runner and authorization N; NOT_REQUIRED/UNRESOLVED blocks execution


- `src/experiment_runner/scientific_auxiliary/auxiliary_anomalies_v1.py`
- `tests/test_auxiliary_anomalies_v1.py`
- Este directorio OpenSpec: tasks.md y registros de revisión nuevos identificados.
- Gobernanza externa futura: evidence/governance/<campaign-id>/sc-09-aux-anomalies/, solo con autorización de campaña.

- Salidas auxiliares en evidence/auxiliary/sc-09-aux-anomalies/, nunca A/B/C; solo con autorización separada.

## Archivos excluidos

Todos los no listados; especialmente frontend/, backend/, data/, evidencia
histórica, controlled_daily_v3, fuentes raw, main, protocolos y grillas congeladas.
No modificar runners v4 en un change de ejecución. Un bug demostrado requiere
otro change aprobado antes de campaña; después de abrir B/C no reinicia derechos.

## Tareas y pruebas

Ver tasks.md. Requisitos: SC-GOV-023.
- `tests/test_auxiliary_anomalies_v1.py` (nuevo, todavía pendiente)

## Evidencia esperada

- `auxiliary/N/review.json`: SC-GOV-023
Guardar comando, salida, identidad y limitaciones; no convertir prueba sintética
en evidencia científica. Revisión checker, crítico y auditor por snapshot.

## Aceptación

Necesidad N=REQUIRED anterior a ejecución, diseño congelado respetado, fixtures aprobados y evidencia auditada. Si NOT_REQUIRED: solo decisión motivada, sin implementación.

## Bloqueo

UNRESOLVED/NOT_REQUIRED impide ejecutar; falta autorización o runner validado; intento de consumir 2023–2025/Balcarce.

## Riesgos

Usar complementos para cambiar selección de A o afirmar validación independiente; confundir simulación con realidad.

## Rollback

Revertir exclusivamente nuevo código antes de ejecución; después preservar todos los artefactos e intentos y documentar corrección.
No reset --hard, checkout destructivo, cambio de ramas ni eliminación de evidencia.
Un commit de checkpoint no marca este change cerrado.

## Impact

Capacidad scientific-closure. La capacidad experiment-runner conserva sus contratos.
Memoria: capítulo 2 método/limitaciones, capítulo 3 trazabilidad/implementación.
