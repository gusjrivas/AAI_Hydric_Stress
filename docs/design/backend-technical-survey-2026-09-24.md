# Relevamiento técnico del backend — Paso 1

**Fecha de corte:** 2026-09-24 (America/Buenos_Aires)

**Repositorio:** `gusjrivas/AAI_Hydric_Stress`

**Snapshot fijo relevado:** `f17fe658bad4726202fe13784bb716c06468af9a` (`origin/main`)
**Carácter del documento:** descriptivo y preparatorio; no constituye auditoría, certificación de cierre ni evaluación de suficiencia científica.

## 1. Condiciones de acceso y método

El `fetch` remoto fue exitoso y permitió fijar `origin/main` en el SHA indicado. En el momento del relevamiento `HEAD` coincidía con `origin/main`. El árbol de trabajo no estaba limpio: existían ocho modificaciones ajenas bajo `replay_packages/`. Se preservaron sin abrirlas, modificarlas ni revertirlas. No se cambió de rama, no se creó un checkout alternativo y no se hizo commit, push, PR, merge, rebase, tag ni release.

La inspección siguió llamadas reales desde routers y servicios hacia el núcleo, y contrastó código, contratos, especificaciones, ADR y pruebas existentes. No se instalaron dependencias, no se levantaron servicios, no se ejecutaron suites ni pruebas individuales, y no se cargaron modelos serializados. Tampoco se ejecutaron entrenamiento, inferencia nueva, recalibración, etapas A/B/C, auxiliares o apertura de holdouts. Los archivos de resultados restringidos y el contenido de paquetes de reproducción no se abrieron; solo se relevaron su existencia, política y contratos desde código versionado y documentación permitida.

### 1.1 Convención de evidencia

- **Código identificado:** comportamiento observado por lectura del snapshot fijado.
- **Documentación declarada:** comportamiento afirmado por una spec, ADR o informe; por sí solo no prueba implementación.
- **Prueba existente:** archivo/caso localizado; no se ejecutó en este paso y no implica que pase actualmente.
- **Ejecución previa reportada:** resultado declarado en un documento anterior; se conserva con su fecha/contexto y no fue revalidado aquí.
- **No comprobado:** requiere entorno, artefacto, modelo o ejecución que quedó fuera del alcance.
- **Punto a verificar en auditoría:** tensión entre fuentes o garantía que necesita comprobación independiente; no se presenta como defecto confirmado.

### 1.2 Trazabilidad del relevamiento

| Recorrido | HU/capacidad principal | Fase CRISP-DM | Impacto de este paso |
| --- | --- | --- | --- |
| Pronóstico operativo | HU4 `predictive-modeling`, HU5 `human-feedback`, HU6 `architecture-integration`, UI `alerting-ui` | modelado / despliegue e integración experimental | Ninguno; solo lectura y documentación. |
| Evaluación y ensamble | HU7 `experiment-runner`, gobernanza `scientific-closure` | modelado / evaluación | Ninguno; no cambia configuración, semillas, gates ni artefactos. |
| Reproducción histórica | HU7/HU8, change `add-causal-historical-replay` | evaluación / comunicación de evidencia | Ninguno; no regenera ni abre el paquete. |
| Persistencia y trazabilidad | HU2, HU4, HU5, HU6, HU7 | preparación / modelado / evaluación | Ninguno. |
| Feedback y linaje | HU5 `human-feedback` | evaluación / mejora supervisada | Ninguno; no dispara recalibración. |

Este relevamiento no cambia hipótesis, propósito, alcance, arquitectura ni configuración experimental. Tampoco autoriza A/B/C, auxiliares, apertura de holdouts, inicialización de ledgers ni merge alguno.

## 2. Inventario ejecutivo de capacidades

| Capacidad | Estado descriptivo respaldado por código | Entrada principal | Persistencia/salida principal | Separación relevante |
| --- | --- | --- | --- | --- |
| Pronóstico legacy por sensor | Implementado | `POST /forecast/{sensor_id}/run` | feedback Parquet + predictor en MLflow; `ForecastRunResponse` | Usa predictor recalibrado, caché o RF explícito; no usa el ensamble v4. |
| Emisión operativa v2 | Implementada detrás de feature gate | `POST /api/v2/sensors/{sensor_id}/forecasts` | JSON operacional atómico por sensor + snapshot original; tanda 1/2/3 días | Solo inferencia con bundles operativos preexistentes; no entrena por HTTP. |
| Evaluación v4 | Implementada como runners y contratos | CLI/runners `controlled_daily_v4` | directorios de artefactos A/B/C, contratos, fingerprints y ledger | Experimental; no hay conexión acreditada con las APIs/UI. |
| Soft voting v4 | Implementado | `run_stage_a` y `SoftVotingClassifier` | OOF, config congelada, pesos y salidas por etapa | Pesos de combinación 1/3 no son balanceo de clases. |
| Reproducción histórica causal | Implementada detrás de feature gate | `/replay/*` | lectura de paquete autorizado + feedback JSONL separado | Proyecta predicciones archivadas; no ejecuta el modelo. |
| Feedback legacy y recalibración | Implementado | `/feedback/*`, `POST /recalibrate/{sensor_id}` | Parquet, Model Registry MLflow y artefacto de linaje | Solo correcciones maduras, rechazadas y compatibles. |
| Revisión v2 | Implementada | `POST .../forecasts/{forecast_id}/reviews` | documento operacional JSON por sensor | Contrato distinto del feedback legacy; elegibilidad expuesta, no se observó disparo automático de recalibración. |
| Catálogo/lecturas v2 | Implementado | `/api/v2/sectors`, `/sensors`, `/readings` | JSON de catálogo + Parquet por sensor | Revisión optimista, locks y escritura atómica. |

## 3. Recorrido A — pronóstico operativo

### 3.1 Camino legacy

**Punto de entrada.** `backend/app/routers/forecast.py::run_forecast`, ruta `POST /forecast/{sensor_id}/run`.

**Llamadas principales identificadas en código.** El router obtiene el dataset del sensor mediante `backend/app/pipeline.py::load_dataset_or_raise`; esa función compara el fingerprint `(mtime, size)` antes y después de leer para rechazar una lectura inestable. Luego `execute_configured_pipeline` arma el contrato con `FEATURE_COLUMNS`, `LABEL_COLUMN` y `HORIZON_DAYS`, y aplica esta prioridad:

1. predictor solicitado por identidad o último predictor recalibrado compatible de MLflow;
2. predictor cacheado en memoria para el mismo sensor y fingerprint;
3. `build_candidate_models(...)["random_forest"]` como modelo operativo explícito.

En este camino legacy `FittedPredictor` contiene un único `predictor.model`; no hay un calibrador serializado separado como en v2. `predict_available` obtiene la salida mediante `positive_probability(predictor.model, ...)`.

El core llamado es `src/architecture_integration/pipeline.py::{run_end_to_end_pipeline,predict_available}`. La partición se fija en la fecha de la fila ubicada al 80% del dataset ordenado. Las variables base son humedad de suelo, radiación solar y humedad relativa; `src/predictive_modeling/feature_engineering.py` agrega lags 1/2/3 y ventanas 3/7. El horizonte legacy es 3 días. La detección de anomalías se pasa como `False`. `predict_available` permite emitir sobre el último día observable sin exigir una etiqueta futura ya conocida.

**Regla de alerta.** `src/predictive_modeling/alerts.py::generate_alerts` produce alerta cuando `y_proba >= 0.5`. El target se vincula a `target_timestamp = fecha + 3 días` por el contrato temporal del predictor.

**Persistencia y respuesta.** `run_forecast` crea filas mediante `human_feedback.schema::init_prediction_feedback`; conserva probabilidad, alerta, `target_timestamp`, umbral y `model_version` —nombre histórico que contiene `FittedPredictor.model_id`—. Combina solo fechas nuevas con el Parquet por sensor y no reemplaza una emisión ya revisada. Devuelve `ForecastRunResponse` con veredictos (`fecha`, alerta, probabilidad, fecha objetivo), filas de train/test y advertencia de selección.

**Ausencias/incompatibilidades previstas.** 404 sin dataset; 422 para dataset vacío, historial insuficiente o incompatibilidades del pipeline; 409 si existe una alerta histórica sin contrato temporal completo. La carga desde MLflow valida igualdad del contrato esperado y tipo `FittedPredictor`.

**Dependencias.** pandas/Parquet, scikit-learn, MLflow/Model Registry y almacenamiento local por sensor.

**Pruebas existentes no ejecutadas.** `backend/tests/test_forecast.py`, `backend/tests/test_pipeline.py`, `tests/test_architecture_integration_pipeline.py`, `tests/test_architecture_integration_functional.py`, `tests/test_operational_inference.py`, `tests/test_feature_engineering.py`, `tests/test_alerts.py`, `tests/test_no_leakage.py`, `tests/test_model_registry.py`.

**Documentación normativa/declarativa.** `openspec/specs/predictive-modeling/spec.md`, `openspec/specs/architecture-integration/spec.md`, `openspec/specs/alerting-ui/spec.md`, ADR-0008 y ADR-0009. La distinción entre RF operativo y selección experimental está declarada en la spec de UI y en `docs/research/hu6-auditoria-revalidacion.md`.

**Limitaciones.** La emisión legacy produce el último día y un horizonte, no la tanda v2 de tres horizontes. La caché es de proceso. Este paso no comprobó un registro MLflow disponible ni cargó modelos.

**Punto a verificar en auditoría — orden de preprocesamiento.** `openspec/specs/architecture-integration/spec.md` declara partir el dataset crudo antes de imputar, mientras `run_end_to_end_pipeline` obtiene `train_raw` para calibración pero ejecuta `prepare_daily_features(ordered, contract)` sobre la serie completa antes del split final de train/test. Como la imputación implementada es causal, esta tensión puede resultar metodológicamente equivalente; debe demostrarse con fixtures temporales y no se clasifica aquí como fuga confirmada.

### 3.2 Camino operativo v2

**Punto de entrada.** `backend/app/routers/producer_v2.py::create_forecasts`, ruta `POST /api/v2/sensors/{sensor_id}/forecasts`, con `Idempotency-Key` obligatorio y feature gate.

**Llamadas principales identificadas en código.** `src/architecture_integration/producer_emission.py::emit_forecasts` captura con `load_dataset_snapshot` los bytes Parquet y el DataFrame en una misma instantánea, valida calendario UTC con `validate_utc_calendar`, fija `as_of_date` en la última medición y rechaza lecturas futuras. Para cada horizonte 1, 2 y 3 intenta `operational_inference::{load_operational_bundle,predict_operational_bundle}` sobre `bundle_root/<sensor>/horizon_<h>`.

**Modelo y calibrador.** El bundle operativo contiene `model.joblib`, `calibrator.joblib` y metadata. `load_operational_bundle` carga y valida ambos objetos, sus clases, features e identidades; sin embargo, la inferencia observada llama directamente a `positive_probability(bundle.calibrator, row)`. El objeto `model` no vuelve a invocarse en `predict_operational_bundle` después de validarse. Los binarios solo se cargan al ejecutar esa ruta. En este relevamiento no se cargaron y no se verificó que haya bundles desplegados.

**Horizonte, fecha objetivo y alerta.** Cada slot se identifica por horizonte 1/2/3 y deriva `target_date = as_of_date + horizon_days`. La regla exacta es `alert = score >= metadata['decision_threshold']`. La implementación devuelve `score_kind='calibrated_probability'`, pero fija `display_probability=None`, `probability_status='not_qualified'` y `probability_reason_code='incompatible_assessment'`; por eso no presenta ese score como porcentaje operativo calificado. También expone el umbral del evento y la referencia de modelo.

**Persistencia y respuesta.** `human_feedback.operational_repository::OperationalRepository.emit_snapshot` toma un lock no bloqueante y hace un único commit atómico del snapshot original, los slots y la respuesta idempotente. El documento local es `ui_metadata/operational_v2__<sensor_id>.json`; el artefacto conserva SHA-256 y bytes Parquet codificados, y metadata de bundles usados. La API devuelve tanda, revisión, slots disponibles o no disponibles y causas.

**Ausencias/incompatibilidades previstas.** `no_readings`, `incompatible_environment`, `already_available` y razones de `BundleUnavailable`; además 409 por calendario/futuro/conflicto de snapshot/idempotencia/operación concurrente, 422 por entrada, y 503 por almacenamiento/captura. Los éxitos de slot son inmutables ante reintentos.

**Dependencias.** Parquet local, scikit-learn/joblib según bundle, locks del sistema, JSON local y catálogo por sensor. La API no entrena por HTTP.

**Pruebas existentes no ejecutadas.** `backend/tests/test_producer_v2_emission.py`, `backend/tests/test_producer_v2_forecasts.py`, `backend/tests/test_producer_v2.py`, `tests/test_operational_inference.py`, `tests/test_operational_horizon_contract.py`, `tests/test_operational_multihorizon_preparation.py`, `tests/test_storage.py`.

**Documentación normativa/declarativa.** ADR-0013, `docs/design/backend-producer-ui-emission-dependencies.md`, `docs/design/backend-producer-ui-first-delivery.md`, `openspec/specs/predictive-modeling/spec.md` y `openspec/specs/architecture-integration/spec.md`.

**Limitaciones.** No se acreditó despliegue real de bundles, ni disponibilidad de calibradores/modelos, ni una ejecución actual. V2 y legacy conviven con contratos y persistencias diferentes.

## 4. Recorrido B — evaluación experimental y ensamble

**Punto de entrada.** `src/experiment_runner/controlled_daily_v4/cli.py` despacha etapas; el núcleo de A es `stage_a_runner.py::run_stage_a`, B `stage_b_runner.py::run_stage_b` y C `stage_c_runner.py::run_stage_c`. No se invocó ninguno.

**Familias implementadas.** `models.py` implementa regresión logística escalada, Random Forest, HistGradientBoosting y `SoftVotingClassifier`. `config.py` declara grillas, semilla 42, horizonte/gap 3, nested temporal CV 3×3, threshold 0.5 y orden de simplicidad LR < RF < HGB < soft voting.

**Selección de configuraciones.** Cada familia recorre su grilla y evalúa configuraciones dentro de folds temporales. `selection.py::select_family` usa MCC OOF concatenado, soporte por outer folds, bootstrap pareado, margen práctico 0.05 y conjunto de equivalencia. Solo declara ganador estable si supera a rivales bajo la regla predeclarada; de otro modo elige por simplicidad y lo rotula `SIN_GANADOR_ESTABLE`, no como superioridad. Si el soporte es insuficiente devuelve `NO_VALID_SELECTION`.

**Construcción y decisión del ensamble.** El soft voting reentrena una base por cada familia LR/RF/HGB y promedia `predict_proba`. Los pesos de combinación son fijos e iguales: 1/3, 1/3, 1/3. `predict` toma la clase con máxima probabilidad combinada; la decisión de estrés usa el threshold normativo 0.5 en las etapas que consumen el score.

**Pesos de combinación versus balanceo.** Los pesos 1/3 determinan cuánto aporta la probabilidad de cada familia al promedio. El balanceo de clases es distinto: `compute_sample_weight` calcula `n_train/(n_classes*n_train_c)` exclusivamente con el `y` del train de cada fold y cada base decide `none` o `sample_weight_balanced`. No se usa `class_weight` ni se deriva un concepto del otro.

**Salidas conservadas.** `artifacts.py` escribe métricas, OOF, decisiones, advertencias, fingerprints, identidad de código/entorno y `frozen_config.json`; para soft voting conserva configuraciones base, modos de balanceo y pesos de combinación. B y C conservan predicciones candidatas y baselines, métricas, fingerprints de entrenamiento/evaluación y diagnósticos; los contratos de transferencia y la admisibilidad cruzan identidades entre etapas. C agrega custodia/ledger y recuperación.

**Modelos entrenados versus configuraciones.** Los objetos de estimador existen en memoria durante runners. `frozen_config.json`, `transfer_contract.py` y los manifiestos son configuraciones/contratos reproducibles, no modelos entrenados serializados. Los bundles operativos v2 sí son artefactos de modelo/calibrador para inferencia, pero pertenecen a otro recorrido. No se verificó un mecanismo que publique automáticamente un ganador v4 como bundle operativo.

**Conexión efectiva con backend/UI.** No se encontró import, endpoint o adaptador que conecte `controlled_daily_v4` o `SoftVotingClassifier` con `backend/app/routers/*`, `backend/app/pipeline.py` o `producer_emission.py`. Legacy usa predictor recalibrado/cacheado/RF; v2 usa bundles operativos por sensor/horizonte. La existencia del ensamble en el repositorio no acredita integración con UI.

**Dependencias.** numpy, pandas, scikit-learn, artefactos locales versionados, CSV científicos y entorno fijado por constraints. MLflow pertenece a recorridos experimentales anteriores/operativos, mientras `controlled_daily_v4/artifacts.py` declara que no registra por sí solo en MLflow.

**Pruebas existentes no ejecutadas.** `tests/test_controlled_daily_v4_models.py`, `test_controlled_daily_v4_soft_voting.py`, `test_controlled_daily_v4_selection.py`, `test_controlled_daily_v4_features.py`, `test_controlled_daily_v4_splits.py`, `test_controlled_daily_v4_stage_a_integration.py`, `test_controlled_daily_v4_stage_b_*`, `test_controlled_daily_v4_stage_c_*`, `test_controlled_daily_v4_artifacts.py`, `test_controlled_daily_v4_transfer_contract.py`, `test_controlled_daily_v4_holdout_ledger.py` y pruebas de reproducibilidad/admisibilidad.

**Documentación normativa/declarativa.** `openspec/specs/experiment-runner/spec.md`, protocolo v4, ADR-0009/0010/0011, decisiones preejecución y `openspec/specs/scientific-closure/spec.md`.

**Limitaciones.** Este paso no inspeccionó resultados cerrados, no volvió a evaluar A/B/C y no certifica el estado científico. El README de cierre conserva una no conformidad histórica y distingue PASS estructural de cierre científico; este relevamiento no la reabre ni la resuelve.

## 5. Recorrido C — reproducción histórica

**Puntos de entrada.** Router `backend/app/routers/replay.py`, feature-gated y prefijado `/replay`: `GET /candidate`, `GET /predictions`, `GET /predictions/{timestamp_origen}`, `GET /history`, `POST/GET /predictions/{timestamp_origen}/feedback`.

**Paquete y candidato admitidos.** El cliente no elige ruta, paquete ni run: `backend/app/dependencies.py` carga una ubicación configurada por servidor. La política externa al paquete está hardcodeada en `src/historical_replay/admission_policy.py`: experimento `4`, child run `1157696b7bb941e394c5af530c762b07`, parent `6d516bb9f778450f8fbe2e5492818e57`, configuración `base`, semilla `4`, commit ejecutable `2a40ee68c52d2eb5e2040a36b1029f756f9c048a` y dataset SHA-256 `121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e`. Estos valores se leyeron de política versionada; no se abrió el paquete.

**Política de admisión e integridad.** `package_loader.py::load_package` exige versión soportada, inventario, confinamiento de rutas y SHA-256 de custodia; cruza parent/child, `mlflow.parentRunId`, estados `FINISHED`, config/semilla/commit, procedencia del dataset y hash histórico. También valida fechas de entrenamiento, maduración `t+h` anterior al corte, concordancia horizonte/corte y que los orígenes de predicción no precedan el cutoff.

**Identidad, horizonte y filtrado causal.** `records.py` tipa identidad `(experiment_id, run_id, config_name, seed, timestamp_origen)`, `target_timestamp`, probabilidad, clase y estado observado. `projection.py::project` devuelve `None` antes del origen; entre origen y target expone predicción sin resultado; desde target solo revela `y_true` y baselines si `target_observed` es verdadero. `history_view::filtered_history` limita la serie al reloj simulado.

**Vinculación con medición posterior.** `observations.py::link_observation` exige dataset/serie coincidente y exactamente una fila para la fecha objetivo. Mantiene separados valor crudo y estado (`medida`, `imputada`, `no_determinado`, `sin_dato_en_fuente`); si el registro afirma target observado pero el valor crudo falta, levanta inconsistencia. El router actual pasa `imputation_markers_df=None`, por lo que distingue `medida` de `no_determinado`, pero no acredita imputación por fila.

**Contratos consumidos por UI.** `schemas_replay.py` define ficha del candidato/evidencia/regla de etiqueta, lista de orígenes, predicción proyectada, medición original, historial y feedback. La API expone split y fecha máxima de entrenamiento por separado, identidad, horizonte, limitaciones y disclaimers. PR #215 agrega un recorrido guiado solo en UI; no cambia estos contratos ni el núcleo de replay en el snapshot.

**Punto a verificar en auditoría — deriva contractual de replay.** La spec delta exige en RH-02 `y_proba`, en RH-03 baselines, en RH-06 procedencia completa por predicción, en RH-13 ambos umbrales y en RH-05/RH-08 estados explícitos por medición. El contrato HTTP actual omite deliberadamente `y_proba`, baselines, parte de esa procedencia y el umbral de decisión; `/replay/history` entrega valor o `null`, no un estado por fila. `tasks.md` reconoce parte del trabajo como pendiente, mientras `traceability.md` marca requisitos implementados. Se registra como deriva entre spec/tareas/trazabilidad/API, no como defecto funcional confirmado.

**Separación de una ejecución nueva.** El router declara y el código confirma lectura/proyección local: no importa runners, no llama a `predict_proba`, no recalcula métricas y no necesita MLflow o red para servir el paquete ya validado.

**Feedback de demo.** `historical_replay.feedback::ReplayFeedbackStore` agrega un archivo JSONL por `package_id` dentro del directorio configurado, fuera del paquete y fuera del Parquet operativo. Solo admite feedback sobre identidad existente después de revelar el target; separa `registered_at` real de `simulated_at`. No alcanza `recalibrate_predictor` ni Model Registry. El aislamiento entre sesiones requiere directorios configurados distintos; `package_id` por sí solo no crea aislamiento de sesión.

**Pruebas existentes no ejecutadas.** `tests/test_historical_replay_{admission_policy,package_loader,records,projection,observations,history_view,feedback,imputation_markers}.py`, `tests/test_build_replay_package.py` y `backend/tests/test_replay.py`.

**Documentación normativa/declarativa.** change `add-causal-historical-replay`, su spec `historical-replay`, y los informes bajo `openspec/scientific-closure/causal-historical-replay-2026-09-22/`.

**Ejecución previa reportada, no revalidada.** `paso4-1-cierre-demo.md` reporta el 2026-09-23: 20 pruebas de package/build, 18 de backend replay y 124 de backend aprobadas, además de recorrido manual Docker. `paso4-1-1-cierre.md` registra feedback manual con `registered_at=2026-09-23T21:33:09.184712+00:00`. El segundo informe retracta expresamente una garantía anterior: no existe prueba de concurrencia ni lock explícito para escrituras JSONL simultáneas.

**Limitaciones.** No se inspeccionó contenido de paquete ni se revalidaron hashes. `GET /history` no expone estado de imputación por fila. La seguridad de dos POST concurrentes al mismo JSONL no está comprobada.

## 6. Recorrido D — persistencia y trazabilidad

### 6.1 Estrato legacy

- Datasets y feedback por sensor en Parquet mediante `data_ingestion.storage` y `human_feedback.registry`.
- `storage.py` aplica lock durante `save_dataset` y reemplazo atómico del archivo ya construido; los endpoints legacy hacen `load` → merge/update → `save` fuera de una única transacción/CAS. No quedó acreditada serialización del ciclo completo ni idempotencia HTTP, a diferencia de v2. Los snapshots unen bytes, SHA-256, fingerprint y DataFrame.
- Predictores emitidos y recalibrados en MLflow Model Registry, separados por convención de nombre/sensor. Metadata conserva contrato, threshold, `model_id`, `trained_through`, `calibration_end` y correcciones aplicadas.
- La emisión original se conserva por fecha: `run_forecast` agrega solo fechas no existentes; una revisión no es reemplazada por una corrida posterior.

### 6.2 Estrato operativo v2

- Catálogo JSON versionado con revisión optimista, lock y escritura atómica.
- `ui_metadata/operational_v2__<sensor>.json` integra tandas, forecasts, revisiones e idempotencia.
- IDs de batch y forecast son SHA-256 deterministas sobre sensor, fecha, horizonte y versión de contrato.
- Un lock cubre captura, inferencia, persistencia y replay HTTP; el snapshot original se conserva junto con su SHA-256.
- Conflictos de misma clave con otro contenido y cambios de snapshot producen 409; slots exitosos no se recalculan.

### 6.3 Estrato experimental v4

- Directorios de etapa contienen identidad de código/entorno, configuración, semillas, fingerprints, métricas, OOF/predicciones, decisiones y advertencias.
- Los contratos A→B→C cruzan identidades de productor y consumidor; admisibilidad rechaza desalineaciones. C incorpora ledger de holdout y verificación de recuperación.
- Los archivos de configuración congelada no equivalen a modelos serializados. La evidencia científica/resultados restringidos no fue abierta.

### 6.4 Estrato de replay

- Paquete científico de solo lectura con inventario y hashes de custodia.
- Feedback de demostración append-only JSONL en directorio aparte por sesión/package.
- La separación evita alterar paquete, predicciones archivadas o feedback operativo; no aporta por sí sola exclusión mutua entre escritores.

**Pruebas existentes no ejecutadas.** `tests/test_storage.py`, `tests/test_catalog.py`, `backend/tests/test_dependencies.py`, `backend/tests/test_producer_v2*.py`, `tests/test_controlled_daily_v4_{artifacts,provenance,code_identity,dataset_fingerprint,reproducibility_artifacts,holdout_ledger}.py` y replay package-loader/build.

**Documentación normativa/declarativa.** ADR-0002/0004/0008/0009/0011/0013, specs de data-ingestion, human-feedback, architecture-integration, experiment-runner y scientific-closure.

## 7. Recorrido E — feedback, recalibración y linaje

### 7.1 Feedback operativo legacy

**Entrada/consulta.** `GET /feedback/{sensor_id}`, `POST /feedback/{sensor_id}/{fecha}/confirm` y `/reject` en `backend/app/routers/feedback.py`.

**Vinculación y madurez.** La fila se vincula por sensor y `fecha` de emisión. `_require_mature_target` comprueba que exista la columna/campo `target_timestamp`, que `model_version` no sea nulo y que el valor comparable no sea futuro. No rechaza de forma explícita `target_timestamp=NaT`; ese caso queda para auditoría. Confirmar no crea etiqueta alternativa; rechazar puede registrar `etiqueta_corregida` y observación. `validated_at` es procedencia temporal para la etapa posterior.

**Distinción respecto de medición objetiva.** La observación humana se guarda como estado/etiqueta/nota sobre la predicción. La medición física continúa en el dataset y el target se deriva según contrato; no se fusionan como un único dato.

### 7.2 Recalibración

**Disparador real.** Solo `POST /recalibrate/{sensor_id}`; registrar o consultar feedback no reentrena automáticamente.

**Selección/aplicación.** `human_feedback.recalibration::recalibrate_predictor` toma únicamente filas rechazadas, con corrección no nula, validadas después de la maduración, target ya terminado, umbral/horizonte compatibles y procedencia de predictor coherente. Reaplica correcciones de ciclos anteriores; exige historial de features, ambas clases y al menos una corrección nueva. Clona/reajusta el estimador, asigna nuevo `model_id`, avanza `trained_through` y conserva `applied_feedback`.

**Linaje.** El router captura DataFrame y `dataset_sha256` desde los mismos bytes, y crea `RecalibrationLineage` con source/successor, referencias de feedback, timestamps, trained-through, fingerprint, SHA-256 y versiones de contrato/pipeline. `register_recalibrated_model` registra predictor y `recalibration_lineage.json` en MLflow. `GET /lineage/{sensor_id}` reconstruye la cadena y falla cerrado con 409 ante declaración parcial o inconsistente.

### 7.3 Feedback v2 y demo

Las reviews v2 se vinculan por `forecast_id`, tienen `request_id` idempotente y `expected_revision`, y se habilitan desde las 00:00 UTC de `target_date`. Una review registrada durante ese mismo día queda como `requires_mature_revalidation`; la elegibilidad para aprendizaje exige madurez posterior. Es una observación humana sobre la emisión, no una medición objetiva. No se encontró conexión automática desde esa elegibilidad hacia `recalibrate_predictor`; registrar la review no dispara recalibración.

El feedback de replay usa otra clase, otro archivo y `package_id`; no entra al registro legacy, al repositorio v2 ni a MLflow. Así se aísla la demostración de la mejora supervisada operativa.

**Pruebas existentes no ejecutadas.** `backend/tests/test_feedback.py`, `test_recalibration.py`, `test_lineage.py`, `test_models_active.py`, `test_producer_v2_forecasts.py`; `tests/test_feedback_schema.py`, `test_feedback_registry.py`, `test_recalibration.py`, `test_recalibration_lineage.py`, `test_model_registry.py`, `test_historical_replay_feedback.py`.

**Documentación normativa/declarativa.** `openspec/specs/human-feedback/spec.md`, `openspec/specs/alerting-ui/spec.md`, ADR-0006, ADR-0008, ADR-0009 y ADR-0013.

**Punto a verificar en auditoría.** Algunas descripciones históricas de human-feedback indicaron ausencia de endpoint de linaje, mientras el snapshot incluye `backend/app/routers/lineage.py` y el router está montado. Deben fecharse ambas fuentes y corregir solo la descripción vigente, si corresponde; no se clasifica aquí como defecto funcional.

## 8. Mapa de conexiones acreditadas

```mermaid
flowchart LR
  subgraph OP[Operativo]
    D1[Parquet por sensor] --> L[POST /forecast sensor run]
    L --> RF[Predictor recalibrado / cache / RF]
    RF --> FL[Feedback Parquet]
    FL --> RC[POST /recalibrate]
    RC --> MR[MLflow Model Registry + linaje]
    D1 --> V2[POST /api/v2/.../forecasts]
    BND[Bundles por sensor y horizonte] --> V2
    V2 --> OJ[JSON operacional + snapshot]
  end
  subgraph EX[Experimental v4]
    CSV[Datos autorizados] --> A[Stage A: LR/RF/HGB/Soft voting]
    A --> FC[Config/contrato congelado]
    FC --> B[Stage B]
    B --> C[Stage C + custodia]
  end
  subgraph HR[Histórico]
    PKG[Paquete autorizado archivado] --> LOAD[Validación de integridad/admisión]
    LOAD --> PROJ[Proyección por reloj simulado]
    PROJ --> RAPI[/replay API]
    RAPI --> RJ[Feedback demo JSONL aislado]
  end
```

No se dibuja conexión entre v4 y UI: no quedó acreditada. Tampoco se dibuja recalibración desde feedback de replay o desde reviews v2, porque no se identificó esa llamada real.

## 9. Dependencias externas

| Dependencia | Uso identificado | Condición no comprobada |
| --- | --- | --- |
| MLflow + Model Registry | Predictores legacy emitidos/recalibrados y linaje | Servicio, runs y modelos disponibles actualmente. |
| Postgres/MinIO (ADR-0004) | Backend/artifacts del tracking MLflow según arquitectura declarada | Despliegue actual no consultado. |
| Parquet local | Datasets y feedback legacy; snapshot v2 | Contenido de datos no inspeccionado. |
| JSON local + locks del SO | Catálogo y repositorio v2 | Comportamiento en filesystem/host productivo no ensayado. |
| Bundles operativos serializados | Inferencia v2 y calibración | Existencia, compatibilidad y contenido no cargados. |
| Paquete de replay | Proyección histórica | Contenido restringido no abierto; integridad no reejecutada. |
| scikit-learn/pandas/numpy | Features, modelos, inferencia y evaluación | Entorno/dependencias no ejecutados. |

## 10. Pull requests relevantes frente al snapshot

Consulta remota de solo lectura realizada el 2026-09-24:

| PR | Estado verificado | Relación con `f17fe658...` |
| --- | --- | --- |
| #207 | MERGED, merge `2079d03...`, 2026-09-21T19:57:48Z | Backend v2 + UI incorporados antes del snapshot. |
| #209 | MERGED, merge `3081a96...`, 2026-09-22T22:34:19Z | Hardening de paginación incorporado. |
| #210 | MERGED, merge `fb34686...`, 2026-09-22T22:34:17Z | Refresh de UI y hardening backend incorporados. |
| #214 | MERGED, merge `f17fe658...`, 2026-09-24T00:23:44Z | Reproducción histórica incorporada; coincide con el snapshot. |
| #215 | **OPEN**, head `feat/replay-ui-guided-experience`, commits `5ab46aa`, `cdbf71c` | Pendiente y solo UI según descripción/lista de archivos; no modifica backend/core replay del snapshot. |
| #188 | MERGED, merge `b8575f3`, 2026-09-09 | Implementación Stage A v4 disponible en main. |
| #194 | MERGED, merge `86d2b21`, 2026-09-16 | Implementación Stage C/custodia v4 disponible en main. |

Por lo tanto, no debe describirse #215 como incorporado ni inferirse que la experiencia guiada pertenece al backend relevado.

## 11. Puntos a verificar en la auditoría

1. Ejecutar, en entorno aislado y sobre SHA fijo, pruebas dirigidas de legacy, v2, replay, feedback/linaje y contratos v4; su mera existencia no prueba vigencia.
2. Verificar bundles operativos reales: identidad, calibrador, umbrales, compatibilidad y correspondencia con la metadata expuesta.
3. Comprobar una emisión v2 idempotente/concurrente y la preservación byte a byte del snapshot, sin tocar datos reales.
4. Revalidar integridad/admisión del paquete de replay sin inspeccionar resultados no autorizados y contrastar SHA/identidades declaradas.
5. Verificar que JSONL de replay no promete concurrencia: hoy no hay lock/test acreditado para dos escritores.
6. Reconciliar RH-02/03/05/06/08/13 con schemas/router, tareas y trazabilidad del replay.
7. Comprobar el caso legacy `target_timestamp=NaT` y actualizaciones Parquet concurrentes, sin asumir transacción/idempotencia.
8. Resolver la tensión split-before-impute de la spec frente al orden real del pipeline mediante fixtures temporales.
9. Aclarar documentación histórica de linaje frente al endpoint vigente.
10. Confirmar que no existe puente v4→bundle/UI antes de afirmar integración del ensamble.
11. Trazar cómo, o si, las reviews v2 llegan a una recalibración; no asumir equivalencia con feedback legacy.
12. Verificar en qué contexto/commit se produjeron las ejecuciones previas reportadas; no trasladar sus PASS al snapshot actual.

## 12. Limitaciones finales

- Inspección estática: no se ejecutó código ni se observaron servicios.
- No se abrieron resultados restringidos, holdouts ni contenidos de paquetes.
- No se cargaron bundles/modelos; su presencia y operabilidad quedan no comprobadas.
- Las cifras de pruebas previas son reportadas por documentos del 2026-09-23, no resultados de este paso.
- El árbol contenía ocho cambios ajenos bajo `replay_packages/`; fueron preservados y excluidos de la inspección.
- No se evalúa suficiencia científica, calidad estadística ni cierre del Trabajo Final.
- Este mapa no autoriza merge ni emite veredicto de backend cerrado.
