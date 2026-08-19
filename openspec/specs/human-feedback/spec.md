# Spec: human-feedback

Capacidad implementada (Épica 3, HU5 — completa, los tres sub-proyectos: casos de uso/estados de validación/modelo de datos/flujo de interacción, registro persistente/integración con predicciones, y recalibración supervisada). Orígenes: `openspec/changes/add-feedback-data-model/`, `openspec/changes/add-feedback-registry-integration/`, `openspec/changes/add-supervised-recalibration/`. Este documento es la fuente de verdad vigente de la capacidad; los *changes* que la originaron quedan como registro histórico de la decisión, no se actualizan en paralelo a este archivo.

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

### Requirement: Persistencia del registro de retroalimentación

El sistema DEBE poder guardar y recuperar un registro de retroalimentación en disco, reutilizando el contrato de acceso a datos ya establecido (`load_dataset`/`save_dataset`).

#### Scenario: Guardar y recuperar un registro sin pérdida de información

- **GIVEN** un registro de retroalimentación con alertas en distintos estados de validación
- **WHEN** se guarda y luego se recupera con el mismo nombre
- **THEN** el registro recuperado es igual al original, incluyendo estados, correcciones y observaciones

Implementado en `src/human_feedback/registry.py` (`save_feedback_log`, `load_feedback_log`, reutilizando `data_ingestion.storage`), testeado en `tests/test_feedback_registry.py`. Verificado sobre datos reales: guardado y recuperado sin pérdida de información.

### Requirement: Actualización del registro sin pérdida de validaciones existentes

El sistema DEBE poder combinar un registro de retroalimentación existente con alertas recién generadas, agregando las fechas nuevas en estado `pendiente` y preservando el estado de validación, la corrección y la observación de las fechas ya presentes.

#### Scenario: Nuevas alertas se agregan sin afectar validaciones previas

- **GIVEN** un registro de retroalimentación existente con una fecha ya `confirmada`, y un conjunto de alertas recién generadas que incluye esa misma fecha (con un valor de alerta distinto) más una fecha nueva
- **WHEN** se combina el registro existente con las alertas nuevas
- **THEN** la fecha ya `confirmada` conserva su estado de validación sin cambios, y la fecha nueva queda `pendiente`

Implementado en `src/human_feedback/registry.py` (`upsert_feedback_log`), testeado en `tests/test_feedback_registry.py`. Verificado sobre datos reales: al simular una nueva corrida de alertas (73 filas vs. 72 originales, incluyendo un día nuevo), la fecha ya confirmada conservó su estado de validación.

### Requirement: Integración de la retroalimentación con los registros de predicción

El sistema DEBE poder unir, por fecha, el registro de retroalimentación con la probabilidad predicha y la etiqueta real del modelo para esa misma fecha.

#### Scenario: Unión de retroalimentación con probabilidad predicha y etiqueta real

- **GIVEN** un registro de retroalimentación y un conjunto de predicciones con fecha, probabilidad predicha y etiqueta real
- **WHEN** se integran ambos conjuntos
- **THEN** cada fila del resultado contiene, para la misma fecha, el estado de validación, la corrección/observación (si existen), la probabilidad predicha y la etiqueta real

Implementado en `src/human_feedback/registry.py` (`integrate_feedback_with_predictions`), testeado en `tests/test_feedback_registry.py`. Verificado sobre datos reales: 72 filas integradas con `y_proba` y `stress_label` reales del modelo Random Forest de HU4.

### Requirement: Selección de observaciones para recalibración

El sistema DEBE poder seleccionar, de un registro de retroalimentación integrado con predicciones, únicamente las observaciones rechazadas que tienen una etiqueta corregida.

#### Scenario: Selección excluye confirmaciones y rechazos sin corrección

- **GIVEN** un registro integrado con una fila `confirmada`, una fila `rechazada` con etiqueta corregida, y una fila `rechazada` sin etiqueta corregida
- **WHEN** se seleccionan las observaciones de recalibración
- **THEN** solo la fila `rechazada` con etiqueta corregida queda seleccionada

Implementado en `src/human_feedback/recalibration.py` (`select_recalibration_observations`), testeado en `tests/test_recalibration.py`. Las confirmaciones se excluyen deliberadamente: no corrigen ningún error, ya que el modelo acertó.

### Requirement: Recalibración supervisada de un modelo candidato

El sistema DEBE poder reentrenar un modelo candidato sobre un conjunto de entrenamiento donde las etiquetas de las fechas seleccionadas para recalibración fueron reemplazadas por su etiqueta corregida.

#### Scenario: El modelo recalibrado predice distinto en las fechas corregidas

- **GIVEN** un modelo entrenado sobre un conjunto original y un conjunto de observaciones de recalibración que corrige la etiqueta de al menos una fecha presente en ese conjunto
- **WHEN** se recalibra el modelo con esas correcciones
- **THEN** el conjunto de entrenamiento usado para el modelo recalibrado tiene, en esas fechas, la etiqueta corregida en lugar de la original

Implementado en `src/human_feedback/recalibration.py` (`recalibrate_model`), testeado en `tests/test_recalibration.py`. Verificado sobre el dataset real (modelo Random Forest de HU4) con 3 correcciones sintéticas inyectadas — la retroalimentación humana real acumulada todavía es insuficiente en volumen (1-2 casos) para una prueba con múltiples correcciones simultáneas: las 3 observaciones fueron seleccionadas correctamente, las etiquetas de entrenamiento quedaron reemplazadas, y el modelo recalibrado predice distinto exactamente en esas 3 fechas respecto del modelo original (predicciones 1,1,0 pasan a 0,0,1, coincidiendo con la corrección inyectada).

## Limitaciones conocidas

- Estos estados se definen como funciones de Python en esta capacidad; la interfaz de usuario que los consume (`GET /feedback`, confirmar/rechazar) se especifica en `alerting-ui` (ver más abajo).
- Los 3 estados de validación (`pendiente`/`confirmada`/`rechazada`) son una simplificación deliberada; no capturan nivel de confianza ni múltiples revisores por alerta.
- `upsert_feedback_log` conserva la retroalimentación existente por fecha, pero no fusiona valores dentro de una misma fecha si dos ejecuciones distintas generaron alertas contradictorias — asume una única fuente de verdad de alertas por fecha.
- La verificación de recalibración usa correcciones sintéticas inyectadas, no retroalimentación humana real acumulada en volumen (todavía hay solo 1-2 casos reales) — es una prueba de que el mecanismo funciona, no una validación de que mejora el desempeño real del modelo con retroalimentación genuina.
- La recalibración no se dispara automáticamente desde la interfaz de usuario ni se persiste el modelo recalibrado; ambas cosas requieren un flujo de despliegue que todavía no existe.
- Expuesto por primera vez a través de una interfaz de usuario en `openspec/specs/alerting-ui/spec.md` (`GET /feedback`, confirmar/rechazar).
