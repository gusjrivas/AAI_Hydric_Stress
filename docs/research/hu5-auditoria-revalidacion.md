# HU5 — Auditoría de revalidación del cierre

HU5 (issue #14) ya había sido cerrada formalmente, con sus 8 issues hijos (#72 a #79) cerrados como `completed`. Con posterioridad a ese cierre, el ciclo de retroalimentación fue extendido mediante una interfaz de usuario (`alerting-ui`), un Model Registry versionado en MLflow y un mecanismo de recalibración con garantías temporales explícitas (`recalibrate_predictor`). Esta auditoría revisó el estado **actual** del código, no solo la evidencia histórica de los PR originales de cierre. Los cuatro criterios de aceptación continúan satisfechos. No se requiere reapertura.

## 1. Criterios de aceptación

### CA1 — Registro de validación de alertas

**Estado: CUMPLE**

Estados vigentes: `pendiente`, `confirmada`, `rechazada` (`src/human_feedback/schema.py::VALIDATION_STATES`). Corrección (`etiqueta_corregida`) y observación son opcionales. Un rechazo puede registrarse sin corrección — es un comportamiento deliberado del esquema, no un descuido —, pero esos rechazos sin corrección no son elegibles para recalibración (ver CA2).

Una validación humana constituye una señal de retroalimentación, no equivale automáticamente a ground truth agronómico certificado: se convierte en etiqueta de entrenamiento únicamente cuando existe una corrección explícita y, en el mecanismo vigente de producción, cuando el día objetivo correspondiente ya maduró.

### CA2 — Incorporación a recalibración supervisada

**Estado: CUMPLE**

`select_recalibration_observations` selecciona exactamente las filas con `estado_validacion == "rechazada"` y `etiqueta_corregida` no nula. Sobre esa selección operan dos mecanismos de recalibración (ver sección 2):

- `recalibrate_model`: mecanismo funcional original de HU5.
- `recalibrate_predictor`: mecanismo temporalmente controlado utilizado en el flujo integrado posterior.

### CA3 — Integración con la arquitectura

**Estado: CUMPLE**

Loop confirmado de punta a punta: `POST /forecast/run` → `GET /feedback` (confirmar/rechazar) → rechazo con corrección → disparo manual de `POST /recalibrate` → nueva versión de predictor registrada en el Model Registry de MLflow → el próximo `POST /forecast/run` reutiliza esa versión (`load_latest_recalibrated_model`, `skip_fit=True`). La recalibración nunca se dispara implícitamente al confirmar o rechazar una alerta.

### CA4 — Información disponible para la evaluación experimental

**Estado: CUMPLE**

Significa que feedback, correcciones y predicciones asociadas pueden persistirse, recuperarse e integrarse (`init_feedback_log`, `update_feedback`, `upsert_feedback_log`, `integrate_feedback_with_predictions`). **No significa** que el efecto cuantitativo del mecanismo de retroalimentación humana (Human-in-the-Loop) ya haya sido demostrado experimentalmente: esa evaluación formal permanece diseñada pero no ejecutada (ver sección 4).

## 2. Recalibración funcional y recalibración temporalmente controlada

`src/human_feedback/recalibration.py` contiene dos mecanismos, ambos vigentes, con propósitos distintos:

### `recalibrate_model`

- mecanismo original de HU5;
- recibe `X_train`/`y_train`/`dates_train` directamente;
- sustituye, en `y_train`, la etiqueta de cada fecha presente en las observaciones de recalibración por su etiqueta corregida;
- clona y reentrena el modelo sobre ese conjunto corregido;
- útil como prueba funcional aislada de que el mecanismo de sustitución de etiquetas y reentrenamiento funciona.

### `recalibrate_predictor`

- mecanismo vigente, más completo, utilizado por el flujo integrado (`POST /recalibrate`);
- trabaja sobre el `FittedPredictor` versionado (contrato de `predictive-modeling`), no sobre arrays sueltos de entrenamiento;
- valida procedencia temporal del feedback: exige `validated_at`, `target_timestamp`, `model_version` y `target_threshold` presentes en cada fila considerada;
- comprueba que el horizonte de cada corrección (`target_timestamp = fecha + horizon_days`) sea compatible con el contrato del predictor;
- comprueba que el `target_threshold` de cada corrección coincida con el umbral vigente del predictor;
- conserva y reaplica el feedback previamente aplicado (`applied_feedback`) junto con las correcciones nuevas;
- solo incorpora observaciones cuyo target ya está maduro (`target_timestamp < now`) y cuya validación humana ocurrió después de esa maduración (`validated_at >= target_timestamp + 1 día`);
- falla explícitamente si falta historial de features necesario para reaplicar alguna corrección ya aplicada o alguna corrección pendiente;
- exige que el resultado final contenga ambas clases;
- genera un nuevo `model_id`;
- actualiza `trained_through` sin retroceder temporalmente (toma el máximo entre el valor anterior y el nuevo target maduro incorporado);
- valida nuevamente el contrato del predictor resultante antes de devolverlo.

Este segundo mecanismo **no constituye una nueva funcionalidad de esta iteración**: ya existe en el código, ya está testeado (`tests/test_controlled_protocol.py`), y ya es el mecanismo efectivamente invocado por `POST /recalibrate` en producción. Esta iteración solo formaliza documentalmente su comportamiento en `openspec/specs/human-feedback/spec.md` y en ADR-0006, sin modificar código.

## 3. Punto metodológico central: maduración temporal

Una observación utilizada primero para evaluación puede incorporarse posteriormente al entrenamiento **solo** después de que:

- su target esté temporalmente disponible (haya madurado);
- la validación/corrección humana haya ocurrido después de esa maduración;
- a partir de ese momento, deje de tratarse como evidencia out-of-sample independiente para ese mismo predictor (`trained_through` avanza para cubrirla).

**Una observación incorporada posteriormente a recalibración no puede volver a presentarse como muestra independiente para demostrar mejora del modelo recalibrado.**

Se distinguen tres nociones que no deben confundirse:

1. **Evaluación independiente**: medir desempeño sobre una observación que nunca participó del entrenamiento de ese predictor.
2. **Feedback posterior**: la validación humana registrada sobre una alerta, con o sin corrección.
3. **Incorporación al entrenamiento posterior**: cuando una observación corregida y madura pasa a formar parte del conjunto de entrenamiento de una versión posterior del predictor, dejando de servir como evidencia independiente para esa versión.

No se encontró en el código ningún flujo donde una observación se use simultáneamente como (1) y (3) para el mismo predictor: `recalibrate_predictor` exige maduración y posterioridad de la validación humana en dos puntos distintos del pipeline (al validar la alerta en `backend/app/routers/feedback.py`, que bloquea confirmar/rechazar un target inmaduro, y al recalibrar), por lo que ninguna corrección puede originarse antes de que su target exista.

## 4. Evidencia experimental de Human-in-the-Loop: qué demuestra y qué no

La prueba histórica documentada en la spec (`recalibrate_model`, con 3 correcciones sintéticas inyectadas) constituye **evidencia funcional/de integración**: demuestra que una corrección puede ser seleccionada, incorporada al conjunto de entrenamiento, y que el modelo recalibrado predice distinto exactamente en las fechas corregidas respecto del modelo original.

Esta prueba **no demuestra** que la retroalimentación humana (Human-in-the-Loop) mejora el desempeño predictivo real. El volumen real de feedback humano acumulado sigue siendo reducido (1-2 casos históricos, ya documentado como limitación en la spec). La evaluación cuantitativa formal del aporte del feedback (comparar un modelo congelado contra un reentrenamiento sin corrección y contra un reentrenamiento con corrección, sobre los mismos datos) permanece **diseñada pero no ejecutada** en `docs/research/protocolo-experimental-v3.md` y en ADR-0009. Esta auditoría no declara esa evaluación como completada ni la ejecuta.

## 5. Trazabilidad

Disponible actualmente:

- fecha de observación;
- `target_timestamp`;
- estado de validación;
- etiqueta corregida;
- observación textual;
- `validated_at`;
- `model_version` (qué predictor produjo la alerta validada);
- `target_threshold`;
- `applied_feedback` (correcciones ya incorporadas a un predictor);
- `model_id` de la nueva versión resultante de cada recalibración.

Limitaciones de trazabilidad que continúan vigentes:

- no se registra identidad de usuario/revisor (quién confirmó o rechazó cada alerta);
- no existe soporte formal para múltiples revisores sobre la misma alerta;
- los tres estados de validación son una simplificación deliberada, sin nivel de confianza.

Ninguna de estas limitaciones se implementa en esta iteración.

## 6. Auditoría de issues hijos (#72 a #79)

| Issue | Estado revalidado | Evidencia vigente |
|---|---|---|
| #72 — Definir casos de uso y estados de validación de las alertas | RATIFICADO | `VALIDATION_STATES`, sin cambios desde el origen |
| #73 — Diseñar el modelo de datos para registrar retroalimentación | RATIFICADO | `FEEDBACK_COLUMNS`/`schema.py`, sin cambios en su forma original; extendido (no reemplazado) por las columnas de procedencia temporal usadas en producción |
| #74 — Diseñar el flujo de interacción entre alerta, usuario y modelo | RATIFICADO CON LIMITACIÓN | `update_feedback` sin cambios de código; el flujo fue extendido posteriormente por la interfaz de usuario (`alerting-ui`) y por el control de maduración temporal en el backend, sin invalidar el cierre original |
| #75 — Implementar el registro de validaciones de alertas | RATIFICADO | `init_feedback_log`/`update_feedback`, sin cambios |
| #76 — Implementar el registro de correcciones y observaciones | RATIFICADO | Mismo módulo, sin cambios |
| #77 — Integrar la retroalimentación con los registros de predicción | RATIFICADO CON LIMITACIÓN | `integrate_feedback_with_predictions` sin cambios de código; extendido posteriormente por el flujo de producción que agrega procedencia temporal a la integración, sin invalidar el cierre original |
| #78 — Definir reglas para seleccionar observaciones de recalibración | RATIFICADO | `select_recalibration_observations`, sin cambios, coincide exactamente con la spec |
| #79 — Implementar una prueba de recalibración supervisada | RATIFICADO CON LIMITACIÓN | `recalibrate_model` (mecanismo probado por este issue) sin cambios; extendido posteriormente por `recalibrate_predictor` (Model Registry y controles temporales), ahora documentado formalmente en esta iteración, sin invalidar el cierre original |

Todos los issues #72 a #79 continúan **CLOSED / completed**. Ninguno se reabre.

## 7. Conclusión

Los cuatro criterios de aceptación de HU5 (CA1-CA4) permanecen en estado CUMPLE contra el código y las specs vigentes. No se detectaron gaps técnicos bloqueantes ni contaminación del conjunto de evaluación: el mecanismo de producción (`recalibrate_predictor`) implementa garantías anti-contaminación más estrictas que las documentadas originalmente en ADR-0006. El issue #14 y sus 8 issues hijos (#72-#79) permanecen cerrados; esta auditoría no reabre ni modifica ninguno de ellos. `openspec/specs/human-feedback/spec.md` y ADR-0006 fueron sincronizados en esta misma iteración para documentar el comportamiento ya implementado de `recalibrate_predictor`, sin modificar código, tests, ni ampliar el alcance funcional de la capacidad.
