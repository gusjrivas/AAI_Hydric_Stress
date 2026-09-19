# Consolidar evidencia y auditar cierre

## Why

Evaluar suficiencia del alcance completo y redactar conclusiones honestas con memoria trazada.

## What Changes

Trabajo futuro: planificado, sujeto a aprobación y dependencias.
No se ejecuta durante la sesión de preparación. HU7/HU8, Épica 4;
scientific-closure/experiment-runner.
CRISP-DM: preparación, modelado y evaluación. Configuraciones v3
base/+sintéticos/+anomalías/completa preservadas; no modifica hipótesis,
alcance ni arquitectura. Impacto futuro: gobernanza o ejecución del protocolo v4 ya fijado.

## Dependencias

sc-01-evidence-scope, sc-02-runtime-readiness
Requiere PASS de cada dependencia y aprobación del objetivo acotado.
Además: terminal científico auditado (A sin selección, B no validada o C completada) y PASS de todos los complementos REQUIRED. C no es obligatoria si el protocolo se detiene legítimamente antes.

## Archivos autorizados

Administración exclusiva del orquestador: openspec/scientific-closure/changes.json,
solo transiciones justificadas con actor, fecha, autorización, evidencia y snapshot.
Esta ruta no pertenece al implementador; no puede autoaprobar ni editar auditorías.
Gate adicional obligatorio: Audited terminal A or B or C AND all REQUIRED auxiliaries audited; UNRESOLVED blocks closure


- `openspec/scientific-closure/inventory.md`
- `openspec/scientific-closure/claims.md`
- `openspec/scientific-closure/risks.md`
- Este directorio OpenSpec: tasks.md y registros de revisión nuevos identificados.
- Gobernanza externa futura: evidence/governance/<campaign-id>/sc-06-scientific-synthesis/, solo con autorización de campaña.



## Archivos excluidos

Todos los no listados; especialmente frontend/, backend/, data/, evidencia
histórica, controlled_daily_v3, fuentes raw, main, protocolos y grillas congeladas.
No modificar runners v4 en un change de ejecución. Un bug demostrado requiere
otro change aprobado antes de campaña; después de abrir B/C no reinicia derechos.

## Tareas y pruebas

Ver tasks.md. Requisitos: SC-GOV-008, SC-GOV-016, SC-GOV-025.
- `tests/test_scientific_closure_governance.py`

## Evidencia esperada

- `audit.json`: SC-GOV-008
- `claim-evidence-review.json`: SC-GOV-016
- `scientific-closure-audit.json`: SC-GOV-025
Guardar comando, salida, identidad y limitaciones; no convertir prueba sintética
en evidencia científica. Revisión checker, crítico y auditor por snapshot.

## Aceptación

Terminal A/B/C auditado, todas obligaciones aplicables resueltas, matriz requisito→evidencia completa y PASS independiente de cierre científico.

## Bloqueo

Terminal sin auditar, complemento REQUIRED pendiente, afirmación sin respaldo o alcance UNRESOLVED.

## Riesgos

Declarar tesis cerrada solo por tests verdes o por éxito de clasificación P20.

## Rollback

Retirar solo nuevas afirmaciones incorrectas con corrección trazable; no modificar evidencia fuente ni esconder resultados.
No reset --hard, checkout destructivo, cambio de ramas ni eliminación de evidencia.
Un commit de checkpoint no marca este change cerrado.

## Impact

Capacidad scientific-closure. La capacidad experiment-runner conserva sus contratos.
Memoria: capítulo 2 método/limitaciones, capítulo 3 trazabilidad/implementación.
