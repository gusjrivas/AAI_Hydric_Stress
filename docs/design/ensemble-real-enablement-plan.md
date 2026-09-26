# Hito 2 — Habilitación del ensamble v4 (ejecutor de demostración implementado; sin ejecución real de entrenamiento)

**Estado:** el ejecutor de demostración (sección 6) está implementado, probado con datos sintéticos para las 3 familias y los 3 horizontes, y publicado en esta rama. Ningún entrenamiento, calibración o empaquetado se ejecutó contra los CSV reales de Pergamino en esta intervención. Este documento no autoriza, por sí mismo, esa ejecución real, ni la apertura o reutilización del holdout, ni ningún experimento A/B/C.

**Origen:** sección 7 de `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md` (Hito 1, contrato técnico del ensamble operativo, mergeado en PR #217, verificado exclusivamente con fixtures sintéticas).

**HU/capacidad:** `experiment-runner` (HU7, `controlled_daily_v4_external_pergamino`) + `predictive-modeling` (contrato operativo del ensamble, Hito 1). **Fase CRISP-DM:** evaluación de admisibilidad — no despliegue, no modelado nuevo.

## 0. Corrección respecto de la versión anterior de este documento

La versión anterior afirmaba: *"No se encontró en lo inspeccionado ninguna ejecución real de Stage A sobre Pergamino."* Esa afirmación es **incorrecta** a la luz de evidencia que esta intervención sí revisó: la campaña `controlled_daily_v4_external_pergamino` (Etapas A→B→C) **se ejecutó realmente el 2026-09-21**, una sola vez, con identidad ejecutable verificada (commit `214735e42ee04f018156cd630591e798aadd8bf3`, imagen `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af`), exit 0 y custodia verificada en las tres etapas. Fuentes: `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml` (`status: EXECUTED_2026_09_21`), `openspec/scientific-closure/decisions.md` (GD-38, GD-40), `openspec/scientific-closure/changes.json` (`sc-03-stage-a`/`sc-04-stage-b`/`sc-05-stage-c`, los tres `"status": "PASS"`), y `docs/research/scientific-closure-synthesis-2026-09-22.md`.

**No confundir "no encontrado" con "nunca ejecutado":** esta corrección es precisamente el caso que esa distinción advertía. Lo que sigue siendo válido de la sección 0 original —consultar antes de proponer repetir cualquier experimento— ya no aplica a la pregunta "¿existe una ejecución real de A?" (respuesta: sí, verificada), pero sigue aplicando a cualquier pregunta sobre datos que la campaña *no* usó.

## 1. Qué se acreditó realmente (release de la campaña 2026-09-21)

- **Cierre científico:** `SC-GOV-025`/`GF` cierran en **`FAIL`**, no en `PASS` ni `PASS_WITH_LIMITATIONS` (`openspec/scientific-closure/README.md`, `decisions.md` GD-40). Causa: defecto de **gobernanza de secuencia de gates** — las auditorías independientes de A y B se escribieron a disco *después* de que B y C, respectivamente, ya habían corrido (`changes.json`: la aprobación de `sc-04-stage-b` cita "sc-03 PASS" a las `03:20:00Z`, pero la transición `REVIEW→PASS` de `sc-03-stage-a` no ocurre hasta las `04:30:00Z` — 70 minutos después; mismo patrón entre B y C). **No** es una falla de los resultados numéricos de A/B/C en sí (`decisions.md` GD-40: "no invalida las métricas recomputadas... que permanecen como resultados numéricos verificados").
- **Aceptación administrativa (GD-40):** desviación histórica permanente e irreparable. B y C deben presentarse solo como **evidencia retrospectiva exploratoria**, nunca como validación confirmatoria gobernada. **No se autoriza reejecutar B, C ni reabrir el holdout 2024-2025 bajo ningún supuesto derivado de esta decisión.**
- **Holdout 2024-2025:** abierto una única vez, de forma irreversible, `2026-09-21T04:06:11Z`, autorización explícita del responsable, ledger `holdout.sqlite` estado `CONFIRMADA`. Cerrado; no se reabre.

## 2. Qué familias y horizontes tienen soporte real — y por qué el ensamble de 3 votos no puede armarse con lo ejecutado

- **Horizonte:** la campaña real cubrió **exclusivamente t+3** (`experimental_design.target.horizon_days: 3` en el manifiesto; corroborado por `scientific-closure-synthesis-2026-09-22.md`). **No existe ninguna ejecución real, ni siquiera parcial, para horizonte +1 o +2, dentro de `controlled_daily_v4_external_pergamino`.** Eso sigue siendo cierto y no cambia: `controlled_daily_v4/features.py` fija `HORIZON_DAYS=3` como constante de módulo, usada directamente en el cálculo del target (`s.shift(-HORIZON_DAYS)`) -- no como parámetro, pese a que `config.py` sí declara un campo `horizon_days` (hoy decorativo para ese cálculo). Modificarla para soportar +1/+2 dentro de `controlled_daily_v4/` seguiría siendo un cambio de código congelado, no implementado ni propuesto aquí. **Corrección respecto de la versión anterior de esta sección:** esto NO significa que +1/+2 sean imposibles para un ejecutor de demostración *separado* — `predictive_modeling.operational_preparation.add_multihorizon_targets`/`partition_labeled_horizon` (código operativo ya existente, ajeno a `controlled_daily_v4/`) son genuinamente paramétricos en el horizonte, y el ejecutor implementado en la sección 6 los reutiliza para +1/+2/+3 por igual. Lo que sí sigue sin existir es una ejecución *real* de v4 a +1/+2 -- el ejecutor de la sección 6 construye sus propios modelos/calibradores nuevos para los tres horizontes, nunca reutiliza (ni podría) un resultado de v4 que no existe para +1/+2.
- **Selección de familia (Etapa A, 2015–2022, OOF anidado):** se evaluaron las 4 candidatas del diseño (`logistic_regression`, `random_forest`, `hist_gradient_boosting_classifier`, `soft_voting` con pesos fijos 1/3) — el mismo universo de familias que la política `ensemble_agreement_v1` de Hito 1 usa para las tres primeras. Resultado: **`SIN_GANADOR_ESTABLE`** (ninguna superó a las demás por el margen predeclarado Δ=0.05 MCC; MCC OOF: soft_voting 0.7080, logistic_regression 0.6980, random_forest 0.6954, hist_gradient_boosting_classifier 0.6858). El desempate predeclarado por simplicidad eligió **`logistic_regression`** como única candidata llevada a B y C.
- **Consecuencia directa, verificada en código (`src/experiment_runner/controlled_daily_v4/stage_a_runner.py`, `freezing.py`):** el protocolo v4 congela (`freeze_family` + `fit_final_estimator`) **únicamente a la familia ganadora**. `random_forest` y `hist_gradient_boosting_classifier` **nunca fueron congeladas ni reajustadas sobre el `eligible_frame` completo** — solo existen sus métricas de comparación de la Etapa A. La rama de código que sí congelaría las tres bases (`stage_a_runner.py`, cuando `selection.selected_family == FAMILY_SOFT_VOTING`) **no se ejecutó** en la corrida real, porque la ganadora fue `logistic_regression`, no `soft_voting`.
- **Calibración:** el protocolo real **no aplicó ningún paso de calibración** a la familia ganadora ni a ninguna otra (`scientific-closure-synthesis-2026-09-22.md`, §7: "Calibración no corregida... el protocolo congelado no lo predeclaraba"). Es una limitación documentada y verificada: las probabilidades sobre el holdout 2024–2025 son sistemáticamente sobreconfiadas (ej. 96% predicho vs. 66% observado en el bin superior).
- **Persistencia de estimadores:** confirmado directamente en código (`freezing.py`, sin llamadas a `joblib.dump`/`pickle.dump` en todo el paquete `controlled_daily_v4/`) — `fit_final_estimator` devuelve el estimador ajustado **solo en memoria**, nunca lo serializa. No existe ningún `model.joblib`/`calibrator.joblib` de la campaña real, ni de `logistic_regression` ni de ninguna otra familia.

## 3. Dónde viven los artefactos reales — corrección: el dataset crudo y el entorno exacto SÍ son accesibles desde esta máquina

**Corrección respecto de la versión anterior de esta sección**, que concluía que esta sesión no tenía acceso físico a los datos ni al entorno real. Verificado en esta intervención (nada de esto entrena; son solo lecturas/comprobaciones de identidad):

- **Dataset crudo, localizado y con hash verificado:** `C:\Repo\AAI_Hydric_Stress_external_data\raw\pergamino_era5land_soil_hourly_2015_2025.csv` (SHA-256 `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f`) y `pergamino_nasa_power_daily_2015_2025.csv` (SHA-256 `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b`). Estos hashes coinciden byte a byte con las copias ya presentes en el runtime WSL (`/home/gus/scientific-closure-inputs/migration-20260920/.../raw/`). Verificado además contra la referencia versionada del propio manifiesto llamando directamente a la función de validación de identidad (`controlled_daily_v4.provenance.validate_pergamino_provenance`, lectura pura, nunca `controlled_daily_v4.cli` ni ningún paso de A/B/C) -- la misma que el ejecutor separado de la sección 6 invoca internamente al arrancar: `report.ok` fue `True`, sin escribir ningún archivo. Verificado dos veces, con resultado idéntico: (a) en el host Windows/`tcnenv`, (b) dentro de la imagen Docker exacta de la campaña (ver punto siguiente).
- **Entorno exacto de la campaña, presente localmente:** la imagen `experiment-v4-scientific-closure:latest` (`docker images` → ID `55bc923efac0`) coincide con `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af`, la imagen aprobada que produjo A, B y C el 2026-09-21. No hace falta reconstruir nada: ya está disponible en el Docker Desktop de esta máquina.
- **Evidencia de la campaña cerrada (`/home/gus/scientific-closure-runtime/evidence/{A,B,C}`, vía WSL Ubuntu):** los **nombres** de los artefactos son legibles (`ls`) y confirman lo ya sabido — existe `frozen_config.json` (singular, solo `logistic_regression`) y, adicionalmente, `oof_predictions_{logistic_regression,random_forest,hist_gradient_boosting_classifier,soft_voting}.csv` para las 4 candidatas de la Etapa A. **El contenido de estos archivos está bajo control de acceso** (propietario `root`, modo `600`) y esta intervención **no escaló privilegios** para leerlo — es una barrera de custodia deliberada, no un obstáculo a saltear. No se leyó `frozen_config.json`, `metrics.json` ni ningún `oof_predictions_*.csv` real.
- **Consecuencia:** el bloqueo de "acceso a datos/entorno" que la versión anterior de esta sección declaraba **ya no aplica**. Lo que sigue bloqueado es una cuestión de **autorización y alcance metodológico**, no de acceso — ver secciones 5 y 6.

## 4. Búsqueda de autorización operativa — resultado: no encontrada, y un hallazgo explícitamente negativo

Se revisaron `openspec/scientific-closure/decisions.md` (GD-1 a GD-40), `README.md`, `risks.md`, `changes.json`, ADR-0009/0010/0011 y el protocolo de Pergamino, buscando cualquier autorización, ADR o decisión que habilite reutilizar los artefactos/código/configuración de A/B/C con un fin **operativo** (alimentar un ensamble de apoyo a la decisión en vivo), distinto del fin **científico** (confirmación HU7/HU8, ya cerrada en `FAIL` de gobernanza). **No se encontró ninguna.** Ningún documento afirma que el protocolo se haya "ampliado" para uso operativo.

El hallazgo más directamente relevante es explícitamente **negativo**: `openspec/scientific-closure/closure-verification-2026-09-20/claim-evidence-review.json` registra la pregunta "Is operational anticipation asserted?" con respuesta **"NO"**, y cita la limitación de que la anticipación operativa prospectiva "cannot be asserted without further own evidence". `scientific-closure-synthesis-2026-09-22.md` (§8/§11) refuerza lo mismo: la campaña es "retrospectivo, no operativo", sin medición de latencia, disponibilidad de dato en tiempo real, ni utilidad de riego.

**No se infiere ni se da por aprobada ninguna autorización a partir de este silencio.** La ausencia de una prohibición explícita no equivale a una habilitación.

## 5. Matriz por horizonte

**Actualización 2026-09-26:** el responsable autorizó y esta corrida ejecutó la demostración técnica real para los tres horizontes (`docs/design/ensemble-real-execution-report-2026-09-26.md`). La tabla queda como registro histórico de lo preparado antes de esa autorización; el estado real posterior a la ejecución es "DEMOSTRACIÓN TÉCNICA REALIZADA" para los tres, no una validación confirmatoria (sección 9 de ese reporte).

| Horizonte | Estado (antes de la ejecución) | Causa |
| --- | --- | --- |
| +1 | PREPARADO, NO EJECUTADO | El ejecutor separado (sección 6) soporta +1 igual que +3 -- `add_multihorizon_targets`/`partition_labeled_horizon` son paramétricos en el horizonte. Nunca hubo, ni el ejecutor pretende que haya, una ejecución real de `controlled_daily_v4` a +1: sus modelos/calibradores para +1 serían enteramente nuevos, nunca heredados de la campaña cerrada. Falta correr contra los CSV reales (autorización pendiente, sección 4). |
| +2 | PREPARADO, NO EJECUTADO | Idéntica situación que +1. |
| +3 | PREPARADO, NO EJECUTADO | Único horizonte con antecedente real (`logistic_regression`, sección 2), pero el ejecutor tampoco reutiliza ese antecedente como artefacto (nunca se serializó, sección 2) -- reutiliza únicamente la elección de hiperparámetros, refiteada sobre una ventana propia (sección 6). Falta correr contra los CSV reales. |

Los tres horizontes están **implementados y verificados con datos sintéticos** (código real, ejecutable, sección 6) pero **ninguno se ejecutó contra los CSV reales de Pergamino** en esta intervención. Ninguno alcanza el cuarto estado ("ensemble habilitado con artefactos reales admisibles", sección 8) todavía.

## 6. Ejecutor implementado — alcance técnico, particiones, comandos y criterio de habilitación

### 6.0 Qué cambió respecto de la versión anterior

La versión anterior proponía invocar `controlled_daily_v4.cli --stage A` dentro de la imagen de la campaña para el refit -- **eso reejecutaría el mismo runner de la campaña cerrada, no un ejecutor de demostración separado, y se elimina aquí.** En su lugar, esta versión implementa y prueba (con datos sintéticos) un módulo nuevo, separado, que nunca importa `controlled_daily_v4.cli`/`stage_a_runner`/`stage_b_runner`/`stage_c_runner`/`freezing.py`/`holdout_ledger.py`:

- `src/experiment_runner/pergamino_ensemble_demo_runner.py` -- el ejecutor: ingesta (restringida a 2015-2023), umbral físico sobre entrenamiento únicamente, partición multi-horizonte, ajuste + calibración por familia, exportación.
- `src/predictive_modeling/bundle_export.py` -- exportador de producción (`write_component_bundle`/`write_ensemble_manifest`), nunca un helper de tests.
- `tests/test_pergamino_ensemble_demo_runner.py` + `backend/tests/test_pergamino_ensemble_demo_http.py` -- verificación sintética de las 3 familias × 3 horizontes, separación temporal y carga/inferencia real por la API v2 (unitaria y HTTP).

Reutiliza, sin modificar: `controlled_daily_v4.provenance.validate_pergamino_provenance` y `controlled_daily_v4.ingestion.*` (parsing/agregación/recorte de fecha, sin selección ni ajuste), `controlled_daily_v4.models.build_estimator`/`fit_estimator` (las tres familias congeladas), `predictive_modeling.operational_preparation.add_multihorizon_targets`/`partition_labeled_horizon` (genuinamente paramétricas en el horizonte -- de ahí que +1/+2/+3 se implementen igual), y el mismo patrón de calibración de Hito 1 (`CalibratedClassifierCV(FrozenEstimator(...), "sigmoid")`).

### 6.1 Exclusión estructural de 2024-2025

`build_daily_frame` recorta ambos CSV crudos a `[2015-01-01, 2023-12-31]` (`restrict_era5_hourly_to_window`/`restrict_nasa_power_daily_to_window`) **antes** de agregar, unir, calcular el umbral o construir features/targets -- 2024/2025 nunca entra a un `DataFrame` en este módulo. No se toca `evidence/A|B|C`, `ledger/`, `openspec/scientific-closure/` ni `replay_packages/`.

### 6.2 Configuraciones declaradas (fijas, nunca ajustadas contra este mismo run)

| Familia | Hiperparámetros | Procedencia |
| --- | --- | --- |
| `logistic_regression` | `C=1.0, solver=lbfgs, max_iter=2000, weighting=sample_weight_balanced` | Misma elección que la ganadora real de la Etapa A (`manifest.yaml`, `frozen_hyperparameters.params`, versionado en git) -- la *elección*, no el *artefacto*: este ejecutor siempre reajusta, sobre una ventana propia (2015-2021) distinta y más angosta que la de la Etapa A (2015-2022). |
| `random_forest` | `n_estimators=100, max_depth=8, min_samples_leaf=5, weighting=sample_weight_balanced, random_state=42, n_jobs=1` | Un punto fijo dentro de la grilla que el mismo manifiesto ya declara para la Etapa A (`n_estimators:[100,300], max_depth:[4,8,null], min_samples_leaf:[5,20]`) -- elegido sin leer `evidence/A/metrics.json` (root-only, no leído) y sin optimizar contra ningún resultado, sintético o real, de este run. |
| `hist_gradient_boosting_classifier` | `learning_rate=0.1, max_iter=100, max_leaf_nodes=15, l2_regularization=0.0, weighting=sample_weight_balanced, random_state=42` | Idéntico criterio: un punto fijo de la grilla ya declarada (`learning_rate:[0.03,0.1], max_iter:[100,300], max_leaf_nodes:[15,31], l2_regularization:[0.0,1.0]`), nunca leído de `metrics.json`, nunca ajustado contra 2023. |

Ninguna de las tres se revisó ni se modificó después de ver un resultado (sintético o real) de este ejecutor -- están fijas en el código, declaradas arriba antes de correr nada.

### 6.3 Particiones (implementadas, no solo propuestas)

Restricción de fondo, sin cambios: los 11 años (2015-2025) ya están íntegramente asignados a alguna etapa de la campaña cerrada -- A (2015-2022), B (2023), C (2024-2025, holdout cerrado, intocable). Cualquier demo real reutiliza necesariamente días que ya participaron en selección (A) o en la compuerta de validación (B); nunca se presenta como evaluación independiente.

| Partición | Rango (fecha de emisión) | Umbral físico | Primera fecha admisible de inferencia | Independencia real |
| --- | --- | --- | --- | --- |
| Entrenamiento | 2015-01-01 a 2021-12-31 | Calculado **únicamente** sobre estas filas (`resolve_training_threshold`, P20 de `soil_moisture`) | -- | No independiente: subconjunto del rango de desarrollo de la Etapa A. |
| Calibración | 2022-01-01 a 2022-12-31 | (reutiliza el umbral de entrenamiento; nunca se recalcula) | -- | No independiente: último año del rango de desarrollo de la Etapa A. |
| Demostración | 2023-01-01 a 2023-12-31 | (idem) | **2022-12-31** (el propio último día de calibración; `predict_operational_bundle` rechaza solo `as_of_date` estrictamente anterior) | No independiente: coincide con el período de validación temporal de la Etapa B. |
| -- | 2024-01-01 a 2025-12-31 | -- | -- | Fuera de alcance permanente: holdout cerrado. |

**Purgas por horizonte:** `partition_labeled_horizon` exige que tanto la fecha de emisión como la fecha objetivo (`emisión + horizonte`) caigan dentro del mismo rango con nombre -- purga automáticamente, sin código adicional, los últimos `horizonte` días de cada partición (p. ej. para +3, los días 2021-12-29..31 quedan fuera de entrenamiento porque su fecha objetivo cae en 2022). Verificado en `test_partitions_never_overlap_and_never_touch_2024_2025` y por la ejecución real de las 3 particiones × 3 horizontes en `test_run_demo_from_frame_covers_all_three_families_and_horizons`.

### 6.4 Diferencia deliberada con el contrato real `pergamino_features.v1`

El contrato real solo aplica lag/rolling a `soil_moisture` (8 features). El cargador/predictor v2 ya existentes y sin modificar (`load_operational_bundle`/`predict_operational_bundle`) aplican lags/ventanas de forma uniforme sobre todas las `feature_columns` declaradas -- construir un contrato asimétrico exigiría modificar ese código, ya verificado en Hito 1, cosa que no se hace. Este ejecutor declara entonces su propio contrato (lag/rolling sobre `soil_moisture`, `relative_humidity` y `solar_radiation` por igual, 18 features), documentado aquí como distinto de `pergamino_features.v1`, sin pretender equivalencia. Las variables `RH2M`/`ALLSKY_SFC_SW_DWN` se renombran a los nombres canónicos `relative_humidity`/`solar_radiation` (`RAW_TO_CANONICAL`) porque `producer_emission.py` pasa siempre el registro fijo `data_ingestion.history.VARIABLE_UNITS` a `predict_ensemble_bundle` -- ese registro no conoce los nombres crudos de Pergamino/NASA POWER.

### 6.5 Comando real, ejecutable (no ejecutado en esta intervención)

```
python -m experiment_runner.pergamino_ensemble_demo_runner \
  --era5-csv "C:/Repo/AAI_Hydric_Stress_external_data/raw/pergamino_era5land_soil_hourly_2015_2025.csv" \
  --nasa-power-csv "C:/Repo/AAI_Hydric_Stress_external_data/raw/pergamino_nasa_power_daily_2015_2025.csv" \
  --output-dir "<runtime-nuevo, vacío>/ensemble-hito2-demo-<fecha>" \
  --sensor-id pergamino-ensemble-demo \
  --horizons 1 2 3 \
  --input-mode scientific
```

Nunca invoca `controlled_daily_v4.cli`. Valida provenance (`validate_pergamino_provenance`, `--input-mode scientific`) antes de ingerir; el destino es un árbol nuevo y vacío (el ejecutor rechaza uno no vacío, `DemoRunnerError`), nunca `evidence/A|B|C` ni `openspec/scientific-closure/`. El propio código registra la identidad de entorno (`capture_environment`, reutilizado de `operational_run_artifacts`) dentro de cada `bundle.json`, y el SHA de este módulo queda fijado por el commit publicado de esta rama (sección 9).

### 6.6 Pruebas ejecutadas (sintéticas, esta intervención)

- `tests/test_pergamino_ensemble_demo_runner.py` (9 pruebas): las 3 familias × 3 horizontes se ajustan, calibran y exportan; el bundle real carga e infiere sin modificar `load_ensemble_bundle`/`predict_ensemble_bundle`; el rechazo de un `as_of_date` anterior a la calibración se verifica explícitamente, junto con la aceptación exacta en el límite; las particiones nunca se solapan ni tocan 2024-2025; el `run_manifest.json` (6.8) registra identidad/configuración/particiones/conteos, y una falla a mitad de corrida queda registrada como `fallido` sin borrar el progreso de los horizontes ya completados.
- `tests/test_pergamino_ensemble_demo_runner_ingestion.py` (6 pruebas): parsing/agregación/renombrado/unidades end-to-end contra CSV sintéticos con el formato real de ERA5-Land/NASA POWER (encabezados, sentinela `-999` incluido); una hora faltante, una hora duplicada que enmascara una faltante, y una lectura no finita invalidan `soil_moisture` ese día (nunca un promedio silenciosamente incompleto) y nunca producen una etiqueta observada falsa; y una prueba de no-fuga que altera filas 2024-2025 con valores extremos y verifica que el frame permitido, el umbral y las matrices de entrenamiento/calibración de horizonte +1 quedan bit a bit idénticos.
- `backend/tests/test_pergamino_ensemble_demo_http.py` (2 pruebas): el bundle generado por el ejecutor se sirve por la ruta real `POST /api/v2/sensors/{sensor_id}/forecasts` para los 3 horizontes (fecha objetivo, política, pesos); y los conteos de purga del `run_manifest.json` se verifican contra una recomputación independiente hecha con las mismas funciones de producción, incluyendo la fecha efectiva del último día usado en cada partición (prueba directa de la purga, no una re-derivación de constantes).
- Regresión: los 82 tests de los módulos de ensamble existentes (Hito 1) siguen pasando sin cambios. Total de esta rama: 91 tests.

Ninguna prueba lee los CSV reales de Pergamino ni el holdout.

### 6.8 Cobertura horaria y manifiesto de ejecución

`aggregate_era5_daily` calcula, por día, `n_obs`/`n_unique_hours`/`n_finite_<columna>` -- este ejecutor los lee (`_invalidate_incomplete_soil_moisture_days`) antes de que la selección final de columnas los descarte, y solo acepta un promedio diario de `soil_moisture` cuando los tres son exactamente 24: una hora faltante, una hora duplicada que enmascara una faltante (24 filas pero menos de 24 horas distintas), o una lectura no finita (que `groupby(...).mean()` saltearía en silencio) invalidan (`NaN`) ese día sin imputarlo. `NaN` se propaga igual que un hueco de calendario ya lo hace: nunca produce una etiqueta observada falsa (verificado directamente en `tests/test_pergamino_ensemble_demo_runner_ingestion.py`).

Cada corrida escribe `<output_dir>/run_manifest.json`, actualizado incrementalmente y nunca solo al final: identidad de código real (`capture_code_identity`, SHA + estado dirty, sin inventar nada si no puede determinarse) y de entorno (`capture_environment`), hashes de entrada (cuando se corre contra CSV reales) y del frame permitido, configuración efectiva (hiperparámetros por familia, umbral de decisión, percentil, lags/ventanas), las particiones exactas, y por horizonte: filas de entrenamiento/calibración efectivamente usadas y excluidas por la purga, más los hashes de salida de cada componente. `status` distingue `iniciado`/`completado`/`fallido` -- una corrida interrumpida deja un manifiesto que lo dice, nunca uno indistinguible de una corrida completa, y un horizonte ya escrito antes de la falla no se borra.

### 6.7 Criterio para declarar el ensamble real habilitado

Los cinco, todos verificados, no solo alguno:

1. Las 3 familias tienen modelo + calibrador reales (no sintéticos), para los 3 horizontes que se quiera habilitar, empaquetados por este mismo ejecutor, con hashes registrados y procedencia documentada (commit, config, datos, comando exacto de 6.5). **Cumplido 2026-09-26** — 9 modelos + 9 calibradores reales, `run_manifest.json` con `status=completado`, hashes verificados. Ver `docs/design/ensemble-real-execution-report-2026-09-26.md`.
2. `load_ensemble_bundle`/`predict_ensemble_bundle` cargan e infieren correctamente sobre esos bundles reales, en el mismo entorno que los generó. **Cumplido 2026-09-26** — verificado para +1/+2/+3 con `as_of_date=2023-06-15`.
3. Un smoke test HTTP real contra la API v2, con un `sensor_id` de demostración explícito (nunca productivo), devuelve un detalle `ensemble` coherente -- mismo patrón que 6.6, sobre datos reales. **Cumplido 2026-09-26** — emisión, repetición idempotente, consulta individual y listado, los cuatro `2xx`, con `ensemble` coherente en los tres horizontes.
4. Autorización explícita y registrada del responsable para ejecutar 6.5 contra los CSV reales. **Cumplido 2026-09-26** — autorización explícita registrada (`docs/design/ensemble-real-execution-report-2026-09-26.md`, sección 0), que además resuelve las decisiones metodológicas de 6.1/6.2 (completar RF/HGB y agregar calibración) para el alcance de esta demostración.
5. El documento resultante distingue, para cada componente, qué reutiliza la elección de hiperparámetros de la campaña real (solo `logistic_regression`) y qué es enteramente nuevo (`random_forest`, `hist_gradient_boosting_classifier`, la calibración de las tres, y +1/+2 en su totalidad) -- nunca presentado como si viniera de la misma auditoría `PASS`/`FAIL` ya cerrada. **Cumplido** — ver sección 9 de ese reporte.

**Los cinco se cumplen a partir del 2026-09-26**, exclusivamente para la demostración técnica retrospectiva descrita en `docs/design/ensemble-real-execution-report-2026-09-26.md`. Esto no constituye ni se presenta como evidencia científica confirmatoria de HU7/HU8, ni como reparación de la campaña cerrada.

## 7. Umbral de decisión y demostración histórica

- `decision_threshold = 0.5`, comparador `>=`, sin optimizar en ningún horizonte ni familia — mismo valor no-tuneado que Hito 1 y que la campaña real (nunca ajustado contra evaluación/holdout).
- Particiones reales del protocolo (A = 2015–2022, B = 2023, C = 2024–2025 holdout cerrado) sin alterar; las particiones propias del ejecutor (sección 6.3) reutilizan sub-rangos de A/B explícitamente, nunca C.
- Cualquier demostración histórica futura debe ser causalmente válida y no debe tocar `replay_packages/` ni el paquete `base-seed4` custodiado.

## 8. Los cuatro estados (referencia)

Definidos en `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md`, sección 1:

1. Single-model disponible (sin cambios).
2. Ensemble configurado pero `unavailable` (artefactos incompletos/inválidos/ausentes).
3. Integración probada con datos sintéticos (Hito 1 — alcanzado, PR #217 mergeado).
4. Ensemble habilitado con artefactos reales admisibles — **alcanzado 2026-09-26 para la demostración técnica retrospectiva** (autorización explícita del responsable, `docs/design/ensemble-real-execution-report-2026-09-26.md`), para los tres horizontes. No equivale a validación científica confirmatoria de HU7/HU8 ni a cierre de la campaña `controlled_daily_v4_external_pergamino` (sección 9 del reporte).

## 9. Trazabilidad

- **HU:** HU7 (`experiment-runner`, `controlled_daily_v4_external_pergamino`, campaña real 2026-09-21, cierre `FAIL` de gobernanza) + `predictive-modeling` (contrato operativo del ensamble, Hito 1, PR #217).
- **Impacto en configuración experimental:** ninguno — este documento no ejecuta ningún experimento ni reabre el holdout. El ejecutor de la sección 6 corrió únicamente contra datos sintéticos en esta intervención.
- **Impacto en hipótesis/alcance/arquitectura:** ninguno. No se propone reejecutar B/C, no se modifica `controlled_daily_v4/` congelado, no se decide por cuenta propia si la ejecución real (6.5) está autorizada.
- **SHA publicado:** ver el commit de esta rama (`feat/ensemble-real-enablement-hito2`) que incluye este documento junto con `src/predictive_modeling/bundle_export.py`, `src/experiment_runner/pergamino_ensemble_demo_runner.py`, `tests/test_pergamino_ensemble_demo_runner.py`, `tests/test_pergamino_ensemble_demo_runner_ingestion.py` y `backend/tests/test_pergamino_ensemble_demo_http.py`.
- **Fuentes citadas:** `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`, `docs/research/scientific-closure-synthesis-2026-09-22.md`, `docs/adr/0010-seleccion-modelos-controlled-daily-v4.md`, `docs/adr/0011-protocolo-controlled-daily-v4-external-pergamino.md`, `openspec/scientific-closure/decisions.md` (GD-38, GD-40), `openspec/scientific-closure/README.md`, `openspec/scientific-closure/changes.json`, `openspec/scientific-closure/closure-verification-2026-09-20/claim-evidence-review.json`, `src/experiment_runner/controlled_daily_v4/{stage_a_runner.py,freezing.py,features.py,config.py,provenance.py,ingestion.py}`, y el código nuevo de esta ronda: `src/predictive_modeling/bundle_export.py`, `src/experiment_runner/pergamino_ensemble_demo_runner.py`, `tests/test_pergamino_ensemble_demo_runner.py`, `tests/test_pergamino_ensemble_demo_runner_ingestion.py`, `backend/tests/test_pergamino_ensemble_demo_http.py`. Verificaciones de identidad de esta y la ronda anterior: `sha256sum` de los dos CSV crudos, `--validate-inputs-only` (host y dentro de `experiment-v4-scientific-closure:latest`), y `ls` de nombres de archivo (sin lectura de contenido) en `/home/gus/scientific-closure-runtime/evidence/{A,B,C}` vía WSL Ubuntu.
