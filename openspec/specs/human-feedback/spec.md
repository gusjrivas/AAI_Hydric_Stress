# Spec: human-feedback

Capacidad implementada (Épica 3, HU5 — primer sub-proyecto: casos de uso, estados de validación, modelo de datos y flujo de interacción). Origen: `openspec/changes/add-feedback-data-model/`. Este documento es la fuente de verdad vigente de la capacidad; el *change* que la originó queda como registro histórico de la decisión, no se actualiza en paralelo a este archivo.

Los otros dos sub-proyectos de HU5 (registro persistente de validaciones/correcciones e integración con las predicciones; reglas de selección y prueba de recalibración supervisada) todavía no comenzaron y se documentarán como *changes* independientes que extienden esta spec.

## Requirements

### Requirement: Esquema de registro de retroalimentación

El sistema DEBE poder representar, por cada alerta generada, un registro de retroalimentación con: fecha, valor de la alerta, estado de validación (`pendiente`, `confirmada` o `rechazada`), una etiqueta corregida opcional, y una observación textual opcional.

#### Scenario: Inicialización de un registro de retroalimentación a partir de alertas generadas

- **GIVEN** un conjunto de alertas generadas con sus fechas
- **WHEN** se inicializa el registro de retroalimentación a partir de esas alertas
- **THEN** cada alerta queda representada con estado de validación `pendiente` y sin corrección ni observación

Implementado en `src/human_feedback/schema.py` (`init_feedback_log`, `FEEDBACK_COLUMNS`), testeado en `tests/test_feedback_schema.py`. Verificado sobre las alertas reales generadas en HU4 (Random Forest, umbral 0.5, dataset Melchor Romero 2024): registro inicializado con 72 filas, todas en estado `pendiente`.

### Requirement: Actualización del estado de validación de una alerta

El sistema DEBE poder actualizar el estado de validación de una alerta puntual, identificada por su fecha, agregando opcionalmente una etiqueta corregida y una observación.

#### Scenario: Confirmar una alerta

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se confirma esa alerta
- **THEN** su estado de validación pasa a `confirmada`

#### Scenario: Rechazar una alerta con corrección

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se rechaza esa alerta indicando una etiqueta corregida y una observación
- **THEN** su estado de validación pasa a `rechazada`, y la etiqueta corregida y la observación quedan guardadas en esa fila

Implementado en `src/human_feedback/schema.py` (`update_feedback`), testeado en `tests/test_feedback_schema.py`. Verificado sobre datos reales: se confirmó una alerta real (correctamente emitida) y se rechazó un falso negativo real (2024-10-18, donde hubo estrés real sin alerta) con `etiqueta_corregida=1` y una observación textual.

## Limitaciones conocidas

- Este sub-proyecto define solo el modelo de datos y las funciones de actualización en memoria; no incluye todavía persistencia real a disco (Parquet) del registro de retroalimentación ni su integración con los registros de predicción — eso corresponde al segundo *change* de HU5.
- No hay interfaz de usuario para que una persona interactúe con estos estados; por ahora son funciones de Python que una interfaz futura (HU6/frontend) consumiría.
- Los 3 estados de validación (`pendiente`/`confirmada`/`rechazada`) son una simplificación deliberada; no capturan nivel de confianza ni múltiples revisores por alerta.
