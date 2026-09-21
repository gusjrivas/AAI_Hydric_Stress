## 1. Contratos e integración después de aprobación
- [x] 1.1a Materializar esquemas OpenAPI y fixtures de catálogo e históricos.
- [ ] 1.1b Materializar esquemas y fixtures de emisión, feedback, resumen,
      recalibración y assessments.
- [x] 1.2 Integrar catálogo, selección de sector y consulta de lecturas.
- [x] 1.3a Implementar identidad, persistencia transaccional e idempotencia
      del repositorio operacional v2 por sensor (tandas y emisiones).
- [ ] 1.3b Integrar snapshot real de lecturas y emisión de tres horizontes
      desde el modelo (pendiente: emisión real HU4 fuera de esta entrega).
- [x] 1.4 Integrar revisión humana (GET/GET/POST /forecasts) y listado
      persistente de pendientes (pending_total, reviewable_pending_total).
- [ ] 1.5 Integrar resumen, procedencia, fechas, frescura y linaje.
- [ ] 1.6 Integrar recalibración explícita compatible, sin ejecución por GET.
- [x] 1.7a Probar aislamiento, faltantes, errores, concurrencia y reinicio de
      catálogo e históricos.
- [x] 1.7b-i Probar esos escenarios para el repositorio operacional v2
      (emisión sembrada por fixtures y feedback): identidad, inmutabilidad,
      idempotencia y reinicio; concurrencia probada en dos niveles
      distintos: control optimista de revisión con hilos concurrentes en
      un mismo proceso, y exclusión real entre procesos de sistema
      operativo independientes (`subprocess`, cada uno con su propio
      `OperationalRepository` sobre el mismo almacenamiento).
- [ ] 1.7b-ii Probar esos escenarios para recalibración y assessments
      (pendiente; ambos fuera de alcance de esta entrega).
- [x] 1.8a Ejecutar regresión de endpoints legacy y demo PR #202–#205 para esta entrega.
- [ ] 1.8b Reejecutar regresiones al integrar las porciones v2 restantes.
- [x] 1.9a Verificar fixtures y OpenAPI publicados de catálogo e históricos.
- [ ] 1.9b Verificar consumidores de UI para el contrato v2 completo.
- [x] 1.10a Documentar activación, rollback, evidencia y límites de esta entrega.
- [ ] 1.10b Documentar activación y límites de las capacidades v2 restantes.
- [ ] 1.11 Revisar recorrido integrado antes de proponer merge a main.
- [x] 1.12 Antes de archivar, corregir estructura preexistente de architecture-integration sin cambiar requisitos y revalidar la spec canónica.
- [x] 1.13a Implementar validación fail-closed y registro de identidad SHA-256 para
      un manifiesto de calibración congelado, sin entrenar ni evaluar.
- [ ] 1.13b Exponer evidencia inmutable de assessment con aislamiento por sensor y
      probar los motivos de porcentaje no publicable.

- [x] 1.14 Implementar identidad y transaccion operacional por sensor segun decisiones del 2026-09-20; probar concurrencia, caidas y replay.
- [x] 1.15 Aplicar reserva permanente demo- a mutaciones operacionales v2; probar estados, ausencia de manifiesto y compatibilidad legacy.
