# HU6 — Auditoría de revalidación del cierre

HU6 (issue #15) ya había sido cerrada formalmente, con sus 6 issues hijos (#80 a #85) cerrados como `completed`. Con posterioridad a ese cierre, la arquitectura fue extendida y corregida mediante una interfaz de usuario (`alerting-ui`), un mecanismo de recalibración con Model Registry versionado (HU5), un sistema de caché de predictor, ingesta de sensores mock/en vivo (ADR-0007), ruteo y aislamiento multi-sensor (ADR-0008), contratos temporales explícitos (ADR-0009) y el protocolo experimental formal `controlled_daily_v3`. Esta auditoría revisó el código **actual**, no solo la evidencia histórica de los PR originales de cierre. No se detectaron gaps técnicos bloqueantes. Los cuatro criterios de aceptación continúan satisfechos. No se requiere reapertura.

## 1. Criterios de aceptación

### CA1 — Todos los componentes intercambian información correctamente

**Estado: CUMPLE**

Fronteras principales confirmadas por lectura del código vigente:

- `data-ingestion → data-quality → predictive-modeling`: DataFrame con `timestamp`, columnas físicas del esquema, `is_anomaly` opcional.
- `predictive-modeling → alerts`: `y_proba` convertida a alerta binaria vía `alert_threshold`.
- `alerts → human-feedback`: registro inicializado con `fecha`, `target_timestamp`, `model_version` (identificador del predictor, ver nota más abajo), `target_threshold`.
- `human-feedback → recalibration`: exige procedencia temporal completa (`validated_at`, `target_timestamp`, `model_version`, `target_threshold`); falla explícitamente si falta.
- `predictor → Model Registry`: el `FittedPredictor` completo se serializa junto con metadata de contrato, validado antes de cargar.
- `backend → núcleo src/`: pasa siempre por `make_contract`/`FittedPredictor.validate`.
- `frontend → backend`: rutas con `sensor_id` explícito en cada llamada.
- `experiment-runner → núcleo`: mismas funciones del core, sin adaptador propio.

**Aclaración de nomenclatura:** el campo `model_version` persistido en el registro de retroalimentación contiene en realidad `FittedPredictor.model_id` (identificador lógico e inmutable del predictor), no un número de versión del Model Registry de MLflow. El comportamiento es correcto — permite recuperar el predictor exacto que emitió cada alerta —, pero el nombre puede inducir a error. Documentado formalmente en `openspec/specs/human-feedback/spec.md`.

### CA2 — El flujo completo de procesamiento se ejecuta sin errores

**Estado: CUMPLE**

Se distinguen tres caminos (ver sección 2), y los tres operan correctamente por lectura de código y de los tests existentes:

- **Core experimental** (`run_end_to_end_pipeline`): sin errores, verificado por `tests/test_architecture_integration_pipeline.py` y `tests/test_architecture_integration_functional.py`.
- **Backend/UI** (`execute_configured_pipeline`): sin errores, verificado por `backend/tests/test_pipeline.py`, `test_forecast.py`, `test_feedback.py`, `test_recalibration.py`.
- **Flujo experimental** (`experiment_runner`): consume el mismo core, sin path alternativo obsoleto.

El CLI (`scripts/run_end_to_end_pipeline.py`) no pudo reejecutarse en esta auditoría por ausencia de un intérprete Python en el entorno de auditoría. Esto constituye **evidencia de ejecución faltante**, no un defecto funcional detectado: por lectura de código, el script es compatible con la firma actual de `run_end_to_end_pipeline`.

### CA3 — La arquitectura genera alertas tempranas utilizando todos los componentes integrados

**Estado: CUMPLE**

Este criterio se interpreta contra una arquitectura configurable, no como una exigencia de que todos los componentes estén simultáneamente activos para cada alerta:

- **Modelado predictivo**: obligatorio en cualquier configuración.
- **Anomalías**: opcional (`include_anomaly_detection`), integrado correctamente cuando se activa (fit solo train, apply train+test, `is_anomaly` llega al modelo).
- **Datos sintéticos**: factor experimental de HU7 (`add_synthetic_rows`), aplicado solo sobre train cuando se activa, sin tocar test.
- **Feedback/recalibración**: ocurren después de emitir la alerta, no como precondición para generarla.

Existe al menos un camino válido para cada componente central (modelado, anomalías, sintéticos, feedback/recalibración).

### CA4 — La arquitectura queda preparada para la ejecución del plan experimental

**Estado: CUMPLE**

HU7 consumió efectivamente `run_end_to_end_pipeline` sin necesitar corregir ningún defecto de integración de HU6. La adaptación de datos sintéticos sobre variables ya construidas (`add_synthetic_rows`, en vez de columnas físicas crudas) es una **extensión experimental legítima** de HU7 sobre el orquestador base — no una corrección de un defecto de HU6, que documentó explícitamente desde el origen que la generación sintética no estaba integrada directamente en el orquestador por la falta de continuidad temporal de las filas físicas sintéticas.

## 2. Mapa actual de arquitectura

### Núcleo

```
dataset → calidad → labeling (umbral congelado) → feature engineering
→ split/purga (target_timestamp < cutoff) → anomalías opcionales (fit train, apply train+test)
→ selección automática o modelo explícito → predicción → alerta → feedback inicial
```

### Operativo (backend/UI)

```
dataset por sensor → backend → predictor (recalibrado > cacheado > Random Forest explícito)
→ último día observable (predict_available) → feedback humano → recalibración manual
→ Model Registry (por sensor) → forecast posterior reutiliza el predictor
```

### Experimental

```
dataset formal (melchor_romero_2024_consolidado) → controlled_daily_v3
→ configuraciones (anomalías/sintéticos parametrizables) → modelado (explícito por semilla)
→ métricas → MLflow → artefactos formales
```

Las tres rutas comparten las mismas capacidades subyacentes (`data-quality`, `predictive-modeling`, `human-feedback`) sin duplicarlas, pero configuran esas capacidades de forma distinta según su propósito: el núcleo y el flujo experimental permiten selección automática y anomalías/sintéticos parametrizables; el flujo operativo prioriza estabilidad frente a folds degenerados y desactiva anomalías por decisión operativa.

## 3. Modelo operativo vs. selección automática experimental

El backend operativo (`backend/app/pipeline.py::execute_configured_pipeline`) usa actualmente un contrato Random Forest explícito cuando no existe un predictor recalibrado o cacheado reutilizable para el sensor, en vez de la selección automática entre candidatos. Esto es una decisión operativa documentada inline en el código: la selección automática (`select_best_candidate`) falla explícitamente cuando algún fold de validación temporal carece de ambas clases, y la UI necesita poder producir un pronóstico incluso en esa situación.

La selección automática permanece disponible y vigente en el núcleo experimental y es la que efectivamente usa `controlled_daily_v3` cuando no se fija un modelo explícito para una comparación controlada. Esta divergencia es **intencional**, pero estaba **mal documentada**: `openspec/specs/alerting-ui/spec.md` seguía afirmando que la UI usa selección automática, una descripción que ya no coincide con el código vigente. Corregido en esta iteración (ver sección 5).

No se presenta a Random Forest como superior científicamente: es, en el flujo operativo vigente, el modelo elegido por una decisión de estabilidad operativa, no por evidencia de desempeño.

## 4. Auditoría de issues hijos (#80 a #85)

| Issue | Estado revalidado | Evidencia vigente |
|---|---|---|
| #80 — Definir contratos, entradas y salidas entre componentes | RATIFICADO CON LIMITACIÓN | `FittedPredictor` (contract.py) sin cambios en su forma original; extendido con `model_id`/`applied_feedback`/`calibration_end` por HU5 sin romper el contrato original |
| #81 — Integrar el componente de calidad con el componente predictivo | RATIFICADO CON LIMITACIÓN | Cifras originales (286/71) superadas por las correcciones de fuga temporal (292/74), ya documentadas con nota de actualización en `architecture-integration/spec.md`; el mecanismo de integración en sí no cambió de forma |
| #82 — Integrar las alertas con el mecanismo de retroalimentación | RATIFICADO CON LIMITACIÓN | Cifras originales (22 alertas/71 pendiente) históricas; extendido posteriormente por `init_prediction_feedback` (con `model_version`/`target_timestamp`) para el flujo de producción, sin invalidar el mecanismo original |
| #83 — Configurar la ejecución completa de la arquitectura | RATIFICADO CON LIMITACIÓN | `scripts/run_end_to_end_pipeline.py` no re-verificado numéricamente tras las correcciones de fuga (evidencia faltante, ver sección 6), pero compatible por lectura con la firma vigente |
| #84 — Ejecutar pruebas funcionales de integración | RATIFICADO CON LIMITACIÓN | `test_architecture_integration_functional.py` sin cambios; las 3 pruebas originales siguen siendo válidas, extendidas posteriormente por pruebas de integración a nivel backend/multi-sensor |
| #85 — Resolver incidencias y documentar los ajustes de integración | RATIFICADO CON LIMITACIÓN | La incidencia original (orden de imports) sigue resuelta; incidencias metodológicas posteriores (fuga temporal, `is_anomaly` en test) fueron documentadas y corregidas en HU3/HU4, no como parte de este issue pero sin contradecirlo |

Todos los issues #80 a #85 continúan **CLOSED / completed**. Ninguno se reabre.

## 5. Documentación sincronizada en esta iteración

- `openspec/specs/alerting-ui/spec.md`: rutas actualizadas para incluir `{sensor_id}` en todos los endpoints citados; distinción explícita entre el modelo operativo (Random Forest fijo) y la selección automática experimental; comportamiento actual de `POST /forecast/{sensor_id}/run` (veredicto único del último día observable, vía `predict_available`) documentado, preservando la verificación histórica de 71 filas del holdout marcada como tal; limitación de "ingesta de sensores en vivo" marcada como resuelta (ADR-0007/ADR-0008), con aclaración de que IoT sigue siendo fuente de datos, no contribución central; sección nueva de "Multi-sensor" documentando el aislamiento por sensor y la compatibilidad vigente del frontend; requirement de caché reformulado para no describirlo como caché del "modelo auto-seleccionado".
- `openspec/specs/human-feedback/spec.md`: nota explícita sobre la semántica de `model_version` (contiene `model_id`, no una versión de MLflow); rutas obsoletas sin `sensor_id` corregidas en las menciones de "Limitaciones conocidas".

No se modificó ningún requirement funcional ni escenario formal: los cambios son de precisión documental sobre comportamiento ya implementado.

## 6. CLI de HU6

`architecture-integration/spec.md` conserva la nota de que `scripts/run_end_to_end_pipeline.py` no fue re-verificado directamente después de las correcciones de fuga temporal. Esa nota sigue siendo verdadera y no se modifica en esta iteración: no se ejecutó el CLI (ausencia de intérprete Python en el entorno de esta auditoría), y no se inventa una ejecución ni se actualizan cifras. Conclusión segura: el script es compatible por inspección del código con `run_end_to_end_pipeline` vigente, sin nueva evidencia de ejecución en el entorno de auditoría.

## 7. Conclusión

Los cuatro criterios de aceptación de HU6 (CA1-CA4) permanecen en estado CUMPLE contra el código y las specs vigentes. No se detectaron gaps técnicos reales, fuga temporal, problemas de contratos funcionales, problemas de aislamiento multi-sensor, ni incompatibilidades actuales entre frontend y API — el frontend ya consume correctamente las rutas con `sensor_id` desde la resolución del breaking change de PR #163. El issue #15 y sus 6 issues hijos (#80-#85) permanecen cerrados; esta auditoría no reabre ni modifica ninguno de ellos. `openspec/specs/alerting-ui/spec.md` y `openspec/specs/human-feedback/spec.md` fueron sincronizadas en esta misma iteración para documentar el comportamiento ya implementado, sin modificar código, tests, ni ampliar el alcance funcional de ninguna capacidad.
