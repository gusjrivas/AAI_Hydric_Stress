# Spec: alerting-ui

> **Actualización normativa 2026-09-05:** rige el protocolo [controlled_daily_v3](../../../docs/research/protocolo-experimental-v3.md) y ADR-0009. Los ejemplos cuantitativos anteriores son históricos; no deben confundirse con la nueva evaluación de objetivos observados ni con inferencia futura.

Capacidad implementada (Épica 3, HU5+HU6 — primera exposición de retroalimentación humana y pipeline completo a través de una interfaz de usuario). Origen: `openspec/changes/add-alerting-ui/`. Este documento es la fuente de verdad vigente de la capacidad.

## Requirements

### Requirement: Ejecución de pronóstico desde la interfaz, por sensor

El sistema DEBE poder ejecutar el pipeline completo (calidad, modelado, alertas) sobre el dataset consolidado de un sensor dado, y devolver un veredicto para el último día observable disponible (alerta sí/no, probabilidad, fecha objetivo) sin exponer qué modelo lo generó.

#### Scenario: Correr un pronóstico produce un veredicto y persiste el feedback inicial

- **GIVEN** un dataset consolidado disponible para un `sensor_id` dado
- **WHEN** se invoca el endpoint de ejecución de pronóstico para ese sensor
- **THEN** se devuelve el veredicto correspondiente al último día observable (fecha, alerta, probabilidad, fecha objetivo), y el registro de retroalimentación de ese sensor queda persistido con esa fecha en estado `pendiente` (o conservando su estado previo si ya existía)

Implementado en `backend/app/routers/forecast.py` (`POST /forecast/{sensor_id}/run`), testeado en `backend/tests/test_forecast.py`.

**Comportamiento vigente:** `backend/app/pipeline.py::execute_configured_pipeline` construye la inferencia futura vía `predictive_modeling`/`architecture_integration.pipeline.predict_available` y filtra el resultado al último `timestamp` observable del dataset (`available[available.timestamp == latest]`) — no requiere que exista todavía el target futuro para emitir ese veredicto, y la respuesta incluye `fecha_objetivo` (`target_timestamp`) además de `fecha`/`alerta`/`probabilidad`. `POST /forecast/{sensor_id}/run` devuelve por lo tanto un único veredicto por corrida (el del día más reciente disponible para ese sensor), no una lista de veredictos sobre todo un holdout.

**Verificación histórica previa a la evolución hacia inferencia futura por sensor.** La verificación original (`train_rows=286`, `test_rows=71`, 22 de 71 fechas marcadas como alerta, dataset real de Melchor Romero 2024, sin `sensor_id`) corresponde a una versión anterior del endpoint, cuando devolvía la lista completa de veredictos sobre el holdout de evaluación en vez del último día observable. No debe usarse como evidencia del comportamiento actual; el contrato de respuesta (`ForecastRunResponse`) cambió de forma para reflejar el veredicto único.

**Modelo utilizado:** el backend operativo usa actualmente un contrato Random Forest explícito (`build_candidate_models(RANDOM_STATE)["random_forest"]`) cuando no existe un predictor recalibrado o cacheado reutilizable — ver la sección "Modelo operativo vs. selección automática experimental" al final de este documento. Esto reemplaza la actualización histórica de 2026-08-22 que documentaba selección automática entre candidatos como comportamiento vigente de esta capacidad; esa actualización describía correctamente su momento, pero ya no describe el código actual.

### Requirement: Consulta y validación humana de alertas

El sistema DEBE poder listar el registro de retroalimentación persistido, y permitir confirmar o rechazar una alerta puntual identificada por fecha.

#### Scenario: Confirmar una alerta vía la API

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se invoca el endpoint de confirmación para esa fecha
- **THEN** el registro persistido queda con esa fecha en estado `confirmada`

#### Scenario: Rechazar una alerta con corrección vía la API

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se invoca el endpoint de rechazo para esa fecha, con una etiqueta corregida y una observación
- **THEN** el registro persistido queda con esa fecha en estado `rechazada`, con la corrección y la observación guardadas

Implementado en `backend/app/routers/feedback.py` (`GET /feedback/{sensor_id}`, `POST /feedback/{sensor_id}/{fecha}/confirm`, `POST /feedback/{sensor_id}/{fecha}/reject`), testeado en `backend/tests/test_feedback.py`.

**Verificación histórica previa a la introducción obligatoria de `sensor_id` en las rutas** (ver ADR-0008): se hizo clic en "Confirmar" sobre la fila 2024-10-19 (su columna "Estado" pasó a "confirmada" inmediatamente) y en "Rechazar" sobre la fila 2024-10-20 (pasó a "rechazada" inmediatamente), contra un frontend y unas rutas anteriores al breaking change de PR #163. Al volver a correr el pronóstico desde la interfaz, ambas fechas conservaron su estado validado mientras las restantes se regeneraron en estado `pendiente` — esto confirmó el comportamiento de `upsert_feedback_log` de punta a punta a través de la interfaz de ese momento. El mecanismo de preservación (`upsert_feedback_log`) no cambió; las rutas y el frontend que lo ejercitan sí (ver la sección de multi-sensor).

### Requirement: Disparo manual de recalibración desde la interfaz

El sistema DEBE poder recalibrar el modelo usado para pronosticar a partir de las alertas rechazadas con corrección presentes en el registro de retroalimentación, y registrar el resultado de forma versionada.

#### Scenario: Recalibrar con correcciones pendientes

- **GIVEN** un registro de retroalimentación con al menos una alerta en estado `rechazada` con `etiqueta_corregida` no nula
- **WHEN** se invoca el endpoint de recalibración
- **THEN** se reentrena el modelo incorporando esas correcciones, el resultado queda registrado con una nueva versión, y la respuesta indica la versión registrada y cuántas correcciones se aplicaron

#### Scenario: Recalibrar sin correcciones pendientes

- **GIVEN** un registro de retroalimentación sin ninguna alerta `rechazada` con `etiqueta_corregida` no nula
- **WHEN** se invoca el endpoint de recalibración
- **THEN** se devuelve un error explícito indicando que no hay correcciones pendientes de aplicar, sin registrar ninguna versión nueva

Implementado en `backend/app/routers/recalibration.py` (`POST /recalibrate/{sensor_id}`) y `src/human_feedback/model_registry.py`. Testeado en `backend/tests/test_recalibration.py` y `tests/test_model_registry.py`. Verificado sobre datos reales: ver `docs/seguimiento-tareas.md`.

El mecanismo de recalibración invocado por este endpoint es `recalibrate_predictor` (`src/human_feedback/recalibration.py`), con las garantías temporales documentadas en `openspec/specs/human-feedback/spec.md` (requirement "Recalibración temporalmente controlada con retroalimentación madura"): solo incorpora correcciones cuyo target ya maduró y cuya validación humana ocurrió después de esa maduración.

**Actualización (2026-09-06) — linaje explícito, campo adicional retrocompatible:** cada recalibración exitosa registra además un evento de linaje (`openspec/specs/human-feedback/spec.md`, requirement "Linaje explícito de recalibraciones HITL") que vincula el predictor vigente (`source_model_id`), el predictor sucesor (`successor_model_id`) y el feedback nuevo que disparó la recalibración. `RecalibrationResponse` agrega el campo opcional `recalibration_id` (por defecto `None`, sin romper clientes existentes que lo ignoren) para permitir correlacionar la respuesta HTTP con ese evento; recuperarlo íntegramente requiere `human_feedback.model_registry.load_recalibration_lineage`/`list_recalibration_lineage`, no se expone todavía como ruta HTTP propia.

**Actualización (2026-09-05) — contrato de esquema obligatorio al registrar y validado al cargar:** una auditoría de reproducibilidad encontró que `register_recalibrated_model` guardaba metadatos de esquema (columnas de variables, horizonte, umbral, versión de pipeline) de forma opcional, y `load_latest_recalibrated_model` no verificaba compatibilidad antes de cargar — un modelo registrado con un esquema de variables distinto podía cargarse silenciosamente. Corregido: `register_recalibrated_model` ahora requiere `feature_columns`, `horizon_days`, `threshold` y `pipeline_version` (registrados como parámetros MLflow), y `load_latest_recalibrated_model(sensor_id, expected_feature_columns=None)` valida esas columnas contra las del modelo registrado antes de cargarlo, lanzando `ModelContractMismatch` (en vez de cargar silenciosamente) si no coinciden. `backend/app/routers/recalibration.py` y `backend/app/pipeline.py` ya pasan estos valores (`backend/app/config.py::HORIZON_DAYS`, `PIPELINE_VERSION`). Testeado en `tests/test_model_registry.py` (`test_load_latest_recalibrated_model_raises_on_feature_columns_mismatch`, entre otros).

### Requirement: Uso del modelo recalibrado en el próximo pronóstico

El sistema DEBE usar la versión más reciente del modelo recalibrado (si existe alguna) al ejecutar un nuevo pronóstico, en vez de entrenar un modelo nuevo desde cero.

#### Scenario: Pronóstico posterior a una recalibración

- **GIVEN** un modelo recalibrado ya registrado
- **WHEN** se ejecuta el pronóstico
- **THEN** las predicciones se generan con ese modelo registrado, sin reentrenar uno nuevo

#### Scenario: Pronóstico sin ninguna recalibración previa

- **GIVEN** que todavía no se registró ningún modelo recalibrado
- **WHEN** se ejecuta el pronóstico
- **THEN** se entrena un modelo nuevo, igual que el comportamiento previo a este *change*

Implementado en `backend/app/pipeline.py` (`execute_configured_pipeline`) y `src/architecture_integration/pipeline.py` (`skip_fit`). Testeado en `backend/tests/test_pipeline.py` y `tests/test_architecture_integration_pipeline.py`. Verificado sobre datos reales: ver `docs/seguimiento-tareas.md`.

### Requirement: Reutilización del modelo cacheado por sensor mientras el dataset no cambie

El sistema DEBE reutilizar, sin volver a entrenar, el último modelo ajustado para un sensor dado mientras el dataset consolidado de ese sensor no haya cambiado (según su huella/fingerprint); DEBE volver a ajustar cuando el dataset cambie o cuando todavía no exista un modelo cacheado para ese sensor. Este comportamiento solo aplica cuando no hay un modelo recalibrado registrado para ese sensor — la prioridad de un modelo recalibrado sobre el caché no cambia.

#### Scenario: El dataset no cambió entre dos corridas

- **GIVEN** un modelo ya cacheado para un sensor en una corrida anterior, sin modelo recalibrado registrado para ese sensor, y el dataset consolidado de ese sensor sin cambios
- **WHEN** se ejecuta una nueva corrida para ese mismo sensor
- **THEN** se reutiliza el mismo modelo cacheado sin volver a ajustarlo

#### Scenario: El dataset cambió entre dos corridas

- **GIVEN** un modelo ya cacheado para un sensor en una corrida anterior, sin modelo recalibrado registrado para ese sensor, y el dataset consolidado de ese sensor modificado desde esa corrida
- **WHEN** se ejecuta una nueva corrida para ese mismo sensor
- **THEN** se vuelve a ajustar el modelo, y el resultado reemplaza al modelo cacheado para ese sensor

#### Scenario: Un modelo recalibrado sigue teniendo prioridad sobre el caché

- **GIVEN** un modelo recalibrado registrado en MLflow para un sensor y, además, un modelo ya cacheado para ese mismo sensor
- **WHEN** se ejecuta una nueva corrida para ese sensor
- **THEN** se usa el modelo recalibrado, ignorando el caché

Implementado en `backend/app/pipeline.py` (`execute_configured_pipeline`, `_selection_cache` indexado por `sensor_id`), testeado en `backend/tests/test_pipeline.py`.

**Precisión sobre la semántica del caché:** este requirement se originó cuando el backend usaba selección automática entre candidatos (de ahí el nombre histórico "modelo auto-seleccionado"). El backend operativo vigente usa un contrato Random Forest explícito cuando no hay predictor recalibrado o cacheado (ver la sección "Modelo operativo vs. selección automática experimental" más abajo); el mecanismo de caché por huella de dataset y por sensor sigue vigente y sigue evitando reentrenar innecesariamente en cada corrida, independientemente de si el modelo subyacente es fijo o auto-seleccionado.

### Requirement: Observabilidad de solo lectura para la demo académica

El sistema DEBE exponer, por sensor y de solo lectura, la calidad/anomalías del dataset consolidado, la identidad verificable del predictor que usaría el próximo pronóstico, y la cadena completa de linaje de recalibraciones — sin modificar el dataset, sin entrenar ni recalibrar, y sin crear ningún run o versión nueva en MLflow.

#### Scenario: Consultar calidad y anomalías de un sensor

- **GIVEN** un dataset consolidado disponible para un `sensor_id` dado
- **WHEN** se invoca el endpoint de calidad de ese sensor
- **THEN** se devuelve el reporte de calidad (`data_quality.quality_report`) y anomalías (`data_quality.anomaly_detection.detect_anomalies`, exploratorio, calculado bajo demanda) sin modificar el dataset ni el predictor operativo

#### Scenario: Consultar el predictor activo sin que exista ninguno todavía

- **GIVEN** un sensor que nunca corrió un pronóstico ni una recalibración
- **WHEN** se invoca el endpoint del predictor activo de ese sensor
- **THEN** se devuelve la configuración del contrato (horizonte, columnas, lags, ventanas — siempre disponible desde `backend/app/config.py`) con `origin`, `model_id`, `version`, `trained_through` y `calibration_end` explícitamente `None`, nunca inventados

#### Scenario: Consultar la cadena de linaje completa

- **GIVEN** un sensor con una o más recalibraciones exitosas
- **WHEN** se invoca el endpoint de linaje de ese sensor
- **THEN** se devuelve la cadena cronológica completa (`human_feedback.model_registry.list_recalibration_lineage`), o un error HTTP explícito (409) si algún evento de linaje está corrupto o incompleto — nunca una cadena parcial ni un error oculto

Implementado en `backend/app/routers/quality.py` (`GET /quality/{sensor_id}`), `backend/app/routers/models.py` (`GET /models/{sensor_id}/active`) y `backend/app/routers/lineage.py` (`GET /lineage/{sensor_id}`). Testeado en `backend/tests/test_quality.py`, `backend/tests/test_models_active.py` y `backend/tests/test_lineage.py`, incluyendo verificación explícita de ausencia de efectos secundarios (ningún run ni versión de modelo nuevos).

El predictor "base configurado" (sin recalibración previa) se identifica leyendo la metadata del último predictor `issued` (`human_feedback.model_registry.load_latest_issued_predictor_metadata`, agregada junto con `get_latest_recalibrated_version` para esta capacidad) — nunca cargando ni entrenando un modelo distinto del que usaría `execute_configured_pipeline`.

## Limitaciones conocidas

- ~~Un único modelo fijo (Random Forest, configuración base) genera el veredicto; el motor de selección/ensamble entre varios modelos queda para una iteración futura (`openspec/changes/add-alerting-ui/proposal.md`, "Fuera de alcance").~~ **Actualización (2026-08-22):** por un tiempo resuelto mediante selección automática entre candidatos (`openspec/specs/predictive-modeling/spec.md`, requirement "Selección automática del mejor modelo candidato"). **Actualización posterior (ver "Modelo operativo vs. selección automática experimental" más abajo):** el backend operativo volvió a usar un contrato Random Forest explícito, por una decisión deliberada distinta del motivo original de esta limitación — no es un regreso a la limitación original, sino una decisión operativa para evitar que la UI falle ante folds de validación degenerados.
- ~~No hay ingesta de datos de sensores en vivo; el dataset es el mismo consolidado histórico de HU2, configurable por nombre pero no por fuente en tiempo real.~~ **Actualización:** resuelto mediante ingesta de sensores mock/en vivo (`POST /sensors/{sensor_id}/readings`, ADR-0007) y ruteo/aislamiento multi-sensor (ADR-0008) — ver la sección "Multi-sensor" más abajo. El dataset consumido por esta capacidad para un `sensor_id` dado puede ser el generado por ese flujo de ingesta mock, separado por construcción del dataset histórico formal de HU7/HU8 (`melchor_romero_2024_consolidado`, sin prefijo `sensor__`). La ingesta de sensores sigue siendo una fuente de datos y contexto experimental, no la contribución central del proyecto (que permanece siendo la arquitectura de IA).
- ~~El disparo de recalibración supervisada (HU5) no está conectado a la UI todavía.~~ **Actualización (2026-08-19):** resuelto — ver el requirement "Disparo manual de recalibración desde la interfaz" más arriba.
- El registro de retroalimentación asume un único pronóstico por fecha calendario — no distingue entre pronósticos recalculados en momentos distintos para la misma fecha objetivo. Esto no se expone con el dataset histórico estático actual, pero deberá resolverse antes de soportar datos de sensores en vivo con recálculo continuo a mayor frecuencia.
- ~~El backend entrena el modelo en cada corrida (sin cachear) cuando no hay un modelo recalibrado registrado; aceptable con el tamaño de dataset actual (~357 filas), a revisar si el dataset crece significativamente~~ **Actualización (2026-08-23):** resuelto — ver el requirement "Reutilización del modelo cacheado por sensor mientras el dataset no cambie" más arriba (`openspec/changes/add-selection-caching/`).
- El campo `model_version` persistido en el registro de retroalimentación (`src/human_feedback/schema.py`) conserva ese nombre por compatibilidad histórica, pero en el flujo operativo vigente contiene `FittedPredictor.model_id` (un identificador lógico e inmutable del predictor), no un número de versión del Model Registry de MLflow — ver `openspec/specs/human-feedback/spec.md` para el detalle completo de esta distinción.

## Multi-sensor

Todas las rutas de esta capacidad exigen un `sensor_id` explícito (`POST /forecast/{sensor_id}/run`, `GET /feedback/{sensor_id}`, `POST /feedback/{sensor_id}/{fecha}/confirm`, `POST /feedback/{sensor_id}/{fecha}/reject`, `POST /recalibrate/{sensor_id}`, `POST /sensors/{sensor_id}/readings`, `GET /quality/{sensor_id}`, `GET /models/{sensor_id}/active`, `GET /lineage/{sensor_id}`; ver ADR-0008). Por cada sensor: el dataset consolidado, el registro de retroalimentación, el modelo recalibrado en el Model Registry de MLflow y el caché de modelo (`_selection_cache`) están aislados entre sí mediante la convención de nombres de `data_ingestion.sensor_naming`, sin estado global compartido entre sensores.

El frontend consume estas rutas con `sensor_id` desde `frontend/src/App.tsx` (estado del sensor compartido entre secciones) y sus features `forecast/`, `quality/` y `lineage/`, tras el breaking change deliberado introducido por PR #163 (que exigió `sensor_id` en todos los endpoints) y su resolución posterior, que incorporó el selector/input de sensor en la interfaz. No queda ninguna llamada del frontend a una ruta sin `sensor_id`.

## Modelo operativo vs. selección automática experimental

El backend operativo (`backend/app/pipeline.py::execute_configured_pipeline`) usa actualmente un contrato Random Forest explícito (`build_candidate_models(...)["random_forest"]`) cuando no existe un predictor recalibrado o cacheado reutilizable para el sensor, en vez de invocar la selección automática entre candidatos. Esta es una decisión operativa deliberada, documentada inline en el código: la selección automática (`select_best_candidate`, `openspec/specs/predictive-modeling/spec.md`) falla explícitamente cuando algún fold de validación temporal carece de ambas clases, y la UI necesita poder producir un pronóstico incluso en esa situación.

La selección automática entre candidatos permanece disponible y vigente en el núcleo experimental (`predictive-modeling`, `architecture-integration`) y es la que efectivamente usa el protocolo experimental formal (`controlled_daily_v3`) cuando no se fija un modelo explícito para una comparación controlada. Esta divergencia entre el backend operativo y el núcleo experimental es intencional y no debe interpretarse como que `alerting-ui` usa selección automática de modelos: no la usa actualmente.
