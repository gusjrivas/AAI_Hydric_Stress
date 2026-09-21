# Primera entrega backend para UI del productor

Fecha: 2026-09-19. Rama: `feat/hu6-backend-soporte-ui`.

## Alcance entregado

Esta entrega implementa únicamente catálogo de sectores/puntos y consulta
histórica. No acepta ADR-0013 en su totalidad ni implementa predictores
multihorizonte, calibración, porcentajes, feedback v2, autenticación o UI.

La fachada se activa explícitamente con `PRODUCER_V2_ENABLED=true`. Si la
variable no está activa, las rutas v2 responden 404; los endpoints legacy siguen
disponibles. Desactivar la fachada no elimina el catálogo ni modifica series.

| Método y ruta | Comportamiento |
|---|---|
| `GET /api/v2/sectors` | Lista sectores con `limit` y cursor opaco. |
| `POST /api/v2/sectors` | Registra metadatos de un sector. |
| `PATCH /api/v2/sectors/{sector_id}` | Actualiza con `expected_revision` y permite seleccionar el sensor primario. |
| `GET /api/v2/sensors` | Lista sensores registrados y series legacy descubiertas; admite `sector_id`, `limit` y cursor. |
| `POST /api/v2/sensors` | Registra o adopta un sensor sin crear ni reescribir lecturas. |
| `PATCH /api/v2/sensors/{sensor_id}` | Actualiza metadatos con revisión optimista. |
| `GET /api/v2/sensors/{sensor_id}/readings` | Consulta una ventana UTC de 1 a 365 días mediante `days` y `end`. |

Los listados devuelven `items` y `next_cursor`. El cursor queda ligado al
recurso, filtros y corte temporal de la primera página; reutilizarlo con otros
filtros responde `invalid_cursor`.

Los errores v2 usan
`{error:{code,message,details,request_id}}` y exponen el mismo
`request_id` en `X-Request-ID`. Los errores legacy conservan su forma previa.
OpenAPI publica modelos separados para respuestas y errores v2.

## Persistencia y consistencia

El catálogo se guarda como
`data/ui_metadata/catalog.v1.json`, separado de las series. Usa reemplazo
atómico, lock de archivo entre procesos e incremento de `revision` bajo el
mismo lock. Dos altas concurrentes del mismo `sensor_id` producen una creación
y un conflicto, sin archivo parcial.

`save_dataset` y `append_reading` escriben Parquet mediante un temporal en el
mismo directorio y `os.replace`. `append_reading` mantiene dentro del lock la
secuencia lectura-modificación-reemplazo, conserva orden ascendente y reemplazo
por timestamp de los escritores legacy.

El historial deriva DataFrame y `snapshot_id` SHA-256 de la misma captura de
bytes. Devuelve solo filas almacenadas, nulos, fechas faltantes, cobertura,
unidades, procedencia y flags de calidad. No imputa, entrena, emite pronósticos ni
escribe durante GET. Un sensor registrado sin archivo devuelve `no_readings`;
uno desconocido devuelve 404 y un fallo de lectura devuelve 503.

## Compatibilidad, rollback y límites

Las rutas existentes, incluida
`POST /sensors/{sensor_id}/readings`, no cambian. Adoptar una serie
`sensor__*.parquet` solo agrega metadatos y preserva sus bytes. Las pruebas usan
directorios temporales y el checkout se monta en solo lectura; no se escriben
datasets ni resultados del usuario.

Rollback operativo: establecer `PRODUCER_V2_ENABLED=false` o retirar la
variable. El archivo versionado de catálogo se conserva para una reactivación.
No existe eliminación de sectores o sensores en esta entrega.

Quedan fuera los endpoints de resumen, pronóstico, assessments, reviews y
recalibración de `api-contract.md`, además de cualquier consumidor de UI.

## Trazabilidad

- HU2 / `data-ingestion`: CRISP-DM comprensión y preparación de datos.
- HU6 / `architecture-integration` y `alerting-ui`: CRISP-DM despliegue e
  integración.
- Configuraciones experimentales, `controlled_daily_v3`, HU7/HU8, hipótesis,
  propósito, alcance y capas de arquitectura: sin cambios.
- Memoria técnica: capítulo 3, persistencia operacional, concurrencia y fachada;
  capítulo 2 conserva procedencia, faltantes y límites de interpretación.

## Validación

- Dominio dirigido: 33 pruebas de storage, catálogo e históricos.
- Contrato HTTP y sensores legacy dirigido: 18 pruebas.
- Compatibilidad dirigida con escritores legacy: 21 pruebas.
- Suite backend completa: 61 pruebas.
- Demo acelerada: 56 pruebas aprobadas y 1 skip preexistente documentado.

Las advertencias observadas son deprecaciones de MLflow/FastAPI y un
`FutureWarning` de pandas sobre inferencia futura de tipos en el `concat`
legacy; no se registraron fallos funcionales. Ruff, Black, los dos changes
mediante `openspec validate --strict` y `git diff --check` pasan. El validador
informa el problema estructural preexistente de la spec canónica
`architecture-integration`, ya conservado como tarea pendiente 1.12.
