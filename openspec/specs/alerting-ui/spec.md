# Spec: alerting-ui

> **Actualización normativa 2026-09-05:** rige el protocolo [controlled_daily_v3](../../../docs/research/protocolo-experimental-v3.md) y ADR-0009. Los ejemplos cuantitativos anteriores son históricos; no deben confundirse con la nueva evaluación de objetivos observados ni con inferencia futura.

Capacidad implementada (Épica 3, HU5+HU6 — primera exposición de retroalimentación humana y pipeline completo a través de una interfaz de usuario). Origen: `openspec/changes/add-alerting-ui/`. Este documento es la fuente de verdad vigente de la capacidad.

## Requirements

### Requirement: Ejecución de pronóstico desde la interfaz

El sistema DEBE poder ejecutar el pipeline completo (calidad, modelado, alertas) sobre el dataset consolidado configurado, y devolver un veredicto por fecha (alerta sí/no, probabilidad) sin exponer qué modelo lo generó.

#### Scenario: Correr un pronóstico produce alertas y persiste el feedback inicial

- **GIVEN** un dataset consolidado disponible bajo el nombre configurado por variable de entorno
- **WHEN** se invoca el endpoint de ejecución de pronóstico
- **THEN** se devuelve una lista de veredictos por fecha (fecha, alerta, probabilidad), y el registro de retroalimentación queda persistido con esas fechas en estado `pendiente` (o conservando su estado previo si ya existían)

Implementado en `backend/app/routers/forecast.py` (`POST /forecast/run`), testeado en `backend/tests/test_forecast.py`. Verificado manualmente contra el dataset real (`data/melchor_romero_2024_consolidado.parquet`) y el frontend real: el backend (`uvicorn app.main:app --port 8000`) y el frontend (`npm run dev`, `http://localhost:5173`) corriendo juntos produjeron `train_rows=286`, `test_rows=71`, con 22 de las 71 fechas marcadas como alerta (`alerta: true`) — por ejemplo 2024-10-31 (probabilidad 0.51), 2024-11-16 (0.67), 2024-12-13 (0.68). La tabla renderizada en el navegador mostró las 71 fechas reales (2024-10-19 a 2024-12-28) con probabilidades reales. Verificación cruzada vía `curl -X POST http://localhost:8000/forecast/run`: mismos `train_rows`/`test_rows`/cantidad de alertas, coincidiendo con los números ya conocidos de la verificación previa de HU4/HU7 sobre este mismo dataset/modelo.

**Actualización (2026-08-22):** desde `openspec/changes/add-model-selection-engine/`, el modelo usado ya no es un Random Forest fijo — se selecciona automáticamente entre candidatos. Verificado sobre el mismo dataset real: `logistic_regression` y `random_forest` empataron en `cv_mean_score=0.0000` (el tamaño de muestra actual deja folds tempranos sin ejemplos de la clase de estrés, ver "Limitaciones conocidas" de `openspec/specs/predictive-modeling/spec.md`); se endureció el desempate en `select_best_candidate` para preferir `random_forest` en caso de empate, y con ese fix el pronóstico sobre este dataset elige `random_forest`.

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

Implementado en `backend/app/routers/feedback.py` (`GET /feedback`, `POST /feedback/{fecha}/confirm`, `POST /feedback/{fecha}/reject`), testeado en `backend/tests/test_feedback.py`. Verificado manualmente end-to-end con el frontend real: se hizo clic en "Confirmar" sobre la fila 2024-10-19 (su columna "Estado" pasó a "confirmada" inmediatamente) y en "Rechazar" sobre la fila 2024-10-20 (pasó a "rechazada" inmediatamente). Al volver a correr el pronóstico desde la interfaz, ambas fechas conservaron su estado validado (`confirmada`/`rechazada`) mientras las 69 fechas restantes se regeneraron en estado `pendiente` — esto confirma el comportamiento de `upsert_feedback_log` (preservar la retroalimentación humana entre corridas) de punta a punta a través de la interfaz real, no solo a nivel de unidad.

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

Implementado en `backend/app/routers/recalibration.py` (`POST /recalibrate`) y `src/human_feedback/model_registry.py`. Testeado en `backend/tests/test_recalibration.py` y `tests/test_model_registry.py`. Verificado sobre datos reales: ver `docs/seguimiento-tareas.md`.

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

### Requirement: Reutilización del modelo auto-seleccionado mientras el dataset no cambie

El sistema DEBE reutilizar, sin volver a seleccionar, el último modelo auto-seleccionado mientras el dataset consolidado no haya cambiado; DEBE volver a seleccionar cuando el dataset cambie o cuando todavía no exista un modelo cacheado. Este comportamiento solo aplica cuando no hay un modelo recalibrado registrado — la prioridad de un modelo recalibrado sobre la selección automática no cambia.

#### Scenario: El dataset no cambió entre dos corridas

- **GIVEN** un modelo ya auto-seleccionado en una corrida anterior, sin modelo recalibrado registrado, y el dataset consolidado sin cambios
- **WHEN** se ejecuta una nueva corrida
- **THEN** se reutiliza el mismo modelo cacheado sin volver a seleccionar

#### Scenario: El dataset cambió entre dos corridas

- **GIVEN** un modelo ya auto-seleccionado en una corrida anterior, sin modelo recalibrado registrado, y el dataset consolidado modificado desde esa corrida
- **WHEN** se ejecuta una nueva corrida
- **THEN** se vuelve a seleccionar el mejor candidato, y el resultado reemplaza al modelo cacheado

#### Scenario: Un modelo recalibrado sigue teniendo prioridad sobre el caché

- **GIVEN** un modelo recalibrado registrado en MLflow y, además, un modelo auto-seleccionado ya cacheado
- **WHEN** se ejecuta una nueva corrida
- **THEN** se usa el modelo recalibrado, ignorando el caché de selección automática

Implementado en `backend/app/pipeline.py` (`execute_configured_pipeline`), testeado en `backend/tests/test_pipeline.py`.

## Limitaciones conocidas

- ~~Un único modelo fijo (Random Forest, configuración base) genera el veredicto; el motor de selección/ensamble entre varios modelos queda para una iteración futura (`openspec/changes/add-alerting-ui/proposal.md`, "Fuera de alcance").~~ **Actualización (2026-08-22):** resuelto — ver el requirement "Selección automática del mejor modelo candidato" en `openspec/specs/predictive-modeling/spec.md` y "Uso del motor de selección automática..." en `openspec/specs/architecture-integration/spec.md`.
- No hay ingesta de datos de sensores en vivo; el dataset es el mismo consolidado histórico de HU2, configurable por nombre pero no por fuente en tiempo real.
- ~~El disparo de recalibración supervisada (HU5) no está conectado a la UI todavía.~~ **Actualización (2026-08-19):** resuelto — ver el requirement "Disparo manual de recalibración desde la interfaz" más arriba.
- El registro de retroalimentación asume un único pronóstico por fecha calendario — no distingue entre pronósticos recalculados en momentos distintos para la misma fecha objetivo. Esto no se expone con el dataset histórico estático actual, pero deberá resolverse antes de soportar datos de sensores en vivo con recálculo continuo.
- ~~El backend entrena el modelo en cada corrida (sin cachear) cuando no hay un modelo recalibrado registrado; aceptable con el tamaño de dataset actual (~357 filas), a revisar si el dataset crece significativamente~~ **Actualización (2026-08-23):** resuelto — ver el requirement "Reutilización del modelo auto-seleccionado mientras el dataset no cambie" más arriba (`openspec/changes/add-selection-caching/`). Sigue siendo cierto que, desde `openspec/changes/add-model-selection-engine/`, la corrida en caso de *cache miss* es una búsqueda de hiperparámetros con validación cruzada sobre ambos candidatos (más costosa que un único `.fit()`), aceptada como tradeoff deliberado (ver "Alternativas consideradas" de ese *change*).
