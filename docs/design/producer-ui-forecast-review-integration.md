# Consulta de pronósticos y revisión humana en "Mi cultivo"

Fecha: 2026-09-20. Frontend: `C:\Repo\AAI_Hydric_Stress`,
`feat/hu6-ui-productor-integracion`. Backend consultado como contrato de
solo lectura: `C:\Repo\AAI_Hydric_Stress_backend_ui`,
`feat/hu6-backend-soporte-ui` (worktree; no se tocó).

Trazabilidad: HU6; capacidad `alerting-ui` (presentación en "Mi cultivo",
`ProducerView`); consume la fachada operacional descrita en
`architecture-integration`/`predictive-modeling`/`human-feedback` del
worktree backend (`producer_v2.py`, `schemas_v2.py`,
`operational_repository.py`). CRISP-DM: despliegue/integración. No afecta
HU7/HU8, `controlled_daily_v3`, hipótesis, alcance ni arquitectura. No se
modificó ningún archivo de backend, spec canónica ni change de OpenSpec.

## Alcance entregado

En `frontend/src/features/producer/`:

- `forecastsApi.ts`: cliente v2 de `GET .../forecasts`, `GET
  .../forecasts/{id}` y `POST .../forecasts/{id}/reviews`, con las mismas
  convenciones que `catalogApi.ts`/`readingsApi.ts` (errores tipados,
  `ProducerV2UnavailableError` para la fachada apagada). Mapea los códigos
  de error del contrato (`forecast_not_found`, `review_not_open` con su
  `review_open_at`, `revision_conflict` con `actual_revision`,
  `idempotency_conflict`, `demo_write_locked`) a excepciones específicas;
  cualquier otro error (5xx, red) queda como error genérico recuperable.
- `ForecastCard.tsx`: una emisión con su fecha objetivo, horizonte,
  `as_of_date`/`issued_at` (para distinguir emisiones que comparten fecha
  objetivo), alerta, `display_probability` (nunca 0 % cuando falta: "Probabilidad
  no disponible"; nunca deriva un porcentaje de `score`) y el flujo de
  revisión (confirmar/rechazar, comentario opcional, corrección posterior
  sin vencimiento).
- `ForecastsSection.tsx`: dos listas independientes y paginadas (cursor)
  por sensor — "Pendientes de revisar" (`review_status=pending`, con
  `pending_total`/`reviewable_pending_total` del sensor completo, no de la
  página visible) e "Historial de pronósticos" (sin filtro) — con la misma
  protección contra respuestas atrasadas de un sensor ya no seleccionado
  que ya usa `ProducerHistoryPanel`.
- `ProducerView.tsx`: reemplaza la nota "los pronósticos todavía no están
  integrados" por `<ForecastsSection>` cuando hay un sensor elegido.

## Decisiones de idempotencia y concurrencia (contrato v2)

- `request_id` se genera al abrir el formulario de revisión (clic en
  "Confirmar"/"Rechazar") y se conserva mientras ese envío esté incierto:
  un error recuperable (red, 5xx) mantiene el formulario y el mismo
  `request_id`; "Reintentar" reenvía el mismo cuerpo exacto. Cambiar de
  acción o cancelar y volver a empezar genera un `request_id` nuevo, nunca
  reutilizado para una opinión distinta.
- `revision_conflict` (alguien más registró una opinión mientras se
  completaba el formulario) descarta el intento local, no sobrescribe nada
  y vuelve a consultar `GET .../forecasts/{id}` para mostrar el resultado
  real del servidor.
- `idempotency_conflict` y `demo_write_locked` se muestran con su
  explicación en lenguaje cotidiano, sin reintento automático.
- Nunca se muestra "guardado" antes de la respuesta 2xx real del POST.

## Sin datos inventados

No existe generación real de emisiones v2 en esta entrega del backend
(`operational_repository.record_batch` no se expone por HTTP; ver
`docs/design/backend-producer-ui-emission-dependencies.md`, sección 4, en
el worktree backend). Por lo tanto, contra un backend real hoy ambas listas
mostrarán su estado vacío ("Todavía no hay pronósticos disponibles" /
"No tenés pronósticos pendientes de revisar"), con la aclaración explícita
de que la ausencia de pronósticos no equivale a ausencia de riesgo. No se
agregaron fixtures, sembrado ni botones de generación ficticia dentro de la
aplicación.

## Pruebas

Con fixtures aislados (sin backend), en `frontend/src/features/producer/`:

- `forecastsApi.test.ts`: construcción de query params, cuerpo exacto del
  POST de revisión, mapeo de cada código de error del contrato,
  `displayProbability` (nunca 0 % con `display_probability: null`).
- `ForecastCard.test.tsx`: confirmar/rechazar con comentario, corrección
  posterior de una opinión ya registrada, revisión aún no habilitada
  (`review_not_open` con su fecha), reintento de un error recuperable
  reutilizando el mismo `request_id` (sin duplicar el envío),
  `revision_conflict` sin sobrescribir + refresco desde el servidor,
  `idempotency_conflict`, bloqueo demo (`demo_write_locked`), probabilidad
  ausente.
- `ForecastsSection.test.tsx`: vacío honesto en ambas listas, error
  distinto de vacío con reintento, contadores de pendientes independientes
  de la página visible, dos emisiones con la misma fecha objetivo
  mostradas por separado, paginación ("Ver más"), descarte de una
  respuesta atrasada de un sensor ya no seleccionado, remoción de un
  pronóstico de "Pendientes" al dejar de estar pendiente.
- `ProducerView.test.tsx`: actualizado para el estado vacío honesto en vez
  de la nota "no integrado" que reemplaza esta entrega.

Todas estas son pruebas de comportamiento contra fixtures locales
(`vi.spyOn` sobre `forecastsApi`/`fetch`), no contra un backend real; se
distinguen así de la verificación de integración real documentada en
`docs/design/producer-ui-integration-check.md` para catálogo/históricos.

Comandos ejecutados y resultado:

```
npx vitest run src/features/producer   # 39/39 (incluye los archivos nuevos)
npx vitest run                          # 135/135 (suite completa del frontend)
npx tsc -b                              # sin errores
npx oxlint                              # sin hallazgos
npx vite build                          # build exitoso
```

## Pendiente explícito

- **Verificación en navegador real**: no se realizó en esta entrega. El
  backend v2 de este worktree no expone forma alguna de emitir pronósticos
  reales (ver sección "Sin datos inventados"), por lo que una verificación
  visual solo mostraría los estados vacíos ya cubiertos por
  `ForecastsSection.test.tsx`; se documenta como pendiente en vez de
  simularla, en línea con la limitación de `resize_window` ya registrada en
  `docs/design/producer-ui-integration-check.md`.
- **Verificación de integración contra un backend real con emisiones
  reales**: no es posible todavía porque no existe endpoint de emisión real
  (HU4 pendiente). Cuando exista, repetir el patrón de
  `producer-ui-integration-check.md` sembrando emisiones vía la API real
  (nunca fixtures inyectados en la app) para confirmar
  `review_open_at`/`reviewable`/`training_eligibility` contra el reloj del
  servidor real.
- No se tocó ningún archivo de backend, `openspec/specs/`,
  `openspec/changes/` existentes ni los cambios previos sin commitear de
  otra persona en este worktree (`docs/seguimiento-tareas.md`,
  `ResumenView.*`, `features/summary/HistoryPanel*`, `historyApi.ts`,
  `App.*.test.tsx`, `openspec/changes/add-measurement-history-overview/`,
  `work/`, `docker-compose.override.yml`, datos de prueba en `data/`,
  cambios en `backend/`): quedan intactos y fuera de este commit.
