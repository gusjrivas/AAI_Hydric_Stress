# Backend para la UI orientada al productor

Estado: aceptado por el autor el 2026-09-19; implementación incremental en
`feat/hu6-backend-soporte-ui`. No modifica `main`, specs canónicas ni resultados
históricos hasta completar validación y cierre de cada change.

## Objetivo y decisiones de usuario
Dar soporte a sectores con nombres reconocibles, registros de sensores, tres
pronósticos diarios y revisión humana desde el día objetivo, sin vencimiento.
La UI usa datos y estados de la API; no infiere una alerta negativa cuando falta
una estimación. Sensores son fuentes de datos; IA sigue siendo el núcleo.

## Changes y dependencias
| Change | HU / capacidad | Responsabilidad |
|---|---|---|
| [add-producer-sensor-catalog](../../openspec/changes/add-producer-sensor-catalog/proposal.md) | HU2 / data-ingestion | Catálogo y consulta consistente de lecturas |
| [add-daily-multihorizon-predictors](../../openspec/changes/add-daily-multihorizon-predictors/proposal.md) | HU4 / predictive-modeling | Estimaciones independientes +1/+2/+3 y evaluación |
| [extend-dated-alert-feedback](../../openspec/changes/extend-dated-alert-feedback/proposal.md) | HU5 / human-feedback | Identidad por emisión, revisión y madurez |
| [add-producer-forecast-api](../../openspec/changes/add-producer-forecast-api/proposal.md) | HU6 / architecture-integration, alerting-ui | Orquestación, contratos HTTP y compatibilidad |

Se puede desarrollar catálogo y registro de feedback en forma independiente,
usando fixtures de contrato. La emisión real depende del modelado; la integración
final depende de los tres changes. No se prescribe ejecución paralela de agentes.

## Orden de entregas
1. Revisar estos contratos y el [ADR propuesto](../adr/0013-backend-ui-productor.md).
2. Resolver viabilidad +1/+2/+3 con fixtures y evaluación de desarrollo predeclarada.
   Es la incertidumbre principal: una demo visual no acredita capacidad predictiva.
3. Catálogo, historial y feedback persistente, con contratos probados.
4. API v2 y recorrido integrado; después integrar en la rama UI.
5. Solo proponer merge a main con pruebas, revisión manual y aprobación del usuario.

## Límites explícitos
- No cambiar controlled_daily_v3 ni controlled_daily_v4_external_pergamino,
  abrir holdouts, modificar ledgers o reutilizar evidencia formal para ajustar.
- El contrato operativo nuevo será versionado; no altera modelos ya emitidos.
- Guardar una opinión el mismo día NO la convierte en target diario maduro.
  El detalle normativo está en extend-dated-alert-feedback.
- No fusionar series de varios sensores ni convertir humedad en diagnóstico
  fisiológico. No generar comandos de riego.
- Cuaderno de observaciones libres: fuera de estas entregas; requiere otro change.
  Este alcance guarda observaciones vinculadas a pronósticos.
- No migrar automáticamente los cambios locales de historial de la rama UI.
  En este checkout base PR #205 todavía no existe el nuevo GET de historial.
  La implementación debe conciliar ese trabajo, sin duplicarlo.
- Solo documentación en este conjunto de commits. Todas las tareas de código
  permanecen sin marcar.

## Contrato compartido y criterio de cierre
La fuente de verdad de rutas, campos y códigos es
[api-contract.md](../../openspec/changes/add-producer-forecast-api/api-contract.md).
Los diseños de núcleo establecen semántica, no duplican rutas HTTP.
Requeridos: tres slots de horizonte, aislamiento, ausencia/error/faltantes,
fechas confiables, revisiones persistentes tras reinicio, idempotencia, contrato
legacy y demo #202–#205 sin regresiones. Sin fecha simulada en la API de producción.
La evaluación de porcentajes puede resultar no aprobada: el contrato debe
declararlo y la UI no mostrar una probabilidad como validada en ese caso.

## Trazabilidad
CRISP-DM: comprensión/preparación de datos, modelado, evaluación de desarrollo
y despliegue e integración. Épicas 1, 2 y 3 según change. Capítulos 2 y 3.
HU7/HU8: se conserva evidencia formal; nueva evaluación no se presenta como
resultado formal de esos protocolos. No se cambia hipótesis ni alcance de tesis.

## Validación de estas especificaciones
Los cuatro changes pasan openspec validate <change> --strict. Se verificaron
además enlaces relativos, ejemplo JSON, escenarios y tareas sin marcar.
El validador advierte un problema PREEXISTENTE en la spec canónica
architecture-integration: los requisitos ubicados actualmente en líneas 78 y 102
están fuera de su sección Requirements. No invalida estos deltas, pero impide
archivar ese change hasta corregir la estructura canónica sin cambiar semántica.
Se deja como tarea explícita previa al archivado; no se altera la spec base aquí.
No se ejecutan tests de aplicación: este commit solo agrega documentación.
