# PASO 1 — Revisión dirigida y habilitación del candidato

Fecha: 2026-09-23.
Rama `feat/causal-historical-replay`, worktree
`C:\Repo\AAI_Hydric_Stress_causal_historical_replay`. Se preservaron
intactos, sin modificar, los tres informes de Paso 0
(`paso0-relevamiento.md`, `paso0-ampliacion.md`, `paso0-verificacion-final.md`)
y todos los cambios ajenos ya presentes en el árbol. Alcance de esta tarea:
documentación e inspección en modo lectura mediante servicios y
dependencias ya disponibles en este entorno (API HTTP de MLflow, `git`
sobre el historial ya existente, `docker exec` de solo lectura sobre un
contenedor que ya estaba en ejecución). No se implementó código de
aplicación, no se entrenó, no se ejecutaron inferencias, no se recalcularon
métricas científicas, no se accedió al holdout C. No se hizo commit, push,
PR ni merge.

## 1. Correcciones realizadas

### 1.1 Contrato temporal (`design.md` §4.2, corrige §5.1 anterior)

Regla anterior (incorrecta): excluir la fila completa de una predicción
histórica si su fecha objetivo todavía era futura. Corrección aplicada:

- La predicción es visible desde `timestamp_origen <= reloj`,
  independientemente de si su observación ya maduró.
- La observación (`y_true`/`target_observed`/baselines) solo es visible
  cuando `target_timestamp <= reloj` **y** está disponible
  (`target_observed=true`).
- Si `reloj < timestamp_origen`, la predicción no aparece en absoluto (ni
  siquiera con campos ocultos).
- El reloj puede alcanzar la última `target_timestamp` del run aunque sea
  posterior a la última `timestamp_origen` disponible.
- Se separó el registro interno (`HistoricalPredictionRecord`, inmutable) del
  objeto público de respuesta, ahora una proyección pura y determinística
  (`ReplayPredictionView`, nueva entidad, `design.md` §4.2) función de
  `(registro, reloj)`.
- Se separó la predicción seleccionada (`prediccion_seleccionada_id`) de la
  fecha simulada, para poder seguir el mismo pronóstico mientras el reloj
  avanza.
- Se precisó la semántica de fecha diaria: `frequency="D"`,
  `day_convention="UTC_naive_midnight"`, `issuance="after_daily_observations_available"`
  (del `contract` real del run) — "reloj = D" incluye el día D completo como
  disponible, y las comparaciones `<=`/`>=` incluyen el caso de igualdad.

Se agregaron los 5 escenarios pedidos como pruebas previstas de `RH-02`/`RH-03`/`RH-04`
en `specs/historical-replay/spec.md` y `traceability.md`.

### 1.2 Separación de umbrales (`design.md` §3, corrige §2.d anterior)

Se distinguieron explícitamente (a) el umbral de humedad que define `y_true`
y (b) la regla de decisión del clasificador que produce `y_pred`, con sus
valores reales verificados para este run (ver §2.4 más abajo) — no se asumió
que fueran iguales ni se inventó un valor de 0.5 sin verificar. Nuevo
requisito `RH-13`.

### 1.3 Requisitos y pruebas de causalidad ampliados

Se agregaron `RH-11` (validación de elegibilidad temporal de un run/config
candidato: entrenamiento posterior al origen, etiquetas no maduras al corte,
identidad de modelo ambigua, horizonte incompatible), `RH-12` (rechazo de
vinculación cruzada de observación de otra serie/fecha), y se corrigió `RH-01`
para distinguir explícitamente duplicación de identidad completa de
colisión de fecha objetivo por horizonte incompatible (que ahora se reporta
bajo `RH-11`, no como el mismo tipo de error).

### 1.4 Observaciones y feedback

Se unificaron los estados de medición (`medida`/`imputada`/`no_determinado`/
`sin_dato_en_fuente`) en diseño, spec (`RH-05`) y matriz de trazabilidad. Se
dejó de llamar "hueco de sensor" a un faltante sin comprobar su procedencia;
se usa "medición ausente en la fuente original". Se especificó el
comportamiento de `target_observed=false` (estado explícito, sin
comparación fabricada). Se agregó la regla de temporalidad del feedback: solo
se registra después de revelar el resultado, y un retroceso del reloj oculta
también el feedback ya revelado (proyección, no el registro interno) —
`RH-07` ampliado con dos escenarios nuevos.

### 1.5 Paquete y plan de implementación

Se completó el diseño del paquete reproducible (`design.md` §7) con el
contenido pedido y se distinguieron explícitamente dos familias de hash: el
hash de evidencia histórica del run (`dataset_sha256`, capturado en
ejecución) y el hash de custodia del paquete (calculado al construirlo, para
verificar integridad de la copia exportada). Se reordenaron las tareas
futuras (`tasks.md`): paquete y lector → validaciones → API → interfaz →
feedback → verificación del recorrido y capturas, con tareas explícitas de
frontend (antes ausentes).

## 2. Resultados de las comprobaciones del candidato, con fuentes exactas

Candidato: experimento `hu7-controlled-daily-v3-formal` (`experiment_id=4`),
run hijo `1157696b7bb941e394c5af530c762b07` (`base-seed4`), run padre
`6d516bb9f778450f8fbe2e5492818e57` (`base`).

### 2.1 Procedencia run↔dataset

- **Evidencia:** `curl http://localhost:5000/api/2.0/mlflow/runs/get?run_id=6d516bb9f778450f8fbe2e5492818e57`
  (API real de MLflow, puerto 5000, arquitectura ADR-0004) devuelve el
  parámetro `dataset_sha256=121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e`,
  calculado por `src/experiment_runner/provenance.py::experiment_provenance`
  (`hashlib.sha256(dataset_path.read_bytes())`) en el momento de la
  ejecución (`run_date=2026-09-05T06:05:11.417240+00:00`). Corroboración de
  esta pasada: `docker exec aai-hydric-stress-backend-1 python -c
  "hashlib.sha256(open('/workspace/data/melchor_romero_2024_consolidado.parquet','rb').read()).hexdigest()"`
  devuelve el mismo valor exacto, hoy, sobre el archivo real en ejecución
  (mismo volumen persistente de la arquitectura real, no una copia).
- **Conclusión:** vinculación **verificada por hash de ejecución**, con
  corroboración de identidad actual del archivo. No es una coincidencia de
  fechas ni de `origen='real'`.
- **Limitación:** un hash acredita contenido, no la calidad de la medición
  original en 2024; el hash de hoy corrobora que el archivo no cambió desde
  la ejecución, no sustituye al hash capturado en ese momento (que ya es
  suficiente por sí solo).
- **Efecto sobre habilitación:** deja de ser bloqueo.

### 2.2 Modelo fijo o folds y asociación con cada fila

- **Evidencia:** `git show 2a40ee68c52d2eb5e2040a36b1029f756f9c048a:src/experiment_runner/runner.py`
  y `...src/architecture_integration/pipeline.py` (código exacto de la
  versión ejecutada, commit identificado por el parámetro `commit_sha` del
  run padre, verificado como ancestro del `HEAD` actual con
  `git merge-base --is-ancestor`, y `working_tree_status=""` — árbol limpio
  en el momento de la ejecución). `run_configuration` invoca siempre
  `run_end_to_end_pipeline(..., model=model, ...)` con un modelo explícito
  (`random_forest`); en `run_end_to_end_pipeline`, la rama `model is None`
  (selección automática con validación cruzada purgada) nunca se ejecuta en
  ese caso — se toma `fitted = clone(model).fit(train[names], train.stress_label)`,
  un único ajuste.
- **Conclusión:** modelo fijo único (`RandomForestClassifier`,
  `random_state=4`), sin folds, confirmado por código. Las 67 filas de
  `predictions.json` provienen del mismo modelo.
- **Limitación:** ninguna material.
- **Efecto sobre habilitación:** deja de ser bloqueo.

### 2.3 Corte temporal y madurez de las etiquetas de entrenamiento

- **Evidencia:** mismo código citado en §2.2: `eligible` exige
  `reference.timestamp + horizon_days < cutoff` para las fechas candidatas de
  entrenamiento; `run_end_to_end_pipeline` purga de nuevo:
  `train = eligible[eligible.target_timestamp < cutoff]` (comentario del
  propio código: "Purge by target date, not the number of retained rows").
  Valores concretos de este run (parámetro `split_date=2024-10-19` del run
  padre; `training_dates` de `effective_configuration.json` con máximo
  `2024-10-15`; primer origen de `predictions.json` = `2024-10-19`).
- **Conclusión:** el corte se respeta y las etiquetas de entrenamiento están
  maduras antes del corte, confirmado por código y por los valores
  concretos del run.
- **Limitación:** ninguna material.
- **Efecto sobre habilitación:** deja de ser bloqueo.

### 2.4 Perturbaciones efectivamente aplicadas y particiones afectadas

- **Evidencia:** `run_configuration` solo inyecta ruido dentro de
  `if noise_std_ratio:` (por defecto `0.0`). `git show
  2a40ee68...:scripts/run_hu7_experiments.py` (el script que registra
  `base`/`sinteticos`/`anomalias`/`completa`, incluida `base-seed4`) nunca
  pasa `noise_std_ratio` a `run_configuration` — ese parámetro solo lo pasa
  `scripts/run_hu7_scenarios.py`, para configuraciones con otros nombres
  (`noise_both_0.3`, `noise_test_only_0.3`).
- **Conclusión:** `base-seed4` no tuvo perturbación aplicada en ninguna
  partición, confirmado por trayectoria de código — no por el nombre de la
  configuración ni por comparar `y_proba` con humedad cruda (prohibido por
  esta consigna, y no realizado).
- **Limitación:** los campos `noise_train_seed`/`noise_test_seed`/`noise_scales`
  de `effective_configuration.json` existen siempre (contabilidad
  reproducible incondicional), lo cual explica por qué su sola presencia no
  bastaba como evidencia — se aclara para no volver a interpretarlos como
  indicio de perturbación aplicada.
- **Efecto sobre habilitación:** deja de ser bloqueo.

### 2.5 Significado de `target_observed` y tratamiento de objetivos faltantes

- **Evidencia:** `git show 2a40ee68...:src/predictive_modeling/labeling.py::add_stress_label`
  asigna `stress_label=NaN` exactamente cuando `future_value.isna()` (valor
  crudo del objetivo, nunca imputado); `run_end_to_end_pipeline` calcula
  `target_observed` con la misma condición; la elegibilidad de `test` exige
  `stress_label` no nulo. Verificación directa del artefacto real
  (`predictions.json` descargado vía `GET /get-artifact`): 67/67 filas con
  `"target_observed":true`, 0 en `false` (coincide con la métrica
  `test_rows=67` del run).
- **Conclusión:** en este candidato, `target_observed=false` no ocurre; el
  mecanismo que lo produciría existe en el código pero no está ejercitado
  por ningún ejemplo real de este run.
- **Limitación:** el comportamiento especificado para `target_observed=false`
  (`RH-03`, `RH-05`) no puede verificarse con datos reales de este candidato;
  las pruebas correspondientes requieren un caso construido.
- **Efecto sobre habilitación:** no bloquea — es una limitación de
  cobertura de pruebas, no una condición desconocida sobre el candidato
  elegido.

### 2.6 Separación de umbrales (valores reales)

- **Evidencia:** `effective_configuration.json::contract` (artefacto
  descargado del run) declara `percentile=20.0`, `label_column="soil_moisture"`,
  `units.soil_moisture="m3/m3"`, `target_rule="observed_value_at_t_plus_h_less_than_frozen_threshold"`,
  `alert_threshold=0.5`. La métrica `threshold`/`threshold_mean` del run
  (API MLflow) = `0.31678178906440735` (valor de humedad, m3/m3, congelado
  por `fit_stress_threshold` sobre el entrenamiento limpio). `y_pred =
  (y_proba >= alert_threshold).astype(int)` en `run_configuration`.
- **Conclusión:** dos valores distintos, de naturaleza distinta:
  (a) 0.31678... m3/m3 define `y_true`; (b) 0.5 (probabilidad) define
  `y_pred`. No son intercambiables.
- **Limitación:** ninguna material.
- **Efecto sobre habilitación:** deja de ser bloqueo.

### 2.7 Marcador de imputación por fila (medida vs. imputada)

- **Evidencia:** `git show 2a40ee68...:src/data_quality/imputation.py::interpolate_missing_causal`
  agrega una columna booleana `<columna>_imputado` por cada columna tratada,
  marcando exactamente qué filas fueron completadas por forward-fill causal.
- **Conclusión:** el mecanismo **existe y es preciso** — corrige la
  suposición anterior de que no había marcador confirmado.
- **Limitación:** ese marcador no fue serializado en los artefactos MLflow de
  este run (`predictions.json` solo trae las columnas de test, no las
  features intermedias); para exhibirlo hace falta recomputar la función
  (determinística, sin aleatoriedad) sobre el mismo dataset ya verificado
  por hash — tarea de implementación concreta, no una comprobación de
  conocimiento pendiente.
- **Efecto sobre habilitación:** no bloquea. Mientras no se implemente, el
  estado del historial pre-corte se declara `no_determinado`.

### 2.8 Evidencia de calibración de `y_proba`

- **Evidencia:** búsqueda dirigida en `src/predictive_modeling/` de
  `calibrat`/`isotonic`/`platt` encontró `calibration_assessment.py` y
  `calibration_manifest.py`; `git log --follow` y `git show
  2a40ee68...:src/predictive_modeling/calibration_assessment.py` (falla,
  "exists on disk, but not in" el commit) confirman que ese módulo se
  introdujo **después** del commit que produjo este run. El propio módulo
  declara operar sobre pares `(fecha, probabilidad, resultado)` provistos
  por quien llama, con la evaluación real como "trabajo futuro fuera de este
  módulo", y pertenece a otra capacidad (`add-daily-multihorizon-predictors`).
- **Conclusión:** no hay evidencia de calibración para `base-seed4`, y no
  podría haberla (el módulo no existía cuando se ejecutó, y aunque existiera
  hoy, pertenece a otra capacidad).
- **Limitación:** permanente, no una tarea pendiente.
- **Efecto sobre habilitación:** no bloquea — se disclosa siempre (`RH-05`).

**Impedimentos de entorno encontrados:** ninguno. `python3`/`python` no
están disponibles en el shell de este worktree (confirmado en Paso 0); se
resolvió consultando la API HTTP de MLflow directamente con `curl` y
ejecutando Python de solo lectura dentro del contenedor
`aai-hydric-stress-backend-1`, que ya estaba en ejecución — sin instalar
nada ni levantar servicios nuevos.

## 3. Estado de la especificación

Completa para el alcance de este paso: contratos, recorrido funcional
corregido, 13 requisitos con escenarios (`RH-01`..`RH-13`), matriz de
trazabilidad con pruebas previstas, tareas ordenadas incluyendo frontend.
Ver `openspec/changes/add-causal-historical-replay/`.

## 4. Estado de habilitación del candidato

**Habilitado para implementación**, con limitaciones documentadas y no
bloqueantes (ver §5). La especificación puede estar completa incluso si el
candidato hubiera seguido bloqueado — en este caso no lo está: las cuatro
comprobaciones que la versión anterior dejaba pendientes (procedencia,
modelo fijo, perturbación, marcador de imputación) se investigaron
activamente y se resolvieron con evidencia exacta, en vez de trasladarse de
nuevo a tareas futuras sin intentar resolverlas.

## 5. Bloqueos materiales y limitaciones (separados)

**Bloqueos materiales: ninguno.**

**Limitaciones compatibles con una demostración correctamente descrita (no
bloqueantes):**

- Ausencia de evidencia de calibración de `y_proba` (permanente, §2.8).
- Marcador de imputación del historial pre-corte no persistido en los
  artefactos de este run, aunque el mecanismo existe y es determinístico
  (§2.7) — tarea de implementación, no incógnita.
- `target_observed=false` no ejercitado por ningún ejemplo real de
  `base-seed4` (§2.5) — limita la cobertura de pruebas con datos reales, no
  bloquea la especificación del comportamiento genérico.
- El supuesto de disponibilidad diaria de insumos crudos sigue siendo un
  supuesto documentado del protocolo v3, no verificado por fila — distinto
  y no intercambiable con el filtrado temporal de la interfaz, que sí será
  verificable por test una vez implementado.

Ninguna de estas limitaciones se declaró "No disponible" sin más, ni se
convirtió en limitación permanente sin haber intentado resolverla primero.

## 6. Próxima tarea concreta

Iniciar `tasks.md` §1 ("Paquete y lector"): construir el manifiesto de hashes
del paquete de lectura reproducible y el módulo de lectura de runs v3 que
resuelve la procedencia siguiendo `mlflow.parentRunId`, junto con la
recomputación de `interpolate_missing_causal` para derivar el marcador de
imputación del historial pre-corte. Esa tarea requiere autorización
explícita para empezar a escribir código de aplicación, que este paso no
otorga.

## Cierre

Diff de esta tarea: exclusivamente documental —
`openspec/scientific-closure/causal-historical-replay-2026-09-22/paso1-revision-dirigida.md`
(este archivo, nuevo), la actualización de
`openspec/scientific-closure/causal-historical-replay-2026-09-22/paso1-especificacion.md`,
y la actualización de `openspec/changes/add-causal-historical-replay/`
(`proposal.md`, `design.md`, `specs/historical-replay/spec.md`, `tasks.md`,
`traceability.md`). No se modificaron `paso0-relevamiento.md`,
`paso0-ampliacion.md` ni `paso0-verificacion-final.md`, ni ningún otro
archivo del árbol. No se instaló ninguna dependencia nueva; se usaron
`curl`, `git` y `docker exec` de solo lectura sobre servicios ya en
ejecución. No se entrenó, no se ejecutaron inferencias, no se recalcularon
métricas científicas, no se accedió al holdout C. No se hizo commit, push,
PR ni merge. Se detiene aquí para revisión.
