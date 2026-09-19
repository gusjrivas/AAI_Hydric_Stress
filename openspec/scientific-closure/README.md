# Sistema de cierre científico

Estado inicial: PREPARATION_ONLY. No constituye autorización para A/B/C, apertura
de holdout ni inicialización de ledger. El cierre del sistema de preparación y el
cierre científico del Trabajo Final son decisiones distintas.

## Contexto y autoridad

HU7/HU8, Épica 4; capacidad de gobernanza scientific-closure y capacidad ejecutable
experiment-runner. CRISP-DM: comprensión de datos, preparación, modelado, evaluación.
Vínculos a HU2 (procedencia), HU3 (calidad), HU4 (predicción), HU5 (feedback).
Impacto experimental de esta entrega: ninguno; no modifica v3, grillas, semillas,
hipótesis, propósito ni arquitectura. Justificación en memoria: capítulo 2
(método, inferencia y limitaciones), capítulo 3 (custodia y reproducibilidad).

OpenSpec es la fuente normativa del trabajo y del orden de ejecución.
Los contratos científicos permanecen en el protocolo v4 y las decisiones
preejecución: no se reemplazan por este sistema. Instrucciones explícitas del
responsable delimitan la autorización. Ante contradicción material, registrar
la fuente exacta y BLOCKED para la acción dependiente; continuar solo trabajo
independiente autorizado. No reescribir documentos históricos.

## Navegación

- [Especificación](../specs/scientific-closure/spec.md): 25 requisitos SC-GOV.
- [Matriz](traceability.md) y [registro estructurado](requirements.json).
- [Afirmaciones](claims.md), [inventario](inventory.md).
- [Plan y gates](plan.md), [operación y auditoría](operations.md).
- [Decisiones](decisions.md), [riesgos](risks.md).
- [Cambios](changes.json): dependencias y aplicabilidad.
- [Registro de preparación](preparation-validation.md).
- [Prompt siguiente](next-session.txt): reanuda preparación, no abre A/B/C.

Fuentes preservadas: openspec/project.md; openspec/specs/experiment-runner/spec.md;
docs/research/protocolo-experimental-v3.md;
docs/research/controlled-daily-v4-external-pergamino-protocol.md;
docs/research/scientific-closure-decisions.md;
docs/research/scientific-closure-preexecution-audit.md;
docs/research/scientific-closure-runbook.md;
docs/adr/0009-contratos-temporales-y-experimentos-controlados.md;
docs/adr/0010-seleccion-modelos-controlled-daily-v4.md;
docs/adr/0011-protocolo-controlled-daily-v4-external-pergamino.md.

## Alcance y exclusiones

Incluye inventario auditable, decisiones de suficiencia por afirmación, calificación
del entorno, gates A→B→C, custodia, síntesis y auditoría independiente.
Excluye ejecución científica durante preparación, inspección de holdouts cerrados,
modificación de resultados/v3/UI/main, publicación, tags, PR, merge, rebase y push.
Balcarce, sensores propios, validación agronómica, ET0, DL y nuevas variables
no son requisitos de esta campaña. R/H/N/S son condicionales, no un paquete obligatorio.

## Vocabulario

| Término | Definición |
| --- | --- |
| Evidencia técnica | Tests/fixtures/logs que verifican software; no eficacia científica |
| Evidencia científica | Artefactos de ejecución real autorizada, íntegros y contextualizados |
| Referenciada | Existencia o resultado declarado por una fuente; no revalidado aquí |
| Faltante | Artefacto exigido que no fue aportado; nunca se completa por inferencia |
| Gate científico | Condición predeclarada de avance; distinta del PASS de auditoría |
| PASS | Cumplimiento verificable del objeto auditado, identificado por snapshot |
| FAIL | Incumplimiento material demostrado; preservar hallazgo y corregir lo permitido |
| BLOCKED | Información, autoridad, capacidad o dependencia necesaria ausente/indeterminada |
| Resultado negativo válido | Resultado íntegro permitido por protocolo; no defecto de software |
| Terminal científico | C completada o detención predeclarada en A/B, con evidencia y límites |
| Cierre científico | Suficiencia del conjunto de evidencia para el alcance aprobado, auditada |
| Checkpoint | Commit recuperable de trabajo; no prueba de aceptación ni autorización |
| Identidad ejecutable | SHA del código embebido en la imagen usada en toda A→B→C |
| Identidad documental | SHA de specs/informes; puede ser posterior y debe declararse aparte |

## Formatos y ubicaciones

La evidencia científica futura reside fuera del checkout en
C:\Repo\AAI_Hydric_Stress_scientific_runtime\evidence. Ledger y backups son sus
directorios hermanos. No crear ni inicializar nada allí durante esta preparación.
Los artefactos de gobernanza de una campaña futura residen en
evidence/governance/<campaign-id>/<change-id>/; nunca son resultados del runner ni deben
escribirse dentro de A/B/C. Los nombres relativos de requirements.json son
artefactos esperados de gobernanza, no archivos ya existentes.

Cada registro de comprobación incluye: schema_version, campaign_id, change_id,
requirement_ids, timestamp_utc, actor/rol/modelo, objeto/SHA/imagen, comando,
exit_code, salida o ubicación+hash, resultado, limitaciones. Null significa
desconocido; usar estados explícitos, no valores plausibles.
Cada evidencia enlazada incluye ruta, SHA-256, tamaño, tipo (técnica/científica),
autorización aplicable y ventana temporal. Las auditorías incluyen hallazgos con
ID, severidad, requisito, ubicación, reproducción, esperado/observado y resolución.
El orquestador transcribe respuestas de lectores sin cambiar su veredicto y
conserva referencia a sesión/mensaje. El auditor no escribe archivos.
