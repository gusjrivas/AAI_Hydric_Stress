# Spec: alerting-ui

Capacidad implementada (Épica 3, HU5+HU6 — primera exposición de retroalimentación humana y pipeline completo a través de una interfaz de usuario). Origen: `openspec/changes/add-alerting-ui/`. Este documento es la fuente de verdad vigente de la capacidad.

## Requirements

### Requirement: Ejecución de pronóstico desde la interfaz

El sistema DEBE poder ejecutar el pipeline completo (calidad, modelado, alertas) sobre el dataset consolidado configurado, y devolver un veredicto por fecha (alerta sí/no, probabilidad) sin exponer qué modelo lo generó.

#### Scenario: Correr un pronóstico produce alertas y persiste el feedback inicial

- **GIVEN** un dataset consolidado disponible bajo el nombre configurado por variable de entorno
- **WHEN** se invoca el endpoint de ejecución de pronóstico
- **THEN** se devuelve una lista de veredictos por fecha (fecha, alerta, probabilidad), y el registro de retroalimentación queda persistido con esas fechas en estado `pendiente` (o conservando su estado previo si ya existían)

Implementado en `backend/app/routers/forecast.py` (`POST /forecast/run`), testeado en `backend/tests/test_forecast.py`. Verificado manualmente contra el dataset real (`data/melchor_romero_2024_consolidado.parquet`) y el frontend real: el backend (`uvicorn app.main:app --port 8000`) y el frontend (`npm run dev`, `http://localhost:5173`) corriendo juntos produjeron `train_rows=286`, `test_rows=71`, con 22 de las 71 fechas marcadas como alerta (`alerta: true`) — por ejemplo 2024-10-31 (probabilidad 0.51), 2024-11-16 (0.67), 2024-12-13 (0.68). La tabla renderizada en el navegador mostró las 71 fechas reales (2024-10-19 a 2024-12-28) con probabilidades reales. Verificación cruzada vía `curl -X POST http://localhost:8000/forecast/run`: mismos `train_rows`/`test_rows`/cantidad de alertas, coincidiendo con los números ya conocidos de la verificación previa de HU4/HU7 sobre este mismo dataset/modelo.

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

## Limitaciones conocidas

- Un único modelo fijo (Random Forest, configuración base) genera el veredicto; el motor de selección/ensamble entre varios modelos queda para una iteración futura (`openspec/changes/add-alerting-ui/proposal.md`, "Fuera de alcance").
- No hay ingesta de datos de sensores en vivo; el dataset es el mismo consolidado histórico de HU2, configurable por nombre pero no por fuente en tiempo real.
- ~~El disparo de recalibración supervisada (HU5) no está conectado a la UI todavía.~~ **Actualización (2026-08-19):** resuelto — ver el requirement "Disparo manual de recalibración desde la interfaz" más arriba.
- El registro de retroalimentación asume un único pronóstico por fecha calendario — no distingue entre pronósticos recalculados en momentos distintos para la misma fecha objetivo. Esto no se expone con el dataset histórico estático actual, pero deberá resolverse antes de soportar datos de sensores en vivo con recálculo continuo.
- El backend entrena el modelo en cada corrida (sin cachear) cuando no hay un modelo recalibrado registrado; aceptable con el tamaño de dataset actual (~357 filas), a revisar si el dataset crece significativamente.
