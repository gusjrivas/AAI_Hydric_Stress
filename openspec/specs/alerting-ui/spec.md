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

## Limitaciones conocidas

- Un único modelo fijo (Random Forest, configuración base) genera el veredicto; el motor de selección/ensamble entre varios modelos queda para una iteración futura (`openspec/changes/add-alerting-ui/proposal.md`, "Fuera de alcance").
- No hay ingesta de datos de sensores en vivo; el dataset es el mismo consolidado histórico de HU2, configurable por nombre pero no por fuente en tiempo real.
- El disparo de recalibración supervisada (HU5) no está conectado a la UI todavía.
- El registro de retroalimentación asume un único pronóstico por fecha calendario — no distingue entre pronósticos recalculados en momentos distintos para la misma fecha objetivo. Esto no se expone con el dataset histórico estático actual, pero deberá resolverse antes de soportar datos de sensores en vivo con recálculo continuo.
- El backend entrena el modelo en cada corrida (sin cachear); aceptable con el tamaño de dataset actual (~357 filas), a revisar si el dataset crece significativamente.
