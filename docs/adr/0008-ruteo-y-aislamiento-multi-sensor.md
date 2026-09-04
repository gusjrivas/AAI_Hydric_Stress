# ADR-0008: Ruteo y aislamiento por `sensor_id` para soportar múltiples sensores en paralelo

## Estado

Aceptado (2026-09-03)

## Contexto

ADR-0007 conectó una fuente de datos en vivo (mock) al `alerting-ui`, pero asumió implícitamente **un único sensor por deployment**: `backend/app/config.py` resuelve `DATASET_NAME` y `FEEDBACK_LOG_NAME` una sola vez, a nivel de módulo, desde una variable de entorno fija (`ALERTING_UI_DATASET`); `backend/app/pipeline.py` mantiene un único `_selection_cache` global; y `src/human_feedback/model_registry.py` registra el modelo recalibrado bajo un único nombre fijo (`REGISTERED_MODEL_NAME`) en MLflow. No hay ningún concepto de "sensor" en el sistema — solo "el dataset configurado".

Para probar cómo se comporta la arquitectura propuesta con más de una fuente de lecturas en simultáneo (varios sensores mock generando tráfico concurrente), hace falta que el backend pueda servir múltiples series independientes al mismo tiempo, sin que una interfiera con el estado (caché de modelo, modelo recalibrado, feedback) de otra. Todavía no existe ningún sensor real conectado al proyecto.

## Decisión

### `sensor_id` como segmento de ruta, obligatorio en todos los endpoints relevantes

Los cuatro routers de `alerting-ui` pasan a llevar `sensor_id` en el path: `POST /sensors/{sensor_id}/readings`, `POST /forecast/{sensor_id}/run`, `GET /feedback/{sensor_id}` + `POST /feedback/{sensor_id}/{fecha}/confirm|reject`, `POST /recalibrate/{sensor_id}`. No se ofrece una ruta "sin sensor" ni un `sensor_id` default: como no hay sensores reales ni frontend consumiendo estos endpoints todavía (el frontend queda fuera de esta iteración), no hay compatibilidad hacia atrás que preservar, y mantener dos formas de acceder a lo mismo solo agrega superficie sin beneficio.

`sensor_id` se valida contra `^[a-zA-Z0-9_-]{1,64}$` en una única función compartida (`src/data_ingestion/sensor_naming.py::validate_sensor_id`). Es necesario porque el endpoint de ingesta sigue sin autenticación (limitación ya aceptada en ADR-0007) y `sensor_id` termina formando parte de un nombre de archivo — sin esta validación, un `sensor_id` como `../../etc/passwd` sería un vector de path traversal.

### Un recurso por sensor, nunca un recurso compartido

`sensor_naming.py` deriva, a partir de un `sensor_id` ya validado, tres nombres de recurso por convención de prefijo:

- Dataset: `sensor__{sensor_id}` (vía `data_ingestion.storage`, sin cambios en su contrato).
- Feedback log: `feedback__{sensor_id}` (vía `human_feedback.registry`, sin cambios en su contrato).
- Modelo registrado en MLflow: `alerting_ui_recalibrated_model__{sensor_id}`.

Cada sensor es una serie temporal completamente independiente, exactamente el caso que `predictive_modeling`/`architecture_integration` ya soportan hoy — ningún módulo de esas capas cambia. `backend/app/pipeline.py::_selection_cache` pasa de un único dict global a `dict[str, dict]` indexado por `sensor_id`; `human_feedback/model_registry.py` recibe `sensor_id` como parámetro y lo usa para derivar el nombre de modelo registrado en vez de una constante fija.

### El guard-rail de ADR-0007 (409 sobre el dataset histórico) se elimina, no se adapta

Como todo dataset de sensor queda prefijado con `sensor__`, es estructuralmente imposible que un `sensor_id` válido (según la regex de arriba) produzca el nombre exacto `melchor_romero_2024_consolidado`. La separación entre el dataset histórico de evidencia (HU7/HU8) y los datasets en vivo queda garantizada por construcción del esquema de nombres, no por un chequeo en runtime — se elimina `DATASET_NAME_EXPLICIT` y el `HTTPException(409, ...)` correspondiente en `sensors.py`.

## Alternativas consideradas

- **`sensor_id` opcional con un sensor `default` implícito**: se descarta — solo tendría sentido para preservar compatibilidad con un consumidor real de los endpoints sin sensor (frontend o sensor ya desplegado), y hoy no existe ninguno. Agregar la rama "sin sensor" sería mantener dos caminos para el mismo caso sin ningún beneficio concreto.
- **Dataset único compartido con columna `sensor_id`** (en vez de un dataset por sensor): se descarta para esta iteración — requeriría locking para escrituras concurrentes de sensores distintos sobre el mismo archivo, cambiar la clave de deduplicación de `timestamp` a `(timestamp, sensor_id)`, y tocar `predictive_modeling`/`architecture_integration` para filtrar por sensor antes de correr el pipeline (o rediseñar hacia un modelo cross-sensor, que no es un objetivo planteado). Un dataset por sensor resuelve la concurrencia entre sensores por construcción (nunca comparten archivo) sin tocar el núcleo de ML ya validado en HU3-HU8.
- **Migrar el almacenamiento de lecturas a una base de datos real (Postgres, ya disponible por ADR-0004)**: se descarta por ahora — revisitaría la decisión de ADR-0002 (Parquet local) con un costo de migración de infraestructura que no se justifica todavía para un prototipo de tesis sin sensores reales conectados; queda anotado como camino natural si el proyecto necesitara concurrencia de escritura *dentro* de un mismo sensor (fuera de alcance de este ADR).

## Consecuencias

- Ningún endpoint de `alerting-ui` queda accesible sin especificar `sensor_id` explícitamente — el frontend actual (`ForecastPage.tsx`), que llama a `/forecast/run` sin sensor, deja de funcionar contra el backend actualizado hasta que se le agregue un selector de sensor (fuera de alcance de este *change*; documentado como trabajo futuro).
- El caché de selección de modelo dejó de ser un único valor global: ahora crece un entry por `sensor_id` visto, sin límite ni expiración. Con un número acotado de sensores mock esto no es un problema; si el número de sensores creciera sin límite (o hubiera `sensor_id` efímeros), haría falta una política de expiración — no implementada en este *change*.
- `sensor_id` queda expuesto en URLs y nombres de archivo sin autenticación (limitación heredada de ADR-0007, no introducida por este *change*) — cualquiera que conozca o adivine un `sensor_id` puede leer/escribir sus lecturas, pronósticos y feedback. Aceptable para un prototipo de tesis sin exposición pública; a revisar antes de cualquier despliegue real.
- La concurrencia dentro de un mismo sensor (dos requests simultáneos escribiendo el mismo dataset) sigue sin resolverse — `append_reading` no toma ningún lock de archivo. No es un problema nuevo de este *change* (ya existía con un solo sensor) y sigue fuera de alcance.

## Referencias

- [ADR-0007: Ingesta de sensores en vivo (push) con generador mock](0007-ingesta-de-sensores-en-vivo-mock.md)
- `openspec/changes/add-multi-sensor-ingestion/` — spec delta y plan de implementación.
- `openspec/changes/add-selection-caching/` — introduce el caché de selección que este ADR particiona por sensor.
