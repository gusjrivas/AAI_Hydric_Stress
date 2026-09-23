# Spec delta: historical-replay

Capacidad nueva, de solo lectura sobre evidencia ya persistida del protocolo
`controlled_daily_v3` (`experiment-runner`) y del contrato de retroalimentación
(`human-feedback`). No entrena, no infiere, no recalcula métricas agregadas, no
genera predicciones nuevas. Ver `openspec/changes/add-causal-historical-replay/design.md`
para el diseño completo, la evidencia del candidato verificado, y
`traceability.md` para la matriz de pruebas previstas.

## ADDED Requirements

### Requirement: RH-01 — Rechazo de identidad de predicción duplicada

El sistema DEBE rechazar explícitamente, sin recuperación silenciosa,
cualquier par de registros cuya identidad completa
`(experiment_id, run_id, config_name, seed, timestamp_origen)` sea idéntica.
Una colisión de `target_timestamp` entre registros con identidad distinta se
trata como un problema separado (ver RH-11, "horizonte incompatible"), nunca
como el mismo tipo de error.

#### Scenario: Identidad completa duplicada

- **GIVEN** dos registros con la misma tupla `(experiment_id, run_id,
  config_name, seed, timestamp_origen)`
- **WHEN** se intenta incorporar el segundo al conjunto de predicciones
  históricas
- **THEN** el sistema falla explícitamente, sin promediar, sobrescribir ni
  elegir uno arbitrariamente

#### Scenario: Colisión de fecha objetivo sin duplicación de identidad no se confunde con duplicado

- **GIVEN** dos registros con identidad distinta que declaran el mismo
  `target_timestamp`
- **WHEN** se valida el conjunto de predicciones del run
- **THEN** el sistema lo reporta como "horizonte incompatible" (RH-11), no
  como "identidad duplicada"

### Requirement: RH-02 — Visibilidad de la predicción independiente de la observación

El sistema DEBE mostrar una predicción histórica (`ReplayPredictionView`,
con `timestamp_origen`, `target_timestamp`, `y_proba`, `y_pred` y metadatos de
trazabilidad) desde que la fecha simulada alcanza su `timestamp_origen`,
independientemente de si su observación posterior ya fue revelada.

#### Scenario: Predicción visible antes de alcanzar su fecha objetivo

- **GIVEN** un `ReplayClockState` con `timestamp_origen <= fecha_simulada <
  target_timestamp` para una predicción histórica
- **WHEN** se consulta esa predicción
- **THEN** la respuesta incluye `timestamp_origen`, `target_timestamp`,
  `y_proba`, `y_pred` y su trazabilidad, sin incluir `y_true`,
  `target_observed` ni ningún baseline

#### Scenario: Predicción no visible mientras su origen sea futuro

- **GIVEN** un `ReplayClockState` con `fecha_simulada < timestamp_origen`
- **WHEN** se consulta el conjunto de predicciones del recorrido
- **THEN** esa predicción no aparece en la respuesta, en ningún campo

### Requirement: RH-03 — Revelación de la observación en la fecha objetivo, si está disponible

El sistema DEBE revelar `y_true` y el estado de la medición objetivo
exactamente cuando `fecha_simulada >= target_timestamp` y `target_observed`
sea verdadero; cuando `target_observed` sea falso, DEBE revelar únicamente
ese estado, sin fabricar ni mostrar una comparación.

#### Scenario: Revelación con objetivo observado

- **GIVEN** un `ReplayClockState` con `fecha_simulada >= target_timestamp` y
  `target_observed=true`
- **WHEN** se consulta esa predicción
- **THEN** la respuesta incluye `y_true`, `target_observed=true`, los
  baselines, y el estado de la medición objetivo (siempre "medida")

#### Scenario: Alcance del objetivo sin observación disponible

- **GIVEN** un `ReplayClockState` con `fecha_simulada >= target_timestamp` y
  `target_observed=false`
- **WHEN** se consulta esa predicción
- **THEN** la respuesta incluye únicamente `target_observed=false` con un
  estado explícito "objetivo no observado en este run", sin `y_true` ni
  comparación con `y_pred`

#### Scenario: Salto del reloj por encima de la fecha objetivo revela correctamente

- **GIVEN** un `ReplayClockState` que avanza en un solo paso desde antes de
  `timestamp_origen` hasta después de `target_timestamp`
- **WHEN** se consulta esa predicción tras el salto
- **THEN** la respuesta es idéntica a la que se obtendría avanzando el reloj
  día por día hasta el mismo punto

### Requirement: RH-04 — Conservación exacta y proyección determinística al mover el reloj

El sistema DEBE preservar sin alteración los valores de un
`HistoricalPredictionRecord` al avanzar o retroceder el `ReplayClockState`, y
DEBE poder llevar el reloj hasta la última `target_timestamp` del run aunque
esta sea posterior a la última `timestamp_origen` disponible.

#### Scenario: Retroceder oculta la observación sin alterar el registro interno

- **GIVEN** una predicción ya revelada
- **WHEN** el reloj retrocede antes de su `target_timestamp`
- **THEN** la proyección deja de incluir `y_true`/`target_observed`/baselines,
  pero el `HistoricalPredictionRecord` interno permanece sin cambios

#### Scenario: Volver a alcanzar la fecha objetivo reproduce la misma revelación

- **GIVEN** una predicción ocultada por un retroceso según el escenario
  anterior
- **WHEN** el reloj vuelve a avanzar hasta alcanzar su `target_timestamp`
- **THEN** los valores revelados son idénticos a los de la primera revelación

#### Scenario: El reloj alcanza la última fecha objetivo del run

- **GIVEN** un run cuya última `timestamp_origen` es anterior a su última
  `target_timestamp`
- **WHEN** el reloj avanza hasta el final del período elegible
- **THEN** puede alcanzar esa última `target_timestamp`, revelando su
  observación si corresponde, sin quedar limitado por la última
  `timestamp_origen`

### Requirement: RH-05 — Estados unificados de medición y ausencia de comparación inválida

El sistema DEBE distinguir, para toda medición relevante del recorrido, entre
`medida` (valor crudo presente en la fuente), `imputada` (completada por
`interpolate_missing_causal`, identificable por el marcador `<columna>_imputado`),
`no_determinado` (el marcador existe conceptualmente pero no fue derivado
para esta instancia) y `sin_dato_en_fuente` (ausente incluso tras la
imputación causal), sin sustituir ninguno de estos estados por un valor
plausible ni por otro estado. La medición objetivo que resuelve `y_true` es
siempre `medida` cuando `target_observed=true` (nunca se imputa el objetivo).

#### Scenario: Medición del historial pre-corte sin marcador de imputación derivado

- **GIVEN** una fecha del historial mostrado antes de la revelación cuyo
  marcador de imputación no fue recomputado para esta instancia
- **WHEN** se construye su estado de medición
- **THEN** el estado queda como `no_determinado`, nunca como `medida` ni como
  un valor numérico inferido

#### Scenario: Medición ausente sin marcador de causa comprobada

- **GIVEN** una fecha cuyo valor crudo y su imputación causal están ambos
  ausentes
- **WHEN** se construye su estado de medición
- **THEN** el estado queda como `sin_dato_en_fuente`, sin atribuir la causa a
  un componente físico (p. ej. "sensor") que no fue comprobado

#### Scenario: `target_observed=false` no produce comparación

- **GIVEN** una predicción con `target_observed=false` ya alcanzada por el
  reloj
- **WHEN** se muestra su resultado
- **THEN** se exhibe "sin comparación posible: objetivo no observado en este
  run", sin calcular ni mostrar coincidencia/discrepancia con `y_pred`

#### Scenario: `y_proba` no se presenta como probabilidad calibrada

- **GIVEN** una predicción histórica con `y_proba` revelado en detalle técnico
- **WHEN** se muestra al usuario
- **THEN** se denomina "salida del clasificador" y se acompaña de la
  limitación explícita de que no existe evidencia de calibración para ese
  valor

### Requirement: RH-06 — Trazabilidad hasta el run y evidencia de entrenamiento

El sistema DEBE exponer, junto con cada predicción histórica mostrada, su
`experiment_id`, `run_id` (hijo), `mlflow.parentRunId`, `config_name`, `seed`,
y los parámetros de procedencia del run padre (`dataset_sha256`, `commit_sha`,
`split_date`, `pipeline_version`), declarando si la vinculación run↔dataset
fue verificada por hash de ejecución (como en el candidato de este *change*)
o solo por consistencia observacional (para candidatos futuros donde ese
hash no exista), y si el run corresponde a un modelo fijo confirmado o a una
identidad no resuelta.

#### Scenario: Trazabilidad resuelta vía el run padre

- **GIVEN** un run hijo cuyos parámetros de procedencia completos están
  registrados únicamente en su `mlflow.parentRunId`
- **WHEN** se muestra la trazabilidad de una predicción de ese run
- **THEN** la trazabilidad se resuelve siguiendo esa referencia, no se
  reporta como "no disponible" solo porque el run hijo no los tenga
  directamente

#### Scenario: Vinculación verificada por hash de ejecución

- **GIVEN** un run cuyo `dataset_sha256` fue capturado por la canalización en
  el momento de la ejecución
- **WHEN** se muestra la trazabilidad de una predicción de ese run
- **THEN** la trazabilidad declara "vinculación verificada por hash de
  ejecución", distinguiéndola de una vinculación por consistencia
  observacional

### Requirement: RH-07 — Feedback de demostración persistido por separado, solo tras revelación

El sistema DEBE persistir el feedback de demostración
(`ReplayFeedbackRecord`) en un store lógico distinto del
`feedback__<sensor_id>.parquet` operativo, con `registered_at` y
`simulated_at` separados, admitiendo el registro únicamente después de que la
observación de esa predicción haya sido revelada, sin que ese feedback pueda
alcanzar `select_recalibration_observations`, `recalibrate_predictor`,
`recalibrate_model` ni `POST /recalibrate/{sensor_id}`.

#### Scenario: Rechazo de feedback antes de la revelación

- **GIVEN** una predicción cuya observación todavía no fue revelada por el
  reloj vigente
- **WHEN** se intenta registrar feedback de demostración sobre ella
- **THEN** el sistema rechaza el registro explícitamente

#### Scenario: Retroceder oculta también el feedback ya registrado

- **GIVEN** una predicción con feedback de demostración ya registrado y
  revelada
- **WHEN** el reloj retrocede antes de su `target_timestamp`
- **THEN** la proyección deja de mostrar ese feedback, sin eliminar ni alterar
  el registro interno

#### Scenario: Feedback de demostración no es visible para la recalibración

- **GIVEN** un `ReplayFeedbackRecord` registrado durante una sesión de
  reproducción histórica
- **WHEN** se ejecuta una recalibración sobre cualquier predictor real
- **THEN** ese registro no aparece entre las observaciones consideradas

#### Scenario: Fecha real y fecha simulada quedan separadas

- **GIVEN** un feedback registrado durante la reproducción con el reloj
  simulado en una fecha de 2024
- **WHEN** se persiste el registro
- **THEN** `registered_at` refleja la fecha real de la sesión de demostración
  y `simulated_at` refleja la fecha simulada, sin atribuir el feedback a una
  fecha o a un experto histórico que no lo emitió

### Requirement: RH-08 — Estados "No disponible"/"no determinado" con causa

El sistema DEBE, ante cualquier dato no resoluble del recorrido, mostrar un
estado explícito acompañado de la causa concreta (por ejemplo,
"no_determinado: marcador de imputación no recomputado para esta instancia"),
en vez de omitir el campo o completarlo por inferencia.

#### Scenario: Causa explícita ante dato no resoluble

- **GIVEN** un campo del recorrido cuyo valor no puede determinarse con la
  evidencia disponible
- **WHEN** se muestra ese campo
- **THEN** se exhibe el estado explícito junto con la causa concreta

### Requirement: RH-09 — Identificación visible de reproducción retrospectiva

El sistema DEBE identificar visiblemente, en toda respuesta y superficie de
UI de esta capacidad, que se trata de una reproducción retrospectiva de un
backtest ya resuelto, y no de una alerta emitida en producción esperando
validación humana. DEBE además distinguir explícitamente que el filtrado
temporal de la interfaz no acredita, por sí solo, que los insumos crudos
estaban disponibles ese día en un escenario operativo real.

#### Scenario: Marca visible de reproducción retrospectiva

- **GIVEN** cualquier vista o respuesta de esta capacidad
- **WHEN** se presenta al usuario
- **THEN** incluye una identificación explícita de "reproducción histórica
  retrospectiva", distinta de una predicción operativa real

### Requirement: RH-10 — Ejecución reproducible del recorrido elegido

El sistema DEBE seleccionar la fecha inicial del recorrido mediante una regla
determinística y documentada, y DEBE mantener la predicción seleccionada
(`prediccion_seleccionada_id`) como estado separado de la fecha simulada, de
forma que el usuario pueda seguir la misma predicción mientras el reloj
avanza.

#### Scenario: Selección determinística de la fecha inicial

- **GIVEN** el mismo run verificado (`base-seed4`,
  `run_id 1157696b7bb941e394c5af530c762b07`)
- **WHEN** se inicia el recorrido dos veces de forma independiente
- **THEN** ambas ejecuciones seleccionan la misma fecha inicial y producen la
  misma secuencia de revelaciones

#### Scenario: La predicción seguida persiste al avanzar el reloj

- **GIVEN** una predicción seleccionada por el usuario
- **WHEN** el reloj avanza varios días
- **THEN** la interfaz sigue mostrando esa misma predicción seleccionada, no
  la predicción cuyo origen coincide con la nueva fecha simulada

### Requirement: RH-11 — Validación de elegibilidad temporal de un run/config candidato

El sistema DEBE rechazar, antes de incorporar un run/config a esta capacidad,
cualquiera de las siguientes condiciones: entrenamiento con fechas objetivo
posteriores o iguales al corte (`split_date`), etiquetas de entrenamiento
cuyo objetivo no maduró antes del corte, imposibilidad de establecer que el
run corresponde a un modelo fijo único (folds o modelos múltiples sin
identidad resuelta), u horizonte declarado que no coincide con la diferencia
real entre `timestamp_origen` y `target_timestamp` de sus filas.

#### Scenario: Entrenamiento posterior al origen se rechaza

- **GIVEN** un run cuyas fechas de entrenamiento incluyen alguna con fecha
  objetivo igual o posterior al corte
- **WHEN** se valida su elegibilidad para esta capacidad
- **THEN** el run se rechaza explícitamente, sin incorporarse

#### Scenario: Identidad de modelo ambigua se rechaza

- **GIVEN** un run cuyo mecanismo de generación de predicciones no permite
  establecer si proviene de un modelo fijo único o de varios folds
- **WHEN** se valida su elegibilidad
- **THEN** el run se rechaza explícitamente, distinto del caso confirmado de
  `base-seed4` (§2.b de `design.md`)

#### Scenario: Horizonte incompatible se rechaza

- **GIVEN** una fila cuyo `target_timestamp - timestamp_origen` no coincide
  con el `horizon_days` declarado del contrato
- **WHEN** se valida el conjunto de predicciones del run
- **THEN** esa fila (o el run completo, según el alcance de la
  inconsistencia) se rechaza explícitamente

### Requirement: RH-12 — Rechazo de vinculación cruzada de observación

El sistema DEBE rechazar la vinculación de una `ReplayObservation` cuya
serie, dataset o fecha no coincida exactamente con el `target_timestamp` y la
procedencia de dataset declarados por la predicción a la que se intenta
vincular.

#### Scenario: Observación de otra serie o fecha se rechaza

- **GIVEN** una medición candidata a vincular como observación posterior,
  cuya fecha o serie de origen no coincide con la de la predicción
- **WHEN** se intenta vincularla
- **THEN** el sistema rechaza la vinculación explícitamente, sin usarla como
  si correspondiera

### Requirement: RH-13 — Separación explícita de los dos umbrales

El sistema DEBE distinguir y exponer por separado (a) el umbral de humedad
que define `y_true` (percentil de entrenamiento limpio, congelado, en la
unidad física del sensor) y (b) la regla de decisión del clasificador que
produce `y_pred` (`alert_threshold` sobre `y_proba`), sin asumir que son
iguales ni sustituir uno de ellos por un valor no verificado contra el run.

#### Scenario: Los dos umbrales se muestran con su procedencia y unidad propias

- **GIVEN** una predicción histórica de un run con ambos umbrales
  registrados
- **WHEN** se muestra su detalle técnico
- **THEN** el umbral de humedad se exhibe con su unidad física y su origen
  (percentil de entrenamiento), y la regla de decisión del clasificador se
  exhibe por separado, con su propio origen (parámetro `alert_threshold` del
  run), sin fusionarlos en un único valor
