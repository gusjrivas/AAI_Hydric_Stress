# Change: Add multi-sensor ingestion and isolation

## Trazabilidad

- **Épica:** 3. Integración y mejora (`alerting-ui`) + 1. Fundamentación científica (`data-ingestion`, convención de nombres de recursos por sensor).
- **Historia de usuario:** HU5+HU6 (`alerting-ui`) — extiende `add-mock-sensor-ingestion` para soportar más de un sensor en simultáneo, requisito explícito para poder probar el comportamiento de la arquitectura bajo tráfico concurrente de múltiples fuentes.
- **Fase de CRISP-DM:** Despliegue.
- **Insumo de diseño:** [ADR-0008](../../../docs/adr/0008-ruteo-y-aislamiento-multi-sensor.md), [ADR-0007](../../../docs/adr/0007-ingesta-de-sensores-en-vivo-mock.md).

## Why

`add-mock-sensor-ingestion` conectó una fuente de datos en vivo, pero asumió un único sensor por deployment: `DATASET_NAME`, `FEEDBACK_LOG_NAME` y el modelo registrado en MLflow se resuelven una sola vez, a nivel de módulo. Para validar cómo se comporta la arquitectura propuesta con varios sensores generando lecturas en paralelo (el objetivo de esta iteración), el backend necesita servir múltiples series independientes a la vez sin que el estado de una (caché de modelo, modelo recalibrado, feedback) contamine el de otra.

## What Changes

- **`src/data_ingestion/sensor_naming.py`** (nuevo): `validate_sensor_id(sensor_id: str) -> str` (valida contra `^[a-zA-Z0-9_-]{1,64}$`, levanta `ValueError` si no cumple) y `dataset_name_for(sensor_id)`, `feedback_log_name_for(sensor_id)`, `registered_model_name_for(sensor_id)` — única fuente de verdad del esquema de nombres, usada tanto por el backend como por los scripts CLI.
- **`backend/app/routers/sensors.py`**: `POST /sensors/{sensor_id}/readings` (antes `POST /sensors/readings`). Se elimina el guard-rail 409 sobre el dataset histórico (`DATASET_NAME_EXPLICIT`) — estructuralmente innecesario una vez que el nombre del dataset siempre lleva el prefijo `sensor__`.
- **`backend/app/routers/forecast.py`**: `POST /forecast/{sensor_id}/run` (antes `POST /forecast/run`).
- **`backend/app/routers/feedback.py`**: `GET /feedback/{sensor_id}`, `POST /feedback/{sensor_id}/{fecha}/confirm`, `POST /feedback/{sensor_id}/{fecha}/reject` (antes sin `{sensor_id}`).
- **`backend/app/routers/recalibration.py`**: `POST /recalibrate/{sensor_id}` (antes `POST /recalibrate`).
- **`backend/app/pipeline.py`**: `_selection_cache` pasa de `dict[str, Any] | None` (un único valor global) a `dict[str, dict[str, Any]]` indexado por `sensor_id`. `load_dataset_or_raise` y `execute_configured_pipeline` reciben `sensor_id` como parámetro.
- **`src/human_feedback/model_registry.py`**: `register_recalibrated_model` y `load_latest_recalibrated_model` reciben `sensor_id`, y derivan el nombre de modelo registrado vía `sensor_naming.registered_model_name_for` en vez de la constante fija `REGISTERED_MODEL_NAME`.
- **`backend/app/config.py`**: se elimina `DATASET_NAME`, `DATASET_NAME_EXPLICIT`, `FEEDBACK_LOG_NAME` (resueltos ahora por sensor, no por variable de entorno global). `HISTORICAL_DATASET_NAME` se conserva como constante documental (ningún dataset de sensor puede coincidir con ese nombre).
- **`scripts/seed_mock_sensor_dataset.py`** y **`scripts/simulate_sensor_readings.py`**: agregan `--sensor-id` (obligatorio), y derivan el nombre de dataset vía `sensor_naming`.
- **`scripts/simulate_multiple_sensors.py`** (nuevo): lanza N instancias de `simulate_sensor_readings` en paralelo (subprocesos), una por `sensor_id`, para generar tráfico concurrente real contra el backend.

## Impact

- **Specs afectadas:** `alerting-ui` (MODIFIED: los cinco requirements de ingesta/pronóstico/feedback/recalibración/reutilización de caché pasan a estar scopeados por `sensor_id`; ADDED: aislamiento entre sensores), `data-ingestion` (ADDED: convención de nombres de recursos por sensor).
- **Código afectado:** los cuatro routers de `backend/app/routers/`, `backend/app/pipeline.py`, `backend/app/config.py`, `src/human_feedback/model_registry.py`, `src/data_ingestion/sensor_naming.py` (nuevo), los dos scripts CLI existentes y `scripts/simulate_multiple_sensors.py` (nuevo), y todos sus tests.
- **Breaking change deliberado:** ningún endpoint de `alerting-ui` queda accesible sin `sensor_id`. El frontend actual (`ForecastPage.tsx`) deja de funcionar contra el backend actualizado hasta que se le agregue un selector de sensor — aceptado porque no hay sensores reales ni consumidores de producción todavía (ver ADR-0008, "Consecuencias").
- **Fuera de alcance de este change:** selector de sensor en el frontend (queda para una iteración posterior); autenticación del endpoint de ingesta (limitación heredada de ADR-0007); locking de escritura concurrente *dentro* de un mismo sensor; política de expiración del caché de selección por sensor; consolidación del dataset en vivo con el histórico.

## Alternativas consideradas

Ver [ADR-0008](../../../docs/adr/0008-ruteo-y-aislamiento-multi-sensor.md) — `sensor_id` opcional con default, dataset único compartido con columna `sensor_id`, y migración a Postgres ya se evaluaron y descartaron ahí para no duplicar la discusión.
