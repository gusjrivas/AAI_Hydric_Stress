# Spec: experiment-runner

> **Actualización normativa 2026-09-05:** rige el protocolo [controlled_daily_v3](../../../docs/research/protocolo-experimental-v3.md) y ADR-0009. Los ejemplos cuantitativos anteriores son históricos; no deben confundirse con la nueva evaluación de objetivos observados ni con inferencia futura.

Capacidad implementada (Épica 4, HU7 completa — diseño experimental, procedimiento automatizado con registro en MLflow, y ejecución real —, más los escenarios de escasez/ruido cerrados durante HU8). Orígenes: `openspec/changes/add-experiment-design/`, `openspec/changes/add-experiment-automation/`, `openspec/changes/add-experiment-execution/`, `openspec/changes/add-experiment-scenarios/`. Este documento es la fuente de verdad vigente de la capacidad; los *changes* que la originaron quedan como registro histórico de la decisión, no se actualizan en paralelo a este archivo.

## Protocolo formal vigente: controlled_daily_v3

El protocolo formal actualmente normativo es `controlled_daily_v3` (`docs/research/protocolo-experimental-v3.md`, ADR-0009), implementado por `src/experiment_runner/runner.py::run_configuration` y ejecutado por `scripts/run_hu7_experiments.py` (4 configuraciones de factores) y `scripts/run_hu7_scenarios.py` (4 escenarios de escasez/ruido).

- **Dataset formal:** `melchor_romero_2024_consolidado`, con SHA-256 `121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e`, embebido en el provenance de cada corrida.
- **Calendario:** diario, UTC sin zona horaria (`day_convention: UTC_naive_midnight`), sin huecos.
- **Target:** `soil_moisture(t+3 días) < umbral_congelado` (`target_rule: observed_value_at_t_plus_h_less_than_frozen_threshold`), calculado sobre la observación de referencia limpia, nunca sobre una versión perturbada por ruido o escasez.
- **Umbral:** percentil 20, ajustado sobre el entrenamiento limpio completo (`clean_train`, antes de aplicar cualquier perturbación experimental) y compartido entre condiciones pareadas.
- **Horizonte:** 3 días. **Features:** lags `[1,2,3]` y ventanas móviles `[3,7]` sobre `soil_moisture`, `solar_radiation`, `relative_humidity`.
- **Modelo:** Random Forest fijo (comparación pareada controlada, sin selección automática entre candidatos en estas configuraciones formales). **Umbral de alerta:** 0.5.
- **Semillas formales:** `[0, 1, 2, 3, 4]`, idénticas en las 8 configuraciones.
- **Experimento MLflow:** `hu7-controlled-daily-v3-formal`.
- **Artefactos formales vigentes (no modificar):** `docs/research/reference-v3-formal-results.json` y `docs/research/reference-v3-formal-table.md`, exportados por `scripts/export_hu7_reference.py`. Los artefactos `docs/research/reference-v3-results.json`, `reference-v3-table.md` y `reference-v3-source-manifest.json` son evidencia histórica/provisional anterior al cierre de este protocolo, con metadata de procedencia incompleta (ver `docs/research/protocolo-experimental-v3.md`); no deben usarse como fuente de verdad vigente.

**Semántica de las corridas registradas en MLflow:** son **8 configuraciones × 5 semillas = 40 *child runs* experimentales, anidados bajo 8 *parent runs* de agregación (uno por configuración) = 48 *runs* totales**. No debe describirse esto como "48 seeds" ni como "48 ejecuciones independientes equivalentes": las métricas por semilla viven en los *child runs*; las métricas agregadas (media/desvío) viven en los *parent runs*, y estos últimos no se incluyen como observaciones adicionales al calcular esa agregación.

**Rol del período de evaluación 2024:** constituye una **referencia de desarrollo experimental**, no una validación externa independiente sobre otro sitio o período — así lo declara explícitamente el protocolo formal (`protocolo-experimental-v3.md`, sección "Métricas y evidencia"). Esta limitación se preserva y no debe presentarse como generalización externa.

**Retroalimentación humana (HU5) dentro del plan experimental formal:** el mecanismo de recalibración madura de HU5 está implementado e integrado (ver `openspec/specs/human-feedback/spec.md`), pero la evaluación cuantitativa formal de su aporte al desempeño predictivo (comparar un modelo congelado contra un reentrenamiento sin correcciones y contra un reentrenamiento con correcciones, sobre los mismos datos) está **diseñada pero todavía no ejecutada** dentro de HU7 (`protocolo-experimental-v3.md`, sección "Próxima fase científica"; ADR-0009: *"HU7 «completa» sigue significando anomalías+sintéticos sobre modelado predictivo; no constituye evidencia experimental de mejora por retroalimentación humana"*). Esto no constituye un incumplimiento de los criterios de aceptación de HU7, pero es una limitación relevante para la contrastación de la hipótesis en HU8.

## Protocolo controlled_daily_v4_external_pergamino (Etapas A, B y C)

**Estado (actualizado 2026-09-15, PR de cierre de la Etapa C):** protocolo experimental adicional (`docs/research/controlled-daily-v4-external-pergamino-protocol.md`), formalmente distinto de `controlled_daily_v3` (dataset externo de Pergamino, no el dataset formal `melchor_romero_2024_consolidado`; ver también `docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md`). El detalle completo de sus requirements y escenarios vive en los *changes* que lo originaron, todavía sin archivar (`openspec/changes/add-controlled-daily-v4-external-pergamino/`, `openspec/changes/implement-controlled-daily-v4-stage-a/`, `openspec/changes/implement-controlled-daily-v4-stage-b-c/`); esta sección documenta únicamente su estado de implementación/integración/ejecución, sin duplicar ese contenido aquí.

- **Etapa A** (selección y congelamiento del candidato congelado, `src/experiment_runner/controlled_daily_v4/stage_a_runner.py`): **implementada e integrada** en `main`, verificada exclusivamente con pruebas sintéticas. Ninguna ejecución científica real se realizó todavía sobre los CSV de Pergamino.
- **Etapa B** (reentrenamiento del candidato congelado y compuerta temporal de validación sobre 2023, `src/experiment_runner/controlled_daily_v4/stage_b_runner.py`, más el contrato de transferencia A→B): **implementada e integrada** en `main` (PR #193).
- **Etapa C y su ledger de protección del holdout** (reentrenamiento con `target_timestamp <= 2023-12-31`, evaluación única sobre 2024-2025, `src/experiment_runner/controlled_daily_v4/stage_c_runner.py`; ledger transaccional SQLite, `src/experiment_runner/controlled_daily_v4/holdout_ledger.py`): **implementada y verificada sintéticamente** en el PR que originó este cierre; su **integración a `main`** queda **pendiente** mientras ese PR siga abierto. La inicialización explícita del ledger (`--init-holdout-ledger`), los tres estados del registro (`AUSENTE`/`CONFIRMADA`/`INDETERMINADA`), la secuencia de apertura con `fsync` explícito, y la recuperación de solo lectura de un resultado ya finalizado están todos implementados; ninguno se ejecutó todavía sobre un ledger científico real ni sobre el holdout real.
- **Ejecuciones científicas reales de A, B y/o C, y sus resultados cuantitativos** (sobre los CSV de Pergamino/Balcarce), y la **apertura real del holdout 2024-2025**: **pendientes** — ninguna se realizó todavía; esta sección no las anticipa ni las presenta como obtenidas. No existe ningún ledger científico real inicializado en este repositorio.

**Nota de resolución (2026-09-15):** hasta la actualización anterior de esta sección, la tarea de reflejar aquí la Etapa B quedaba deliberadamente sin marcar, señalando que la tarea equivalente de la Etapa A dejaba esa misma actualización pendiente de una ejecución científica real, y que actualizar solo B sin resolver A sería inconsistente con ese precedente. Encargo explícito (2026-09-15): documentar una capacidad ya implementada e integrada (A y, ahora, B) o implementada y verificada sintéticamente en un PR abierto (C) no depende de que exista una ejecución científica real — el mismo criterio ya usado en este documento para otras capacidades de HU7 (por ejemplo, la retroalimentación humana dentro del plan experimental formal, más arriba: "implementado e integrado", con su evaluación cuantitativa formal declarada aparte como diseñada pero no ejecutada). Esta nota se extiende ahora a C, sin reescribir ningún resultado histórico: las tablas y hallazgos cuantitativos de las secciones siguientes (`controlled_daily_v3`) no se modifican, y esta sección no afirma ninguna ejecución científica de A, B o C, ni apertura real del holdout, que no haya ocurrido.

## Requirements

### Requirement: Aumento sintético del conjunto de entrenamiento sobre variables ya construidas

El sistema DEBE poder generar filas sintéticas adicionales para el conjunto de entrenamiento muestreando conjuntamente las variables predictoras ya construidas (retardos, ventanas móviles) y la variable objetivo, sin requerir una fecha ni continuidad temporal real.

#### Scenario: Las filas sintéticas quedan marcadas y con etiqueta binaria válida

- **GIVEN** un conjunto de entrenamiento con variables predictoras ya construidas y su variable objetivo binaria
- **WHEN** se generan filas sintéticas adicionales a partir de ese conjunto
- **THEN** las filas resultantes quedan marcadas con procedencia `sintetico`, y su variable objetivo toma únicamente los valores 0 o 1

Implementado en `src/experiment_runner/synthetic_augmentation.py` (`add_synthetic_rows`), testeado en `tests/test_synthetic_augmentation.py`. Resuelve el bloqueo documentado en `openspec/specs/architecture-integration/spec.md` (HU6): a diferencia de `data_quality.synthetic_data.generate_synthetic` (que muestrea columnas físicas crudas y no puede usarse junto con las variables de retardo/ventana móvil sin inventar una fecha), esta función muestrea directamente sobre el espacio de variables ya construidas por `predictive_modeling.feature_engineering`, evitando el problema por completo.

Verificado sobre el dataset real (Melchor Romero 2024): partiendo de un conjunto de entrenamiento de 286 filas, se agregaron 100 filas sintéticas sin valores faltantes en las variables predictoras, con etiqueta binaria válida (0/1), y un modelo Random Forest reentrenado sobre el conjunto aumentado predijo sin error sobre las 71 filas del conjunto de evaluación.

### Requirement: Configuraciones comparativas de la Épica 4

El sistema DEBE poder identificar las 4 configuraciones experimentales resultantes de cruzar detección de anomalías (on/off) y aumento sintético (on/off): base, +sintéticos, +anomalías, completa.

#### Scenario: Las 4 configuraciones quedan documentadas con su combinación de factores

- **GIVEN** los dos factores de evaluación (detección de anomalías, aumento sintético)
- **WHEN** se documentan las configuraciones comparativas
- **THEN** existen exactamente 4 configuraciones, cada una con una combinación distinta de ambos factores

Documentado en `proposal.md`. Las 4 configuraciones originales (histórico, `pipeline_version` anterior a `controlled_daily_v3`):

| Configuración | Detección de anomalías | Aumento sintético |
|---|---|---|
| Base | No | No |
| +Sintéticos | No | Sí |
| +Anomalías | Sí | No |
| Completa | Sí | Sí |

**Actualización — 8 configuraciones formales bajo `controlled_daily_v3`:** el protocolo formal vigente (ver sección "Protocolo formal vigente" arriba) ejecuta estas 4 configuraciones de factores (renombradas en minúscula: `base`, `sinteticos`, `anomalias`, `completa`, `scripts/run_hu7_experiments.py::CONFIGURATIONS`) más 4 configuraciones de escenario (`coverage_fraction_0.5`, `recent_fraction_0.5`, `noise_both_0.3`, `noise_test_only_0.3`, `scripts/run_hu7_scenarios.py::SCENARIOS`), todas registradas en el mismo experimento formal (`hu7-controlled-daily-v3-formal`) con las mismas 5 semillas, el mismo dataset y el mismo modelo fijo:

| Configuración | Factor experimental | Train afectado | Test afectado | Target afectado | Propósito |
|---|---|---|---|---|---|
| `base` | ninguno | no | no | no | referencia de comparación |
| `sinteticos` | aumento sintético (solo train) | sí | no | no | ¿aportan datos sintéticos valor predictivo? |
| `anomalias` | detección de anomalías (fit train, apply train+test) | sí | sí | no | ¿aporta `is_anomaly` como predictor? |
| `completa` | anomalías + sintéticos | sí | sí | no | efecto combinado |
| `coverage_fraction_0.5` | escasez por cobertura estratificada (`scarcity_mode="coverage"`, `train_fraction=0.5`) | sí | no | no | disponibilidad limitada de ejemplos supervisados, preservando el calendario |
| `recent_fraction_0.5` | escasez por recencia (`scarcity_mode="recent"`, `train_fraction=0.5`) | sí | no | no | entrenamiento restringido a los datos más recientes |
| `noise_both_0.3` | ruido gaussiano (`noise_mode="both"`, `noise_std_ratio=0.3`) | sí | sí | no | robustez ante ruido de sensor en entrenamiento y despliegue |
| `noise_test_only_0.3` | ruido gaussiano (`noise_mode="test_only"`, `noise_std_ratio=0.3`) | no | sí | no | robustez ante degradación de calidad solo en despliegue |

En ninguna de las 8 configuraciones se perturba el target/ground truth: el umbral se calibra sobre entrenamiento limpio y el objetivo se calcula sobre la observación de referencia, no sobre la versión con ruido o con escasez aplicada (ver `run_configuration` en `src/experiment_runner/runner.py`).

## Diseño experimental

- **Preguntas experimentales**: ¿la detección de anomalías (HU3) mejora el desempeño del modelo predictivo (HU4) frente a la configuración base? ¿aportan los datos sintéticos (HU3) valor predictivo cuando se combinan con las variables de retardo/ventana móvil ya diseñadas (HU4)?
- **Escenarios de escasez y variabilidad**: escasez de datos se aproxima reduciendo el tamaño del conjunto de entrenamiento real (subconjunto de las filas más recientes antes del corte); variabilidad se aproxima ejecutando cada configuración con 5 semillas aleatorias distintas y reportando media/desvío de cada métrica entre corridas. No se inyecta ruido sintético artificial: no hay una caracterización real del ruido de sensor esperado más allá de los gaps ya observados y documentados en ESA CCI Soil Moisture (HU2).
- **Métricas y criterios de evaluación**: se reutilizan sin cambios las de `predictive_modeling.evaluation` (precisión, recall, F1 y ROC-AUC de la clase de estrés), más estabilidad (desvío entre repeticiones) y complejidad del modelo — mismos criterios ya usados para comparar los modelos candidatos en HU4.
- **Particiones, semillas y repeticiones**: partición temporal simple (`data_quality.splitting.temporal_train_test_split`, ya verificada sin fuga en HU3); 5 semillas aleatorias por configuración experimental.

### Requirement: Ejecución automatizada de una configuración experimental con múltiples semillas

El sistema DEBE poder ejecutar una configuración experimental (detección de anomalías y/o aumento sintético) sobre un dataset, repitiendo la ejecución con distintas semillas aleatorias, y devolver las métricas de desempeño de cada semilla.

#### Scenario: Una configuración con 3 semillas produce 3 filas de métricas

- **GIVEN** un dataset consolidado, una configuración experimental, y una lista de 3 semillas
- **WHEN** se ejecuta el procedimiento automatizado con esa configuración
- **THEN** el resultado tiene exactamente 3 filas, una por semilla, cada una con sus métricas de desempeño

Implementado en `src/experiment_runner/runner.py` (`run_configuration`), testeado en `tests/test_experiment_runner.py`. Ejecuta el orquestador de HU6 (`run_end_to_end_pipeline`) una vez por semilla, aplicando `add_synthetic_rows` cuando la configuración incluye aumento sintético. Verificado sobre el dataset real (configuración base, 3 semillas): F1 entre 0.400 y 0.500 según la semilla, ROC-AUC entre 0.533 y 0.558.

### Requirement: Registro de parámetros, versiones y resultados en MLflow

El sistema DEBE poder registrar en MLflow los resultados de una configuración ya ejecutada: un run padre con los parámetros de la configuración y las métricas agregadas, y un run hijo anidado por cada semilla con sus propios parámetros y métricas.

#### Scenario: Registro de una configuración con sus semillas como runs anidados

- **GIVEN** los resultados de una configuración experimental ejecutada con varias semillas
- **WHEN** se registran esos resultados en MLflow
- **THEN** se crea un run padre con las métricas agregadas de la configuración, y un run hijo por cada semilla anidado bajo ese run padre

Implementado en `src/experiment_runner/mlflow_logging.py` (`log_configuration_results`), testeado en `tests/test_mlflow_logging.py`. Se agregó `mlflow` como dependencia del proyecto (`mlflow>=2.14,<3`, mismo rango que el servidor de ADR-0004, para evitar incompatibilidades de API cliente/servidor). Verificado sobre los resultados reales de la configuración base (3 semillas): run padre con `f1_mean=0.449`, `f1_std=0.050` (y equivalentes para precisión/recall/ROC-AUC), y 3 runs hijos anidados recuperables por `tags.mlflow.parentRunId`.

### Requirement: Ejecución real de las 4 configuraciones contra el servidor MLflow

El sistema DEBE poder ejecutar las 4 configuraciones experimentales (base, +sintéticos, +anomalías, completa) con 5 semillas cada una sobre el dataset real, registrando los resultados en el servidor MLflow real (`http://localhost:5000`, ADR-0004).

#### Scenario: Las 4 configuraciones quedan registradas como runs padre distintos

- **GIVEN** el servidor MLflow real levantado (docker-compose) y el dataset consolidado real
- **WHEN** se ejecutan las 4 configuraciones experimentales con sus 5 semillas
- **THEN** el servidor MLflow tiene 4 runs padre distintos, cada uno con 5 runs hijos anidados

Ejecutado y registrado contra el servidor real (`http://localhost:5000`, Postgres + MinIO). Resultado real (dataset Melchor Romero 2024, modelo Random Forest, 5 semillas — `+Anomalías`/`Completa` usaron semillas `[0, 1, 2, 3, 4]`; la lista exacta de semillas de la ejecución original de `Base`/`+Sintéticos` no quedó registrada en el repositorio, ver `docs/research/hu8-analisis-resultados.md`):

| Configuración | F1 (media ± desvío) | ROC-AUC (media ± desvío) | Precisión (media) | Recall (media) |
|---|---|---|---|---|
| Base | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| +Sintéticos | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |
| +Anomalías | 0.4625 ± 0.0414 | 0.5881 ± 0.0309 | 0.6097 | 0.3730 |
| Completa | 0.3733 ± 0.1065 | 0.5297 ± 0.0629 | 0.5286 | 0.2973 |

**Hallazgo actualizado** (tras `openspec/changes/fix-anomaly-feature-integration/`): con `is_anomaly` ya incluida entre las variables predictoras, `+Anomalías` deja de ser idéntica a `Base` y `Completa` deja de ser idéntica a `+Sintéticos`. El efecto medido es positivo y modesto: frente a `Base`, `+Anomalías` mejora el ROC-AUC (0.5551 → 0.5881, fuera de una desviación estándar de `Base`) y la precisión (0.5967 → 0.6097), con un F1 prácticamente igual (0.4585 → 0.4625, dentro del ruido entre semillas) y un recall medio que coincide con el de `Base` a cuatro decimales (0.3730) — coincidencia de redondeo entre semillas individualmente distintas, no la identidad total en las 4 métricas que caracterizaba el defecto ya corregido. Frente a `+Sintéticos`, `Completa` mejora los cuatro indicadores (F1 0.3123 → 0.3733, ROC-AUC 0.5083 → 0.5297, precisión 0.5091 → 0.5286, recall 0.2324 → 0.2973). En ninguna de las dos comparaciones un indicador empeora. El aumento sintético por sí solo (`+Sintéticos` vs. `Base`) sigue empeorando el desempeño en este dataset (F1 0.312 vs. 0.459); ese hallazgo no cambia con este *change*, que solo corrige la integración de `is_anomaly`.

**Actualización (2026-09-04) — corrección de fuga temporal:** los valores de esta tabla quedaron obsoletos tras corregir una fuga temporal real en la imputación y en el cálculo del umbral de estrés (`openspec/specs/data-quality/spec.md` y `openspec/specs/predictive-modeling/spec.md`, ambos actualizados el mismo día; detalle completo en `docs/research/hu8-analisis-resultados.md`, sección 11). Re-ejecutado con el pipeline corregido, mismas semillas `[0,1,2,3,4]` para las 4 configuraciones (`scripts/run_hu7_experiments.py`), registrado en un experimento MLflow nuevo (`hu7-epica4-leakage-fix`) sin sobrescribir esta tabla ni el experimento histórico (`hu7-epica4`): `Base` F1=0.7354±0.0094/ROC-AUC=0.4664; `+Sintéticos` F1=0.7098±0.0379/ROC-AUC=0.4432; `+Anomalías` F1=0.7368±0.0123/ROC-AUC=0.4962; `Completa` F1=0.7075±0.0401/ROC-AUC=0.4544. El orden relativo entre configuraciones no cambia (anomalías sigue ayudando modestamente, sintéticos sigue perjudicando), pero el ROC-AUC de las 4 configuraciones cae a valores en o por debajo de 0.5 — el umbral de estrés corregido reveló que entrenamiento y evaluación tienen distribuciones de humedad de suelo distintas (evaluación es la época más seca del año), lo que el umbral anterior ocultaba parcialmente al calibrarse en parte con la propia evaluación. La lectura correcta ya no es "el modelo aporta poco pero algo aporta" sino "ninguna configuración discrimina mejor que el azar una vez eliminada la fuga" — ver `docs/research/hu8-resultados-discusion-conclusiones.md`, sección 6, para la re-lectura completa de las conclusiones de HU8.

**Actualización (2026-09-05) — purga de frontera de horizonte, consistencia del detector de anomalías y baselines/MCC:** una segunda auditoría corrigió una fuga residual (la etiqueta objetivo filtraba a las últimas filas de train una fecha ya perteneciente a evaluación, ver `openspec/specs/data-quality/spec.md`) y el ajuste del detector de anomalías sobre la propia distribución de evaluación en `run_quality_pipeline` (no afectaba a este *runner*, que ya usaba `architecture_integration.pipeline`, pero sí a la consistencia general del componente `data-quality`). Re-ejecutado (`scripts/run_hu7_experiments.py`, mismas semillas `[0,1,2,3,4]`), registrado en un experimento MLflow nuevo (`hu7-epica4-purged-cv`), sin sobrescribir `hu7-epica4-leakage-fix` ni `hu7-epica4`:

| Configuración | F1 (media ± desvío) | ROC-AUC (media) | MCC (media ± desvío) | Balanced accuracy (media) |
|---|---|---|---|---|
| Base | 0.7309 ± 0.0215 | 0.4447 | 0.0743 ± 0.0889 | 0.5323 |
| +Sintéticos | 0.6960 ± 0.0304 | 0.4105 | -0.0463 ± 0.0753 | 0.4808 |
| +Anomalías | 0.7278 ± 0.0190 | 0.4630 | 0.0571 ± 0.0583 | 0.5243 |
| Completa | 0.6949 ± 0.0404 | 0.4179 | -0.0235 ± 0.0881 | 0.4884 |

Baselines registrados junto a cada configuración (idénticos entre las 4, porque no dependen del modelo entrenado): persistencia F1=0.6087/MCC=-0.1113, clase mayoritaria F1=0.0/MCC=0.0 (predice siempre "no estrés" — confirma que la clase mayoritaria de entrenamiento ya no coincide con la de evaluación, mismo corrimiento estacional de la sección 11), siempre-estrés F1=0.7863/MCC=0.0.

**Hallazgo principal**: el orden `+Anomalías` (0.7368) > `Base` (0.7354) reportado en la corrección anterior **se invierte** (`Base` 0.7309/MCC 0.0743 > `+Anomalías` 0.7278/MCC 0.0571); un diagnóstico por semilla (`[+0.0122, +0.0158, -0.0396, +0.0210, -0.0250]`) confirma que es ruido, no un efecto real — la conclusión "anomalías ayuda modestamente" ya no se sostiene. El orden sintéticos/completa se mantiene (siguen perjudicando). Ver `docs/research/hu8-analisis-resultados.md`, sección 12, y `docs/research/hu8-resultados-discusion-conclusiones.md`, sección 7.

Además, esta ejecución centraliza como constantes nombradas (registradas como parámetros MLflow) el contrato de reproducibilidad completo: dataset, columnas de variables, columna objetivo, `horizon_days=3`, `percentile=20.0`, `lags=[1,2,3]`, `rolling_windows=[3,7]`, `alert_threshold=0.5`, `contamination=0.05`, modelo e hiperparámetros, semillas, `n_synthetic_samples=100`, y `pipeline_version="purged_cv_v2"` (`scripts/run_hu7_experiments.py`, `scripts/run_hu7_scenarios.py`, `src/experiment_runner/runner.py::run_configuration`).

**Nota de vigencia:** las tablas de esta sección (`hu7-epica4`, `hu7-epica4-leakage-fix`, `hu7-epica4-purged-cv`) documentan la evolución metodológica bajo `pipeline_version="purged_cv_v2"`, con 4 configuraciones y 20 corridas (4×5 semillas). El experimento formal vigente, ejecutado con `pipeline_version="controlled_daily_v3"` sobre las 8 configuraciones (ver "Protocolo formal vigente" al inicio de este documento), es posterior a estas correcciones y las incorpora todas (purga de frontera de horizonte, consistencia del detector de anomalías, baselines/MCC); sus resultados están en `docs/research/reference-v3-formal-results.json`/`reference-v3-formal-table.md`, no en las tablas de esta sección. Estas tablas se conservan como registro histórico de la evolución metodológica, no como evidencia formal vigente.

### Requirement: Reproducibilidad verificada entre corridas

El sistema DEBE producir métricas idénticas al re-ejecutar la misma configuración con las mismas semillas.

#### Scenario: Dos corridas de la misma configuración con las mismas semillas coinciden

- **GIVEN** una configuración experimental ya ejecutada con un conjunto de semillas
- **WHEN** se re-ejecuta esa misma configuración con las mismas semillas
- **THEN** las métricas de cada semilla son idénticas entre ambas corridas

Verificado re-ejecutando la configuración `base` con las mismas 5 semillas contra el dataset real: `pandas.testing.assert_frame_equal` confirmó que las métricas de ambas corridas son idénticas fila por fila, sin ninguna diferencia — el procedimiento es completamente determinista dadas las semillas.

### Requirement: Escenario de escasez de datos

El sistema DEBE poder simular escasez de datos conservando solo una fracción configurable del período de entrenamiento (las fechas más recientes antes del corte), sin alterar el período de evaluación.

#### Scenario: Reducir el entrenamiento a la mitad más reciente

- **GIVEN** un dataset con un período de entrenamiento y uno de evaluación ya definidos por una fecha de corte
- **WHEN** se aplica el escenario de escasez con una fracción de 0.5
- **THEN** el período de entrenamiento resultante contiene solo la mitad más reciente de las fechas de entrenamiento originales, y el período de evaluación no cambia

Implementado en `src/experiment_runner/scenarios.py` (`subsample_training_period`), integrado en `run_configuration` vía el parámetro `train_fraction`, testeado en `tests/test_scenarios.py` y `tests/test_experiment_runner.py`. Verificado sobre el dataset real (configuración base, `train_fraction=0.5`, 5 semillas): F1 medio **0.6219 ± 0.0888**, superior al F1 medio de la configuración base sin reducir (0.4585 ± 0.0423). Hallazgo real: reducir el entrenamiento a su mitad más reciente *mejoró* el desempeño en este dataset — explicación plausible: al conservar solo las fechas más cercanas al corte, el conjunto de entrenamiento queda estacionalmente más parecido al período de evaluación inmediatamente posterior, reduciendo el corrimiento de distribución (*distribution shift*) frente a usar todo el año.

**Actualización (2026-09-04):** re-ejecutado con el pipeline corregido de fuga temporal (`scripts/run_hu7_scenarios.py`): F1 medio **0.8430 ± 0.0139**, sigue superior a la base recalculada (0.7354 ± 0.0094) — misma dirección que antes de la corrección. Ver `docs/research/hu8-analisis-resultados.md`, sección 11.

**Actualización (2026-09-05) — MCC revierte esta conclusión:** re-ejecutado con la purga de frontera de horizonte (`scripts/run_hu7_scenarios.py`): F1 medio **0.8374 ± 0.0047** (consistente con el valor anterior), pero **MCC medio -0.1103** — el más negativo de todo el estudio, peor incluso que persistencia (-0.1113). El F1 alto ya no se puede leer como una mejora de desempeño: agregar MCC muestra que este escenario tiene la peor capacidad de discriminación real del estudio, no la mejor — el F1 alto se explica por un desbalance de clases agravado por tener menos datos de entrenamiento para corregir el corrimiento estacional (sección 11.1). **La conclusión "la escasez de datos mejora el desempeño" queda revertida.** Ver `docs/research/hu8-analisis-resultados.md`, sección 12.3.

**Nota de vigencia:** las cifras de este requirement corresponden a `pipeline_version="purged_cv_v2"` con `subsample_training_period`/recorte cronológico simple. El protocolo formal `controlled_daily_v3` distingue explícitamente dos mecanismos de escasez (`select_training_dates`, `scarcity_mode="coverage"` vs. `"recent"`, ver "Protocolo formal vigente" al inicio de este documento) y los ejecuta como `coverage_fraction_0.5`/`recent_fraction_0.5` en el experimento formal, cuyos resultados vigentes están en `docs/research/reference-v3-formal-table.md`.

### Requirement: Escenario de ruido de datos

El sistema DEBE poder simular ruido de sensor agregando ruido gaussiano de media cero a las variables predictoras, con desvío proporcional al desvío observado de cada variable.

#### Scenario: El ruido inyectado no altera la forma del dataset

- **GIVEN** un dataset con variables predictoras numéricas
- **WHEN** se inyecta ruido gaussiano con una proporción de desvío mayor a cero
- **THEN** el dataset resultante tiene la misma forma que el original, con los valores de las variables predictoras modificados

Implementado en `src/experiment_runner/scenarios.py` (`inject_gaussian_noise`), integrado en `run_configuration` vía el parámetro `noise_std_ratio` (semilla de ruido distinta por repetición), testeado en `tests/test_scenarios.py` y `tests/test_experiment_runner.py`. Verificado sobre el dataset real (configuración base, `noise_std_ratio=0.3`, 5 semillas): F1 medio **0.3188 ± 0.1130**, inferior al F1 medio de la configuración base sin ruido (0.4585 ± 0.0423) — el ruido inyectado degrada el desempeño, como se esperaba, y además aumenta notablemente la variabilidad entre semillas (desvío de F1 casi triplicado).

**Actualización (2026-09-04):** re-ejecutado con el pipeline corregido de fuga temporal (`scripts/run_hu7_scenarios.py`): F1 medio **0.6467 ± 0.0520**, sigue inferior a la base recalculada (0.7354 ± 0.0094) — misma dirección que antes de la corrección. Ver `docs/research/hu8-analisis-resultados.md`, sección 11.

**Actualización (2026-09-05):** re-ejecutado con la purga de frontera de horizonte (`scripts/run_hu7_scenarios.py`): F1 medio **0.6690 ± 0.0481**, MCC medio **0.0221** (positivo, sin la contradicción del escenario de escasez — ver requirement anterior). Misma dirección de degradación que antes de esta corrección.

**Nota de vigencia:** las cifras de este requirement corresponden a `pipeline_version="purged_cv_v2"`, con ruido aplicado únicamente a train+test (`both`). El protocolo formal `controlled_daily_v3` distingue explícitamente `noise_mode="both"` de `noise_mode="test_only"` (ver "Protocolo formal vigente" al inicio de este documento) y los ejecuta como `noise_both_0.3`/`noise_test_only_0.3` en el experimento formal, cuyos resultados vigentes están en `docs/research/reference-v3-formal-table.md`. En ambos casos, el ground truth observado nunca se perturba: solo las variables predictoras de entrada reciben ruido.

## Cierre científico v4: prerrequisitos de ejecución (HU7/HU8, 2026-09-20)

A/B/C están implementadas y verificadas **exclusivamente con pruebas sintéticas**; la ejecución científica sigue pendiente. La referencia vigente de diseño es `docs/research/scientific-closure-decisions.md`; las cifras y estados de secciones anteriores de esta spec conservan su carácter histórico. La existencia de estos mecanismos y de sus fixtures NO demuestra eficacia real de ningún candidato.

CRISP-DM: preparación, modelado y evaluación. No se modifica `controlled_daily_v3`, ni la arquitectura, hipótesis, frontend o contratos públicos. Los cuatro complementos (regresión, HITL, anomalías, robustez) tienen diseño predeclarado; implementar sus runners sigue pendiente y no bloquea técnicamente la Etapa A.

### Requirement: Contrato de features ejecutable y serializado

El runner DEBE exponer el contrato de features efectivo como dato serializable (`pergamino_features.v1`) y escribirlo en `resolved_config.json` de las Etapas A, B y C, y en el contrato congelado de transferencia de la Etapa A. El contrato v4 NO DEBE describirse como heredado de `controlled_daily_v3` sin modificación: son contratos distintos, y una diferencia de desempeño v3→v4 no identifica por sí sola un efecto de sitio, período o modelo.

#### Scenario: La Etapa B científica rechaza un contrato congelado divergente

- **GIVEN** una ejecución científica de la Etapa B y un contrato congelado cuyo `feature_contract` difiere del contrato ejecutable vigente
- **WHEN** se invoca la guarda de custodia de la Etapa B
- **THEN** la ejecución se rechaza antes de leer valores de entrada, entrenar o predecir, y el primer intento científico no se consume

### Requirement: Pisos de soporte predeclarados para selección y bootstrap

La selección DEBE exigir al menos **dos** folds con MCC definido de los tres previstos, y al menos el **80 %** de réplicas bootstrap válidas. Estos pisos son predeclarados y NO DEBEN relajarse para obtener un resultado favorable. Sin soporte de folds, la Etapa A DEBE terminar en `NO_VALID_SELECTION`, sin candidato transferible y conservando los diagnósticos de los folds ya evaluados. La compuerta de la Etapa C DEBE aplicar el mismo piso de réplicas válidas que el propio bootstrap.

#### Scenario: Soporte de réplicas insuficiente

- **GIVEN** un bootstrap pareado que produce menos del 80 % de réplicas válidas
- **WHEN** se evalúa la compuerta de la Etapa C sobre ese resultado
- **THEN** no se reporta intervalo, se conservan los diagnósticos con `replicas_valid`, `discarded_fraction` y `support_sufficient`, y la Etapa C no se admite

### Requirement: Métricas indefinidas y evaluaciones monoclase

El MCC DEBE ser indefinido cuando la verdad **o** la predicción es constante, y la exactitud balanceada DEBE ser indefinida con verdad monoclase. Toda métrica indefinida DEBE serializarse como `null` acompañada de estado, razón y soporte — nunca como `NaN` ni como un cero sustituto. Las evaluaciones monoclase de las Etapas B y C DEBEN conservar sus predicciones y las métricas que sí son definibles, y NO DEBEN registrar el resultado de un procedimiento que no se ejecutó. Una Etapa B monoclase NO DEBE abrir la Etapa C.

#### Scenario: Evaluación monoclase en la Etapa B

- **GIVEN** un período evaluable de la Etapa B con etiquetas monoclase y entrenamiento biclase
- **WHEN** se ejecuta la Etapa B
- **THEN** se persisten las predicciones y las métricas definibles, el bootstrap no se ejecuta ni se reporta como fallido, se registra la razón de la evaluación monoclase, y el veredicto no habilita la Etapa C

### Requirement: Métricas de inicio de episodio

El runner DEBE calcular métricas descriptivas de inicio de episodio sobre la fecha objetivo `t+3`, distinguiendo anticipación, detección en el día de inicio, detección tardía y omisión, y reportando días de anticipación, falsos avisos (días y rachas) y soporte. Los episodios cuyo inicio coincide con el comienzo de un segmento o con un hueco de calendario DEBEN censurarse por izquierda y NO DEBEN entrar en el denominador. Estas métricas NO DEBEN interpretarse como evidencia de eficacia operativa.

#### Scenario: Episodio censurado por izquierda

- **GIVEN** un episodio que comienza en la primera fila de un segmento o inmediatamente después de un hueco de calendario
- **WHEN** se calculan las métricas de inicio
- **THEN** el episodio se cuenta como censurado y se excluye del denominador de anticipación

### Requirement: Custodia del primer intento científico de la Etapa B

Una ejecución científica de la Etapa B DEBE reservar el intento en un registro persistente compartido **antes** de parsear, agregar o analizar los valores de entrada (el hash de los archivos sí se calcula antes, porque forma parte de la metadata de la reserva), dejando registrados candidato, commit, imagen inmutable, configuración, hashes de entradas y productor, y entorno, y DEBE finalizar la reserva autenticando los artefactos producidos por hash. Un segundo intento científico DEBE rechazarse. La recuperación DEBE ser de solo lectura, exigir una razón técnica explícita y verificar los hashes registrados, sin reentrenar, predecir ni cambiar el candidato. Un registro ausente o incompleto DEBE fallar cerrado.

#### Scenario: Segundo intento científico de la Etapa B

- **GIVEN** un intento ya reservado para la clave de la Etapa B
- **WHEN** se intenta una nueva ejecución científica de la Etapa B
- **THEN** el nuevo intento se rechaza y solo se admite recuperación explícita de solo lectura

### Requirement: Preflight de metadatos previo a la ejecución

El preflight DEBE validar que checkout, datos crudos, evidencia, ledger y backups son directorios disjuntos y preexistentes, que la identidad de código es limpia y conocida, y que la imagen se identifica por digest inmutable. El preflight NO DEBE leer valores de las entradas, calcular features, inicializar ningún ledger ni abrir ningún período reservado. Su resultado `PREPARED_NOT_AUTHORIZED` NO constituye autorización de ejecución.

#### Scenario: Preflight sobre rutas solapadas

- **GIVEN** una disposición en la que evidencia o ledger quedan dentro del checkout, o dos rutas se solapan
- **WHEN** se ejecuta el preflight
- **THEN** falla explícitamente y no escribe ningún artefacto


## Limitaciones conocidas

- ~~La detección de anomalías no afecta actualmente el desempeño del modelo...~~ **Actualización (2026-08-21):** resuelto en `openspec/changes/fix-anomaly-feature-integration/`. `is_anomaly` ahora es una variable predictora real (detector ajustado solo sobre `train`, aplicado sin reajustar sobre `test`); ver la tabla de resultados actualizada arriba.
- El aumento sintético sobre variables ya construidas empeoró el desempeño frente a la configuración base en este dataset — consistente con la limitación ya documentada de que el muestreo por normal multivariada no captura relaciones no lineales ni la estructura temporal real de las variables de retardo/ventana móvil.
- El aumento sintético es estadísticamente equivalente al de HU3 (normal multivariada); no fue validado con similitud estadística/utilidad predictiva formal como se hizo en HU3 para los datos sintéticos crudos.
- El escenario de ruido (`inject_gaussian_noise`) es una aproximación deliberadamente simple, no calibrada contra ninguna caracterización real de ruido de sensor — se eligió `noise_std_ratio=0.3` como un valor razonable de ejemplo, no como un valor validado empíricamente.
- Los resultados obtenidos bajo los escenarios de disponibilidad limitada son específicos del dataset utilizado, correspondiente a un único año y punto geográfico, y de las estrategias de reducción evaluadas (`coverage_fraction_0.5` y `recent_fraction_0.5`). Solo se evaluó una fracción de 0.5 para cada estrategia, por lo que estos resultados no permiten generalizar que una menor disponibilidad de datos mejore o deteriore sistemáticamente el desempeño predictivo.
- No se ejecutó un escenario combinado de escasez + ruido simultáneos.
- La evaluación cuantitativa formal del aporte de la retroalimentación humana (HU5) al desempeño predictivo permanece diseñada pero no ejecutada dentro de HU7 — ver "Protocolo formal vigente" al inicio de este documento.
- El período de evaluación 2024 usado por `controlled_daily_v3` es una referencia de desarrollo experimental, no una validación externa independiente sobre otro sitio o período.
