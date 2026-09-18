# Vigencia de la evidencia científica

Actualizado 2026-09-17, rama feat/scientific-closure.

- [Decisiones previas a ejecución](scientific-closure-decisions.md): fuente vigente
  para soporte, episodios, custodia y diseños complementarios.
- [Protocolo v4](controlled-daily-v4-external-pergamino-protocol.md) y
  [manifiesto](controlled-daily-v4-external-pergamino-manifest.yaml):
  A/B/C implementadas e integradas, probadas con fixtures; ejecución científica
  pendiente y sin evidencia consolidada v4.
- [Guía operativa](scientific-closure-runbook.md): autorización, rutas externas,
  imagen/commit inmutables, backup y recuperación.
- `protocolo-experimental-v3.md` y `reference-v3-formal-table.md`:
  protocolo y evidencia histórica v3, sin modificación. No réplica directa v4.
- `controlled-daily-v4-stage-b-c-decisiones-pendientes.md`, ADR y seguimiento
  histórico: conservar fechas y contexto; no usar su título como estado actual.
  Las decisiones operativas B/C ya tienen implementación. Las menciones antiguas
  a “B/C no implementadas” quedan reemplazadas por esta nota.

Estados distintos: diseñado ≠ implementado ≠ probado con fixtures ≠ integrado
≠ ejecutado científicamente ≠ evidencia consolidada.
Los complementos regresión/HITL/anomalías reservadas/robustez están diseñados;
sus nuevos runners aún no existen. No se atribuye mejora científica a tests.
