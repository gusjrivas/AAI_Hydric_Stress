# Diseño de la reproducción histórica causal (Paso 1, revisión dirigida)

Continúa `openspec/scientific-closure/causal-historical-replay-2026-09-22/paso0-verificacion-final.md`
(candidato acreditado en su sección "Resultado") y corrige la primera versión
de este documento. Esta revisión completó, en modo lectura sobre servicios y
dependencias ya disponibles (Docker/MLflow/git de este mismo entorno), las
comprobaciones que la primera versión había dejado como pendientes sin
intentar resolverlas. Ver `paso1-revision-dirigida.md` para la fuente exacta
de cada dato citado aquí (API MLflow, commit, artefactos, contenedor).

## 1. Candidato

Experimento `hu7-controlled-daily-v3-formal` (`experiment_id=4`, MLflow puerto
5000), run hijo `FINISHED` `1157696b7bb941e394c5af530c762b07`
(`run_name="base-seed4"`), anidado bajo el run padre
`6d516bb9f778450f8fbe2e5492818e57` (`run_name="base"`,
`mlflow.parentRunId`). Artefactos del run hijo: `predictions.json` (67 filas),
`effective_configuration.json`. Horizonte +3 días. No se extiende a otros
runs/configs/semillas del mismo experimento en esta entrega (ver §8).

**Corrección de arquitectura de trazabilidad**: los parámetros de procedencia
completos (`dataset_sha256`, `commit_sha`, `working_tree_status`,
`model_hyperparameters`, `split_date`, `raw_input_features`, `label_column`,
`percentile`, `alert_threshold`, `pipeline_version`) están registrados
**únicamente en el run padre**, no en el run hijo — el run hijo solo declara
`config_name`/`seed`. Cualquier resolución de procedencia de una predicción
individual debe seguir `run_id` → `mlflow.parentRunId` → parámetros del padre;
resolver solo contra el run hijo es insuficiente y produce una trazabilidad
incompleta.

## 2. Comprobaciones del candidato — resultado (evidencia / conclusión / limitación / efecto)

### 2.a Procedencia run↔dataset

- **Evidencia:** parámetro `dataset_sha256=121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e`
  en el run padre, calculado por `src/experiment_runner/provenance.py::experiment_provenance`
  (`hashlib.sha256(dataset_path.read_bytes())`) **en el momento de la
  ejecución** (`run_date=2026-09-05T06:05:11.417240+00:00`), sobre
  `melchor_romero_2024_consolidado.parquet` — no es un hash calculado hoy que
  se proyecte retroactivamente: es la propia canalización la que lo capturó
  al consumir el archivo. Corroboración adicional de esta pasada: el mismo
  archivo, leído hoy desde el contenedor real en ejecución
  (`aai-hydric-stress-backend-1`, `/workspace/data/melchor_romero_2024_consolidado.parquet`,
  mismo volumen persistente de la arquitectura ADR-0004), produce
  exactamente el mismo SHA-256.
- **Conclusión:** la vinculación run↔dataset queda **verificada por hash de
  ejecución, con corroboración de identidad actual del archivo** — ya no es
  "consistencia observacional" (fechas + `origen='real'`) como se declaraba en
  la versión anterior de este documento.
- **Limitación:** la corroboración de hoy acredita que el archivo no cambió
  *desde* la ejecución hasta hoy; no sustituye ni sería necesaria para
  acreditar la ejecución misma, que ya queda acreditada por el hash capturado
  en 2026-09-05. Ningún hash, calculado ahora o entonces, prueba por sí solo
  que ese archivo era en 2024 una medición correctamente instrumentada — solo
  identifica el contenido consumido.
- **Efecto sobre habilitación:** deja de ser bloqueo. RH-06 debe declarar
  "vinculación verificada por hash de ejecución" para este candidato.

Adicionalmente, `commit_sha=2a40ee68c52d2eb5e2040a36b1029f756f9c048a` (run
padre) y `working_tree_status=""` (árbol de trabajo limpio en el momento de
la ejecución): ese commit existe en este repositorio, es ancestro del `HEAD`
actual (`git merge-base --is-ancestor`, verificado en esta pasada), y su
contenido de `scripts/run_hu7_experiments.py`,
`src/experiment_runner/runner.py`, `src/architecture_integration/pipeline.py`
y `src/predictive_modeling/labeling.py` es exactamente el que se citó en §2.b–2.d.
La identidad ejecutable de este candidato es, por lo tanto, conocida y
verificable — no una versión "no identificada".

### 2.b Modelo fijo o folds, y corte temporal / madurez de las etiquetas

- **Evidencia:** `src/experiment_runner/runner.py::run_configuration` (en el
  commit citado) recibe `model_name="random_forest"` explícito, y llama
  siempre a `run_end_to_end_pipeline(..., model=model, ...)` con `model`
  no-`None`. En `run_end_to_end_pipeline`
  (`src/architecture_integration/pipeline.py`), la rama `model is None`
  (selección automática con validación cruzada purgada,
  `select_best_candidate`) **nunca se ejecuta** cuando se provee un modelo
  explícito; en su lugar: `fitted = clone(model).fit(train[names],
  train.stress_label)` — un único modelo (`RandomForestClassifier`,
  `random_state=4` para esta semilla, confirmado en
  `effective_configuration.json::model_parameters`) entrenado una única vez
  sobre `train`, evaluado una única vez sobre `test`. Ninguna fila de
  `predictions.json` proviene de un fold distinto: las 67 filas de `test` son
  predicciones del mismo modelo fijo.
- **Madurez del corte:** `eligible` (en `run_configuration`) exige
  `reference.timestamp + horizon_days < cutoff` para las fechas candidatas de
  entrenamiento; `run_end_to_end_pipeline` purga de nuevo por fecha objetivo:
  `train = eligible[eligible.target_timestamp < cutoff]` (comentario en el
  propio código: "Purge by target date, not the number of retained rows").
  Confirmado con los valores concretos de este run: `split_date=2024-10-19`
  (cutoff), última fecha de entrenamiento en `effective_configuration.json::training_dates`
  = `2024-10-15` (objetivo `2024-10-18`, anterior al corte); primer origen de
  test = `2024-10-19` (igual al corte), coincide exactamente con el ejemplo ya
  citado en `paso0-verificacion-final.md`.
- **Conclusión:** modelo fijo único, confirmado por código y por parámetros
  del run; corte y madurez de etiquetas de entrenamiento, confirmados por
  código y por los valores concretos de este run.
- **Limitación:** ninguna material. El número de fechas candidatas de
  entrenamiento listadas en `effective_configuration.json` no coincide
  exactamente con `train_rows=199` (métrica del run) — la diferencia proviene
  del filtro adicional de completitud de features (historial insuficiente
  para retardos/ventanas al inicio de la serie) dentro de
  `run_end_to_end_pipeline`, no de escasez ni de selección oculta; se deja
  registrado como precisión menor, no como pendiente.
- **Efecto sobre habilitación:** deja de ser bloqueo.

### 2.c Perturbaciones efectivamente aplicadas y particiones afectadas

- **Evidencia:** `run_configuration` solo inyecta ruido dentro de
  `if noise_std_ratio:` (valor por defecto `0.0` en la firma de la función).
  `scripts/run_hu7_experiments.py` (el script que registra las 4
  configuraciones `base`/`sinteticos`/`anomalias`/`completa`, incluida la de
  este candidato) **nunca pasa `noise_std_ratio`** al llamar
  `run_configuration` — ese parámetro solo lo pasa
  `scripts/run_hu7_scenarios.py`, que registra un conjunto de configuraciones
  con otros nombres (`noise_both_0.3`, `noise_test_only_0.3`,
  `coverage_fraction_0.5`, `recent_fraction_0.5`), distintas de `base`. Por lo
  tanto, para `config_name="base"`, `noise_std_ratio=0.0` (falsy) y el bloque
  de inyección de ruido **no se ejecuta en ningún caso**, para ninguna
  partición.
- Los campos `noise_train_seed`/`noise_test_seed`/`noise_scales` presentes en
  `effective_configuration.json` se generan siempre
  (`np.random.SeedSequence(seed).generate_state(4)` produce 4 sub-semillas
  incondicionalmente) como parte de un esquema de streams de semillas
  independientes reutilizable entre configuraciones — existen como
  contabilidad reproducible, nunca se consumen para transformar datos cuando
  `noise_std_ratio` es `0.0`.
- **Conclusión:** `base-seed4` **no tuvo perturbación aplicada**, en ninguna
  partición — confirmado por trayectoria de código, no por el nombre de la
  configuración ni por comparar `y_proba` con humedad cruda.
- **Limitación:** ninguna. Esta conclusión es específica de esta configuración
  y de este run; no se generaliza a `noise_both_0.3`/`noise_test_only_0.3`
  (fuera de alcance, ver §8).
- **Efecto sobre habilitación:** deja de ser bloqueo. El candidato puede
  etiquetarse explícitamente como "sin perturbación aplicada, verificado por
  código", ya no como condición pendiente.

### 2.d Significado de `target_observed` y tratamiento de objetivos faltantes

- **Evidencia:** `src/predictive_modeling/labeling.py::add_stress_label`
  calcula `stress_label` a partir de `future_value = df[column].shift(-horizon_days)`
  (valor crudo, **nunca imputado** — el objetivo no se imputa, tal como
  declara el protocolo v3) y asigna `stress_label = pd.NA` exactamente cuando
  `future_value.isna()`. `run_end_to_end_pipeline` calcula por separado
  `target_observed = reference[label_column].shift(-horizon_days).notna()`
  — **la misma condición**. La elegibilidad de `train`/`test`
  (`eligible = featured.dropna(subset=base_names + feature_columns + ["stress_label"])`)
  exige `stress_label` no nulo, así que **toda fila que llega a
  `predictions.json` tiene, por construcción, `target_observed=True`** — se
  verificó en esta pasada, contando el artefacto real: 67/67 filas con
  `"target_observed":true`, ninguna en `false` (coincide exactamente con la
  métrica `test_rows=67` del run).
- **Conclusión:** en este candidato específico, `target_observed=false` **no
  ocurre en ningún caso** — no hay, en `predictions.json` de este run, ninguna
  fila con objetivo no madurado. El mecanismo que produciría
  `target_observed=false` (un backtest cuyo período de test alcanzara el
  final de la serie disponible sin horizonte completo) existe en el código,
  pero no está ejercitado por este candidato.
- **Limitación:** el comportamiento de la interfaz ante `target_observed=false`
  (§4, §5) queda especificado de forma genérica para el contrato, pero **no
  puede verificarse contra un ejemplo real de este run** — debe declararse
  explícitamente como "no ejercitado por este candidato" en la documentación
  de la demo, nunca presentado como si se hubiera observado.
- **Efecto sobre habilitación:** no bloquea — es una limitación compatible
  con una demostración correctamente descrita (no oculta el objetivo: lo
  explicita), siempre que el recorrido elegido (§4) no dependa de mostrar ese
  caso, y que la especificación (RH-05) prohíba fabricar una comparación
  cuando ese caso sí ocurra en un candidato futuro.

## 3. Separación de umbrales (corrige §2.d de la versión anterior)

Evidencia exacta, de `effective_configuration.json` y de los parámetros del
run padre — **dos umbrales distintos, de naturaleza distinta, que no deben
confundirse ni asumirse iguales**:

- **(a) Umbral que define `y_true` (humedad):** `fit_stress_threshold(clean_train,
  "soil_moisture", percentile=20.0)` — un valor de humedad de suelo (unidad
  `m3/m3`, según `contract.units`), calculado como el percentil 20 de
  `soil_moisture` del entrenamiento limpio (previo al corte), congelado y
  reutilizado para entrenamiento y evaluación. **Para este run**, el valor
  congelado es `0.31678178906440735` m3/m3 (métrica `threshold`/`threshold_mean`
  del run). `y_true=1` significa "la humedad observada +3 días es menor a ese
  valor congelado" (proxy relativo de esta serie/período, no un umbral
  agronómico validado — capacidad de campo o punto de marchitez no
  determinados aquí).
- **(b) Regla de decisión del clasificador que produce `y_pred`:**
  `alert_threshold=0.5` (parámetro fijo del experimento, **no ajustado ni
  calibrado**), aplicado directamente sobre `y_proba`:
  `y_pred = (y_proba >= 0.5).astype(int)`. No es 0.5 por defecto asumido sin
  verificar: es el valor real registrado en `effective_configuration.json::contract.alert_threshold`
  y en los parámetros del run padre.
- Estos dos valores **no son intercambiables ni comparables entre sí**: (a)
  está en la escala de humedad de suelo, (b) está en la escala de
  probabilidad del clasificador. No se recalculan ni se sobrescriben clases
  archivadas en esta especificación ni en ninguna implementación futura de
  esta capacidad.

**Presentación en la vista principal**: clase predicha (`y_pred`) con su
significado explícito de "proxy estadístico relativo" (nunca "diagnóstico
agronómico validado"). **Detalle técnico**, si se conserva `y_proba`: se
denomina "salida del clasificador" (no "probabilidad de estrés"), acompañada
de la advertencia de que su calibración no está acreditada — se buscó
específicamente evidencia de calibración en esta pasada
(`src/predictive_modeling/calibration_assessment.py`,
`calibration_manifest.py`) y se confirmó que **no aplica a este run**: ese
motor pertenece a una capacidad distinta (`add-daily-multihorizon-predictors`,
manifiesto `config/producer-calibration-plan.frozen.v3.json`), fue
introducido en el repositorio después del commit que produjo este candidato
(`git log` confirma que `calibration_assessment.py` no existe en
`2a40ee68c52d2eb5e2040a36b1029f756f9c048a`), y su propia documentación declara
que opera sobre pares `(fecha, probabilidad, resultado)` provistos por quien
llama, con la evaluación real declarada explícitamente como "trabajo futuro
fuera de este módulo" — no se aplicó, ni pudo haberse aplicado, a
`base-seed4`. La advertencia de no calibración se mantiene, ahora con
evidencia de que se buscó activamente y no se encontró, no por omisión.

## 4. Entidades (corregidas)

### 4.1 `HistoricalPredictionRecord` (evidencia original y procedencia)

Identidad estable: **`(experiment_id, run_id, config_name, seed, timestamp_origen)`**.
`target_timestamp` **no** es una dimensión de identidad — es un campo
derivado (`timestamp_origen + horizon_days`), consistente con que el
horizonte es fijo por run/config; tratarlo como parte de la identidad
confundiría una colisión de fecha objetivo (dos orígenes distintos que por
error de horizonte cayeran en el mismo objetivo) con una duplicación real de
identidad (la misma fila repetida).

Campos: `config_name`, `seed`, `horizon_days` (fijo, 3), `y_proba`, `y_pred`,
`y_true`, `target_observed`, baselines (`persistence`, `majority_class`,
`always_stress`), referencia al run padre (`mlflow.parentRunId`) para
`dataset_sha256`/`commit_sha`/`percentile`/`alert_threshold`/`split_date`.
**Inmutable**: el recorrido nunca reescribe ni recalcula estos campos.

**Validaciones de identidad, dos preguntas distintas (RH-01/RH-11/RH-12):**

1. **Duplicación de identidad** (misma tupla completa repetida): error de
   datos, rechazo inmediato.
2. **Colisión de fecha objetivo sin duplicación de identidad** (dos filas con
   identidad distinta que declaran el mismo `target_timestamp`): solo posible
   si el horizonte no es realmente constante para ese run/config — también
   rechazo, pero diagnosticado como "horizonte incompatible", no como
   "duplicado".

### 4.2 `ReplayPredictionView` (proyección pública, nueva — corrige §5.1 anterior)

La vista pública que efectivamente devuelve la API/UI **nunca es
`HistoricalPredictionRecord` directamente** — es una proyección pura,
determinística y sin estado, función de `(HistoricalPredictionRecord,
ReplayClockState.fecha_simulada)`:

- `reloj < timestamp_origen` → la predicción **no aparece en absoluto** en la
  respuesta (ni siquiera con campos ocultos): todavía no fue "emitida" en la
  línea de tiempo simulada.
- `timestamp_origen <= reloj < target_timestamp` → aparecen `timestamp_origen`,
  `target_timestamp`, `y_proba`, `y_pred`, metadatos de trazabilidad (§4.1);
  **no aparecen** `y_true`, `target_observed`, ni ningún baseline, ni
  siquiera como `null` explícito en el cuerpo de la respuesta — el campo
  está ausente de la proyección, no enmascarado.
- `reloj >= target_timestamp` **y** `target_observed=True` → se agrega
  `y_true`, `target_observed`, los baselines, y el estado de la medición
  original vinculada (§4.3).
- `reloj >= target_timestamp` **y** `target_observed=False` → se agrega
  únicamente `target_observed=False` y un estado explícito "objetivo no
  observado en este run" (§5, RH-05) — nunca se muestra `y_true`
  (no existe), nunca se sintetiza una comparación.

El registro interno (`HistoricalPredictionRecord`) permanece siempre completo
e inmutable; solo la proyección cambia con el reloj. Esto reemplaza la regla
anterior (incorrecta) de "excluir la fila completa porque su fecha objetivo
es futura": la fila se excluye solo si su **origen** todavía es futuro; una
vez emitida, la predicción permanece visible aunque su observación no lo
esté.

### 4.3 `ReplayObservation` (observación/etiqueta posterior)

Dos contextos de medición, distintos y ya no confundidos:

- **Medición objetivo (la que resuelve `y_true`)**: siempre cruda, nunca
  imputada, por construcción de `add_stress_label`/`target_observed` (§2.d).
  Cuando `target_observed=True`, el estado es siempre **`medida`** — no hay
  ambigüedad para este campo en ningún candidato que llegue a tener
  `target_observed=True`.
- **Historial de mediciones mostrado antes del corte** (la serie de
  `soil_moisture`/`solar_radiation`/`relative_humidity` que el recorrido
  exhibe como "disponible hasta la fecha simulada", para dar contexto):
  **puede incluir valores completados por `interpolate_missing_causal`**
  (forward-fill causal). Esta función (`src/data_quality/imputation.py`,
  vigente en el commit citado) **agrega una columna booleana
  `<columna>_imputado` por cada columna tratada**, marcando exactamente qué
  filas fueron completadas por ella — el mecanismo para distinguir
  `medida`/`imputada` en este contexto **existe y es preciso**, contrario a
  lo que asumía la versión anterior de este documento ("no confirmado que
  exista un marcador").
- **Limitación real, no de conocimiento sino de persistencia**: ese marcador
  no fue serializado en los artefactos MLflow de este run (`predictions.json`
  solo tiene las columnas de la tabla de test, no las features
  intermedias). Para exhibirlo en el recorrido, la implementación debe
  recomputar `interpolate_missing_causal` sobre el mismo dataset ya
  verificado por hash (§2.a) — una transformación determinística y pura, sin
  aleatoriedad ni reentrenamiento, no una inferencia nueva ni una métrica
  científica recalculada. Mientras esa recomputación no esté implementada,
  el estado debe declararse **`no_determinado`** (mecanismo conocido, dato no
  derivado todavía), nunca inferirse ni mostrarse como si ya se supiera.
- Estado explícito **`sin_dato_en_fuente`**: cuando ni el valor crudo ni el
  resultado de la imputación causal existen (hueco no completable — sin
  observación previa disponible). No se lo llama "hueco de sensor" sin haber
  comprobado la procedencia exacta del faltante (podría deberse a un corte de
  ingesta, no necesariamente al sensor físico); se usa la denominación neutra
  "medición ausente en la fuente original".

### 4.4 `ReplayClockState` (estado del reloj de reproducción)

`session_id` de reproducción (distinto de `demo_sessions/*`). Campos:
`run_id`/`config_name`/`seed` fijados, `fecha_simulada` actual,
**`prediccion_seleccionada_id`** (la identidad de §4.1 que el usuario está
siguiendo — **separada de la fecha simulada**, para poder seguir la misma
predicción mientras el reloj avanza día a día sin perder la selección),
límites del período elegible (`min(timestamp_origen)` .. `max(target_timestamp)`
del run — el reloj debe poder alcanzar `max(target_timestamp)` **aunque
supere `max(timestamp_origen)`**, ya que en este candidato el último origen es
`2024-12-28` pero el último objetivo es `2024-12-31`). Avanzar o retroceder
el reloj **nunca** modifica `HistoricalPredictionRecord`; solo cambia qué
proyección (§4.2) es visible.

**Semántica de fecha diaria**: `frequency="D"`, `day_convention="UTC_naive_midnight"`,
`issuance="after_daily_observations_available"` (del `contract` en
`effective_configuration.json`). "`reloj = D`" significa que las
observaciones del día `D` ya están disponibles (supuesto documentado del
protocolo v3, no verificado por fila — ver §7); por lo tanto
`timestamp_origen <= reloj` incluye el caso `timestamp_origen == reloj`
(la predicción emitida el mismo día `D` es visible desde que el reloj llega a
`D`), y `target_timestamp <= reloj` incluye igualmente el caso de igualdad.

### 4.5 `ReplayFeedbackRecord` (feedback de demostración)

Reutiliza el esquema de `src/human_feedback/schema.py` sin extender el
módulo original. Agrega, a nivel de contrato de esta capacidad: `registered_at`
(timestamp real de registro) y `simulated_at` (fecha del `ReplayClockState`
al registrar), siempre separados.

**Regla de temporalidad del feedback (nueva, corrige ausencia en la versión
anterior)**: el feedback de demostración solo puede registrarse para una
predicción cuya observación ya fue revelada por la proyección vigente
(`reloj >= target_timestamp` y `target_observed=True`) — intentar registrarlo
antes de la revelación se rechaza explícitamente (sería registrar una
opinión sobre un resultado que la interfaz todavía no debería conocer).
**Al retroceder el reloj** por debajo de `target_timestamp` de una predicción
que ya tiene feedback registrado, la **proyección** de ese feedback (no el
registro interno, que se preserva íntegro) se oculta junto con la
observación — ningún comentario o feedback visible puede revelar
indirectamente un resultado futuro todavía no alcanzado por el reloj vigente.

## 5. Recorrido funcional (especificación, no implementación)

1. Seleccionar una fecha inicial dentro del período elegible del run
   verificado, por una regla determinística: la primera fecha, en orden
   cronológico de `timestamp_origen`, cuyo `target_timestamp` sea resoluble
   (`target_observed=true`, el único caso presente en este candidato — ver
   §2.d) y cuya medición objetivo sea `medida` (siempre lo es cuando
   `target_observed=true`, §4.3). Nunca se elige por acertar la predicción.
2. Mostrar el historial de mediciones disponible hasta el corte simulado
   (§4.4), con su estado (`medida`/`imputada`/`no_determinado`/`sin_dato_en_fuente`,
   §4.3).
3. Mostrar la predicción archivada (`ReplayPredictionView` con
   `timestamp_origen <= reloj`), incluyendo `y_pred` en la vista principal
   (§3) y, en detalle técnico, `y_proba` con su advertencia de no
   calibración.
4. Avanzar el reloj histórico (`ReplayClockState.fecha_simulada`),
   preservando `prediccion_seleccionada_id` (§4.4).
5. Al alcanzar `target_timestamp <= reloj`, revelar `y_true`/`target_observed`
   y, si `target_observed=True`, el estado de la medición objetivo
   (siempre `medida`, §4.3); si `target_observed=False` (no ejercitado por
   este candidato, §2.d), revelar solo ese estado, sin comparación.
6. Mostrar coincidencia o discrepancia entre `y_pred` y `y_true` **solo
   cuando ambos existen** (`target_observed=True`); si `target_observed=False`,
   mostrar explícitamente "sin comparación posible: objetivo no observado en
   este run" (RH-05) — nunca recalcular métricas agregadas del recorrido.
7. Registrar feedback nuevo (`ReplayFeedbackRecord`) vinculado a esa
   predicción, solo disponible después del paso 5 (§4.5).
8. Conservar intactos los artefactos originales: el recorrido es una vista de
   lectura y proyección, no una copia mutable.

No se incorporan horizontes +1/+2 ni escenarios sintéticos en esta primera
entrega.

## 6. Aislamiento y filtrado (backend)

- **Filtrado por proyección, no por exclusión de fila completa** (§4.2): el
  backend construye `ReplayPredictionView` a partir del reloj vigente; el
  cliente nunca recibe `y_true`/`target_observed`/baselines de una fecha
  objetivo no alcanzada, en ningún campo de la respuesta (RH-02/RH-03).
- **Conservación exacta**: avanzar o retroceder el reloj no altera
  `HistoricalPredictionRecord`; una predicción ya revelada, ocultada por un
  retroceso y vuelta a alcanzar, produce exactamente la misma proyección
  (RH-04).
- **Aislamiento del feedback de demostración**: `ReplayFeedbackRecord` se
  persiste en un store lógico separado del `feedback__<sensor_id>.parquet`
  operativo (convención de `src/data_ingestion/sensor_naming.py`), nunca
  pasa a `select_recalibration_observations`/`recalibrate_predictor`/
  `recalibrate_model`/`POST /recalibrate/{sensor_id}` (RH-07). Esta exclusión
  es arquitectónica (tipos/rutas separados), no un valor de configuración.

## 7. Paquete de lectura reproducible (solo diseño, no exportado)

Contenido:

- Copia de `predictions.json` y `effective_configuration.json` del run hijo,
  y de los parámetros del run padre (§1) serializados aparte (no todos están
  en el mismo objeto MLflow).
- Datos necesarios para las mediciones visibles: el recorte de
  `melchor_romero_2024_consolidado.parquet` correspondiente al período del
  run (fechas de origen mínimas a máximas menos el historial de
  retardos/ventanas necesario), con su propio hash.
- Metadatos de procedencia, unidades, etiquetas y cortes: `contract`
  (`effective_configuration.json`), `dataset_sha256`/`commit_sha`/`split_date`
  del run padre, el umbral congelado (a) y `alert_threshold` (b) de §3,
  identidad del servidor MLflow consultado (host/puerto/versión).
- **Dos familias de hash, explícitamente distinguidas**: (i) **hash de
  evidencia histórica del run** — el `dataset_sha256` ya capturado por la
  canalización en 2026-09-05 (prueba lo que el run consumió); (ii) **hash de
  custodia del paquete** — SHA-256 calculado al construir el paquete de
  lectura, de cada archivo incluido en él (prueba que la copia exportada para
  la defensa no fue alterada después de armarse, no reemplaza a (i)).
- Versión del formato del paquete (campo `package_format_version`) y
  comprobación de integridad prevista al cargarlo: recalcular (ii) sobre cada
  archivo cargado y comparar contra el manifiesto; fallar explícitamente ante
  cualquier discrepancia, sin degradar a advertencia.

No se genera ni se exporta en este *change* (ver `tasks.md`).

## 8. Por qué no se generaliza a los 96 runs

Por instrucción explícita, no se exige verificar varios modelos/runs para
aceptar el primer recorrido. Todo lo verificado en §2–§3 es específico de
`base-seed4`; no se extrapola a otras configs/semillas del mismo experimento,
ni a `noise_both_0.3`/`noise_test_only_0.3`/`coverage_fraction_0.5`/
`recent_fraction_0.5` (que sí tienen perturbación/escasez, por construcción
del script que las genera, `scripts/run_hu7_scenarios.py` — dato de esta
pasada, no verificado en profundidad por no ser el candidato elegido).

## 9. Limitaciones que persisten (no bloqueantes, distintas de bloqueos)

- **`y_proba` sin evidencia de calibración** (§3): limitación permanente y
  correctamente disclosable (RH-05); no bloquea, siempre que nunca se
  presente como probabilidad confiable.
- **Marcador de imputación no persistido en los artefactos de este run**
  (§4.3): mecanismo conocido y determinístico, pendiente de una tarea de
  implementación concreta (recomputar `interpolate_missing_causal`), no de
  una comprobación de conocimiento. No bloquea la habilitación; bloquea sí
  la exhibición de "medida" vs. "imputada" en el historial pre-corte hasta
  que esa tarea se complete — mientras tanto, ese estado se muestra como
  `no_determinado`, nunca omitido ni inferido.
- **Supuesto de disponibilidad diaria de insumos** (protocolo v3): declarado,
  no verificado por fila (no existe campo `ingested_at`/`available_at` en el
  código de ingesta, confirmado por búsqueda ya realizada en Paso 0). El
  recorrido documenta el supuesto (§4.4), no lo demuestra por fila. **No se
  confunde con el filtrado temporal de la interfaz** (§6): probar que la
  interfaz nunca revela el futuro (una propiedad de la implementación, RH-02–RH-04)
  no prueba que los insumos crudos estaban realmente disponibles ese día en
  un escenario operativo real (una propiedad del dato, no verificada). Ambas
  afirmaciones deben mantenerse separadas en la memoria (ver §10).

## 10. Documentación para la memoria

| Afirmación que podrá realizarse | Evidencia requerida | Limitación |
|---|---|---|
| El sistema puede reproducir, con datos reales archivados y procedencia verificada por hash de ejecución, un recorrido histórico de predicción→observación con reloj controlado y causalidad exigida en el backend | Capturas de la UI en estado pre-revelación y post-revelación, log/test del filtrado en backend (RH-02–RH-04), manifiesto de hashes del paquete de lectura (§7) | Un solo run/config (`base-seed4`); no generaliza a los 96 runs del experimento (§8) |
| El backtest de `base-seed4` preserva causalidad temporal (purga por fecha objetivo, madurez de etiquetas de entrenamiento, ausencia de perturbación) tal como lo exige el protocolo v3 | Código citado en §2.b/§2.c, valores concretos del run (`split_date`, `training_dates`, `noise_std_ratio` nunca pasado para `base`) | Ninguna material; la ausencia de perturbación y la madurez de entrenamiento quedan confirmadas por trayectoria de código, no por medición estadística de sus efectos |
| La predicción mostrada corresponde a un backtest retrospectivo de v3 ya resuelto, no a una alerta operativa validada después por un humano | `predictions.json`, `target_observed=true` en todas las filas de este run | Debe presentarse explícitamente como backtest formal (RH-09) |
| El filtrado temporal de la interfaz nunca revela el futuro | Tests previstos RH-02–RH-04 sobre la implementación | **No prueba, por sí sola, que los insumos crudos estaban disponibles ese día en producción real** (§9) — son dos afirmaciones distintas, nunca se presenta una como si demostrara la otra |
| El sistema demuestra utilidad agronómica validada | — no puede afirmarse — | El umbral (a) es un proxy relativo de esta serie, no un valor agronómico (capacidad de campo/punto de marchitez no determinados); `y_proba` no tiene evidencia de calibración (§3) |

No se propone ninguna modificación al capítulo 2 (ya corregido). Cualquier
inconsistencia detectada durante la implementación entre lo aquí especificado
y lo efectivamente construido debe señalarse por separado para una decisión
posterior del responsable, no resolverse unilateralmente reinterpretando esta
especificación.

Capturas/artefactos previstos para el capítulo 3: estado del reloj antes de
la revelación (mostrando la predicción visible y la observación ausente),
estado inmediatamente posterior a la revelación, retroceso del reloj
ocultando de nuevo observación/feedback, formulario de feedback de
demostración con `registered_at`/`simulated_at` visibles por separado, y el
manifiesto de hashes del paquete de lectura (§7).
