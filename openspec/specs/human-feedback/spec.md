# Spec: human-feedback

> **Actualización normativa 2026-09-05:** rige el protocolo [controlled_daily_v3](../../../docs/research/protocolo-experimental-v3.md) y ADR-0009. Los ejemplos cuantitativos anteriores son históricos; no deben confundirse con la nueva evaluación de objetivos observados ni con inferencia futura.

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

### Requirement: Recalibración temporalmente controlada con retroalimentación madura

El sistema DEBE poder generar una nueva versión del predictor mediante correcciones humanas cuyo objetivo temporal ya se encuentre disponible, preservando las correcciones aplicadas previamente y avanzando monótonamente la frontera temporal de entrenamiento (`trained_through`).

#### Scenario: Feedback aún no maduro no puede incorporarse

- **GIVEN** una corrección cuya fecha objetivo (`target_timestamp`) todavía no ha madurado
- **WHEN** se intenta recalibrar el predictor
- **THEN** esa corrección no puede utilizarse para reentrenar el predictor

#### Scenario: Corrección madura puede incorporarse a una versión posterior

- **GIVEN** una corrección rechazada, con etiqueta corregida, procedencia temporal completa (`validated_at`, `target_timestamp`, `model_version`, `target_threshold`) y target ya maduro
- **WHEN** se recalibra el predictor
- **THEN** la corrección se incorpora a una nueva versión del predictor y `trained_through` avanza sin retroceder

#### Scenario: Correcciones previamente aplicadas se preservan

- **GIVEN** un predictor que ya contiene correcciones humanas aplicadas (`applied_feedback`)
- **WHEN** se incorpora una nueva corrección válida
- **THEN** las correcciones anteriores se reaplican sobre el historial disponible y no se pierden

#### Scenario: Feedback incompatible falla explícitamente

- **GIVEN** feedback con horizonte, umbral de referencia (`target_threshold`) o procedencia temporal incompatible con el predictor, o correcciones provenientes de más de un predictor
- **WHEN** se solicita recalibración
- **THEN** el sistema falla explícitamente (`ValueError`) en lugar de incorporar esa corrección silenciosamente

**Nota sobre "más de un predictor" (H-01, 2026-09-06):** esta verificación se aplica únicamente a las correcciones nuevas (pendientes) que aporta la recalibración solicitada, no al historial completo del `feedback_log`. Correcciones ya reflejadas en `applied_feedback` legítimamente provienen de un predictor anterior (fueron feedback de un ciclo HITL previo) y se siguen reaplicando sin problema; lo que sigue estando prohibido es que las correcciones *nuevas* de una misma solicitud de recalibración mezclen `model_version` de más de un predictor. Esto permite ciclos HITL sucesivos (forecast → feedback → recalibración → nuevo forecast → nuevo feedback → nueva recalibración) sin que el log acumulado, que mezcla `model_version` de distintos predictores a través del tiempo, bloquee indebidamente la siguiente recalibración.

Implementado en `src/human_feedback/recalibration.py` (`recalibrate_predictor`). Este mecanismo es distinto y más completo que `recalibrate_model` (requirement anterior): en vez de recibir directamente `X_train`/`y_train`, opera sobre el `FittedPredictor` versionado (`predictive_modeling.contract`) y su historial de feedback (`feedback_log`), exigiendo que cada corrección tenga procedencia temporal verificable. Solo incorpora observaciones cuyo `target_timestamp` ya maduró (`target_timestamp < now`) y cuya validación humana ocurrió después de esa maduración (`validated_at >= target_timestamp + 1 día`); una observación incorporada de este modo deja de poder evaluarse fuera de muestra para ese mismo predictor, ya que `trained_through` avanza para cubrirla. Falla explícitamente si falta historial de features para reaplicar una corrección ya aplicada, si las clases resultantes no incluyen ambas categorías, o si no hay correcciones nuevas y maduras pendientes de aplicar. Genera un nuevo `model_id` y valida el contrato resultante antes de devolver el predictor actualizado. Es el mecanismo utilizado por `POST /recalibrate/{sensor_id}` (`openspec/specs/alerting-ui/spec.md`); no reemplaza a `recalibrate_model`, que permanece como mecanismo funcional base para verificar, de forma aislada, que una corrección reemplaza una etiqueta y provoca un reentrenamiento.

**Nota sobre la nomenclatura de `model_version`:** el campo persistido `model_version` en el registro de retroalimentación (`src/human_feedback/schema.py`) conserva ese nombre por compatibilidad histórica, pero en el flujo operativo vigente contiene `FittedPredictor.model_id` — el identificador lógico e inmutable del predictor que emitió la alerta — y no un número de versión del Model Registry de MLflow, que es una noción distinta. El comportamiento es correcto: esta diferencia es justamente lo que permite que `load_predictor_by_id(...)` recupere el predictor exacto que originó el feedback, independientemente de cuántas veces se haya registrado una nueva versión en MLflow desde entonces. No se renombra la columna ni se modifica el esquema en esta iteración.

## Limitaciones conocidas

- Estos estados se definen como funciones de Python en esta capacidad; la interfaz de usuario que los consume (`GET /feedback/{sensor_id}`, confirmar/rechazar) se especifica en `alerting-ui` (ver más abajo).
- Los 3 estados de validación (`pendiente`/`confirmada`/`rechazada`) son una simplificación deliberada; no capturan nivel de confianza ni múltiples revisores por alerta.
- `upsert_feedback_log` conserva la retroalimentación existente por fecha, pero no fusiona valores dentro de una misma fecha si dos ejecuciones distintas generaron alertas contradictorias — asume una única fuente de verdad de alertas por fecha.
- La verificación de recalibración usa correcciones sintéticas inyectadas, no retroalimentación humana real acumulada en volumen (todavía hay solo 1-2 casos reales) — es una prueba de que el mecanismo funciona, no una validación de que mejora el desempeño real del modelo con retroalimentación genuina.
- ~~La recalibración no se dispara automáticamente desde la interfaz de usuario ni se persiste el modelo recalibrado; ambas cosas requieren un flujo de despliegue que todavía no existe.~~ **Actualización (2026-08-19):** resuelto — ver `openspec/specs/alerting-ui/spec.md`, requirement "Disparo manual de recalibración desde la interfaz" (`POST /recalibrate/{sensor_id}`, registro versionado en el Model Registry de MLflow, ADR-0006).
- Expuesto por primera vez a través de una interfaz de usuario en `openspec/specs/alerting-ui/spec.md` (`GET /feedback/{sensor_id}`, confirmar/rechazar).
