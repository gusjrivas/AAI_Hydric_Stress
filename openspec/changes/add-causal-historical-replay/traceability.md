# Matriz de trazabilidad — add-causal-historical-replay

Requisito → prueba (implementada o prevista) → evidencia. Actualizado tras el
Paso 4 (`paso4-interfaz-feedback.md`), que agregó el feedback de
demostración completo (RH-07), la interfaz, y cerró la incertidumbre de
regresión heredada del Paso 2 (ambos fallos eran ambientales). Las pruebas
marcadas **[implementada]** existen y pasan
(`tests/test_historical_replay_*.py`, `tests/test_build_replay_package.py`,
`backend/tests/test_replay.py` — 123 tests en la suite completa de
`backend/tests`; `frontend`: 147 tests en 22 archivos, incluidos los 4 de
`HistoricalReplayPage.test.tsx`); las marcadas **[prevista]** siguen sin
escribirse. El paquete real vigente es
`replay_packages/base-seed4-1157696b7b-v2/` (`_v1` se conserva, no se usa).

| Requisito | Prueba | Evidencia | Condición que la afecta |
|---|---|---|---|
| RH-01 — identidad duplicada vs. colisión de fecha objetivo, con normalización de fecha | **[implementada]** `test_duplicated_full_identity_is_rejected`, `test_equivalent_date_representations_are_treated_as_the_same_identity`, `test_distinct_runs_sharing_target_timestamp_is_not_treated_as_duplicate` (`tests/test_historical_replay_records.py`) | `DuplicateIdentityError` tipado; dos representaciones textuales equivalentes de la misma fecha se detectan como la misma identidad | Ninguna |
| RH-02 — predicción visible desde su origen, sin observación | **[implementada]** unidad: `tests/test_historical_replay_projection.py`; API: `backend/tests/test_replay.py::test_prediction_visible_from_origin_without_future_fields` | Diff campo por campo de la proyección; respuesta HTTP real verificada campo por campo | Ninguna |
| RH-03 — revelación condicionada a disponibilidad | **[implementada]** unidad: `tests/test_historical_replay_projection.py`; API: `backend/tests/test_replay.py::test_observation_revealed_exactly_at_target_date` | Proyecciones y respuestas HTTP comparadas; `target_observed=false` sigue siendo un caso construido (no real) | El caso `target_observed=false` sigue sin ejercitarse con datos reales de `base-seed4` (0/67 filas) |
| RH-04 — conservación exacta al mover el reloj | **[implementada]** unidad: `tests/test_historical_replay_projection.py`; API: `backend/tests/test_replay.py::test_rewinding_hides_the_observation_again`, `test_original_package_files_are_never_modified_by_the_api` | Igualdad estructural de valores revelados dos veces; hashes de los archivos del paquete idénticos antes/después de varias solicitudes | Ninguna |
| RH-05 — estados unificados de medición y ausencia de comparación inválida | **[implementada]** `tests/test_historical_replay_imputation_markers.py`, `tests/test_historical_replay_observations.py`, `tests/test_historical_replay_history_state.py`; API: `medicion_original.estado` expuesto en `backend/tests/test_replay.py::test_observation_revealed_exactly_at_target_date`; estado por fila del historial pre-corte expuesto en `GET /replay/history` (`backend/tests/test_replay.py::test_history_rows_expose_estado_and_causa`, `test_history_estado_becomes_no_determinado_under_imputation_source_drift`) | Estados exhibidos y distinguidos explícitamente en ambos endpoints; ninguna comparación fabricada cuando falta `y_true`; `soil_moisture` sigue siendo siempre el valor crudo original (nunca sustituido), el valor imputado se expone solo en el campo derivado separado `valor_imputado` | `sin_dato_en_fuente`/`no_determinado` con datos reales de `base-seed4` solo se ejercitan de forma sintética (vía drift forzado en el test), porque el paquete real `base-seed4-1157696b7b-v2` no tiene huecos genuinos en el rango replayado |
| RH-06 — trazabilidad vía run padre, hash de ejecución, contrastada contra metadatos capturados | **[implementada]** `tests/test_historical_replay_package_loader.py` (procedencia), `backend/tests/test_replay.py::test_candidate_endpoint_reports_authorized_run_and_disclaimers` (expuesta por la API) | Manifiesto real con `dataset_sha256=121697dd...`, `commit_sha=2a40ee68...`; respuesta HTTP con `run_id`/`experiment_id`/`config_name` | Ninguna para `base-seed4` |
| RH-07 — feedback separado, solo tras revelación | **[implementada]** `tests/test_historical_replay_feedback.py` (7 tests); API: `backend/tests/test_replay.py::test_feedback_rejected_before_reveal`, `test_feedback_registered_after_reveal_is_visible_and_isolated`, `test_feedback_hidden_again_after_rewinding_but_not_deleted`, `test_feedback_rejects_unknown_prediction_identity`; frontend: `ReplayFeedbackForm.tsx` habilitado solo tras revelación, verificado también en navegador real (`paso4-interfaz-feedback.md`) | `ReplayFeedbackStore` (JSON-lines, un archivo por `package_id`, en `replay_feedback/`); `registered_at`/`simulated_at` separados; registro real capturado en navegador (`replay_feedback/base-seed4-1157696b7b-v2.jsonl`) | Ninguna |
| RH-08 — estados con causa | **[implementada]** excepciones tipadas del lector y de `feedback.py` con mensaje exacto; a nivel API, errores HTTP con `detail` claro; a nivel interfaz, estados de carga/error/no-disponible/observación-no-disponible explícitos (`HistoricalReplayPage.tsx`); `GET /replay/history` expone `causa` concreta por fila cuando `estado != "medida"` (`backend/tests/test_replay.py::test_history_rows_expose_estado_and_causa`) | Mensajes de excepción, respuesta HTTP y estado de UI con causa concreta; causa explícita también por fila del historial pre-corte | El frontend (`HistoricalReplayPage.tsx`) todavía no consume `causa`/`estado` por fila del historial — solo el backend los expone; no se rediseñó la UI en este cambio |
| RH-09 — marca de reproducción retrospectiva y distinción de afirmaciones | **[implementada]** API: `backend/tests/test_replay.py::test_candidate_endpoint_reports_authorized_run_and_disclaimers`; interfaz: mensaje fijo visible en toda la pantalla (`HistoricalReplayPage.tsx`), verificado en navegador real | Respuesta HTTP con los tres disclaimers explícitos; captura real de la interfaz | Ninguna |
| RH-10 — reproducibilidad y predicción seguida | **[implementada]** backend: orden cronológico estable, API determinística sin estado; frontend: selección determinística inicial (primer origen de `GET /replay/predictions`) y `selectedOrigin` mantenido fijo en el estado de React al avanzar el reloj — probado (`HistoricalReplayPage.test.tsx`) y verificado en navegador real (avanzar 3 días sin que cambie la predicción seguida) | Orden estable; estado de React que no se resetea con el reloj; captura real | `prediccion_seleccionada_id` como concepto de **API** no existe — la selección vive enteramente en el estado del cliente, decisión de diseño del Paso 4, no una limitación no resuelta |
| RH-11 — elegibilidad temporal + identidad de modelo, **admisión corregida en el Paso 3** | **[implementada]** temporalidad: `tests/test_historical_replay_package_loader.py`, `tests/test_historical_replay_records.py`; identidad de modelo: `tests/test_historical_replay_admission_policy.py`, `tests/test_historical_replay_package_loader.py::test_unknown_candidate_is_rejected_even_if_everything_agrees_internally`, `tests/test_build_replay_package.py` (ambos extremos: lector y constructor) | Excepciones tipadas con el dato exacto; política externa (`historical_replay.admission_policy.ADMITTED_CANDIDATES`) verificada por el lector contra `run_metadata.json` y por el constructor antes de descargar artefactos | La política es una lista manualmente verificada, explícitamente no genérica — un candidato futuro requiere una revisión de código equivalente y editar `admission_policy.py`, no un registro extensible |
| RH-12 — vinculación cruzada de observación | **[implementada]** unidad: `tests/test_historical_replay_observations.py`; API: `link_observation` cableado en `backend/app/routers/replay.py::get_prediction`, usando `dataset_name`/`expected_dataset_name` ambos del propio manifiesto del paquete (nunca de parámetros del cliente) | `CrossSeriesObservationError`/`ObservationConsistencyError` con el dato exacto; verificado en `backend/tests/test_replay.py::test_observation_revealed_exactly_at_target_date` (estado `"medida"` real) | Un escenario de cross-series real a nivel API (dos datasets distintos) no se ejercita — el paquete único autorizado siempre es autoconsistente; el caso está cubierto a nivel unitario |
| RH-13 — separación de umbrales | **[implementada]** valores reales verificados en el manifiesto | Manifiesto real (`replay_packages/base-seed4-1157696b7b-v2/manifest.json`) | Ninguna |

## Defecto de admisión encontrado y corregido en el Paso 3

`_verify_admission_contract` (Paso 2) tomaba `verified_candidates` del
mismo manifiesto que estaba validando: un candidato arbitrario podía
admitirse a sí mismo con solo incluirse en su propia lista.
`build_replay_package.py` generaba además esa autodeclaración para
cualquier `run_id_child` recibido como argumento de línea de comandos, sin
restringirla al candidato realmente revisado.

Corrección: política de admisión mantenida **fuera** del paquete, en código
versionado (`src/historical_replay/admission_policy.py`), con un único
candidato hardcodeado — no un registro extensible ni un sistema general de
firmas. Se corroboraron los valores dados (experimento 4, run hijo/padre,
`base-seed4`, semilla 4, commit `2a40ee68...`, `dataset_sha256=121697dd...`)
contra `paso1-revision-dirigida.md` antes de incorporarlos: **sin
discrepancias**. Aplicada tanto en el lector (`_verify_admission_policy`,
sourced desde `run_metadata.json`, no desde `manifest["candidate"]` ni
`manifest["admission_contract"]`) como en el constructor
(`build_package` llama a `verify_admitted(...)` antes de descargar ningún
artefacto). Prueba central:
`test_unknown_candidate_is_rejected_even_if_everything_agrees_internally`
— un manifiesto cuyo `admission_contract`, `candidate` y `run_metadata.json`
concuerdan perfectamente entre sí, pero describen un run que no es el
admitido, se rechaza igual.

## Correcciones de regresión acumuladas (Paso 2 + Paso 3)

Ver `paso2-correccion-validaciones.md` para el detalle completo del Paso 2
(fallback de hash eliminado, `baselines` inmutable, identidad por fila no
sustituible, validación estricta de tipos, fechas normalizadas,
`run_metadata.json` contrastado, inventario de archivos). El Paso 3 agrega
la corrección de admisión descrita arriba como la más significativa de esta
matriz — cierra una vía de autoacreditación trivial que ninguna prueba
anterior ejercitaba.

## Incertidumbre de regresión cerrada en el Paso 4

El Paso 3 dejó dos hallazgos sin resolver: `test_forecast.py::test_run_forecast_returns_verdicts`
fallando, y `test_producer_v2_emission.py` excluido por una dependencia de
test ausente. El Paso 4 repuso las fixtures faltantes
(`tests/test_operational_inference.py`, `tests/test_operational_run.py`) y
aisló el tracking de MLflow (`MLFLOW_TRACKING_URI=sqlite:///...`, patrón ya
usado por `backend/tests/test_lineage.py`). Con ambas correcciones, **117 →
123 tests de `backend/tests` pasan, 0 fallos** (el número creció porque
esta pasada también agregó los tests nuevos de feedback/orígenes). Causa
raíz identificada con evidencia directa: el contenedor compartido
`aai-hydric-stress-backend-1` (en ejecución hace más de 2 días, con
actividad real ajena a esta tarea) ya tenía registrado en su MLflow
ambiental un modelo `alerting_ui_recalibrated_model__sensor-a` con
`trained_through=2026-09-13` — muy posterior a cualquier fecha del dataset
de test (que termina en 2024-12-31) — por lo que el `test` split de
`execute_configured_pipeline` quedaba vacío (`skip_fit=True`, filtro
`timestamp > trained_through`). Confirmado por comparación directa bajo
condiciones equivalentes: mismo código (`git diff` contra el commit base de
la rama, vacío para todos los archivos involucrados), mismo test, mismo
dataset — con tracking aislado, pasa; con el registro ambiental
preexistente, falla. No es una regresión de este *change*.

## Bloqueos materiales vs. limitaciones (separados, por instrucción explícita)

**Bloqueos materiales sobre el candidato `base-seed4`: ninguno.** Todas las
comprobaciones de procedencia, temporalidad, perturbación y admisión
(`design.md` §2.a–§2.c) permanecen resueltas con evidencia exacta y ahora
verificables automáticamente, tanto por el lector como por la API.

**Limitaciones compatibles con una demostración correctamente descrita (no
bloqueantes, deben disclosarse siempre):**

- `y_proba` sin evidencia de calibración (permanente); la API la omite por
  completo de toda respuesta, en vez de exponerla con advertencia — decisión
  explícita del Paso 3 para esta primera API de demostración, mantenida en
  el Paso 4 (la interfaz tampoco la muestra).
- `target_observed=false` y sus estados de medición asociados
  (`sin_dato_en_fuente`, `no_determinado`) están implementados y probados
  con casos construidos, pero ningún ejemplo real de `base-seed4` los
  ejercita (0/67 filas con `target_observed=false`).
- El supuesto de disponibilidad diaria de insumos crudos sigue siendo un
  supuesto documentado del protocolo v3, no verificado por fila — distinto
  del filtrado temporal de la interfaz/API (RH-09), que sí es verificable
  por test. Probar uno no prueba el otro.
- La política de admisión (RH-11) es una lista manualmente verificada,
  explícitamente no genérica — un candidato futuro requiere una revisión de
  código equivalente y editar `admission_policy.py`.
- El historial pre-corte (`GET /replay/history`) todavía no distingue
  `medida`/`imputada`/`no_determinado` por fila — solo el valor numérico o
  `null`. La medición del objetivo ya revelado sí distingue estos estados.
- Verificación de interfaz realizada contra una instancia Docker aislada y
  descartable de la misma imagen del backend, no contra el contenedor
  compartido — documentado explícitamente en `paso4-interfaz-feedback.md`,
  junto con el hallazgo de que el contenedor compartido tiene su propio
  MLflow ambiental con estado real preexistente ajeno a esta tarea.

Ninguna de estas limitaciones se resuelve declarándola "No disponible" sin
más ni convirtiéndola en limitación permanente sin haber intentado
resolverla primero.

## Cierre funcional de la demo (Paso 4.1)

Detalle completo en `paso4-1-cierre-demo.md`. Resumen de lo corregido:

- **Aislamiento de estado real, no solo aparente.** El `requestKey` de texto
  `origen|fecha` del Paso 4 identificaba una consulta, pero se repetía en
  una navegación A→B→A: la segunda consulta a "A" y la primera compartían
  la misma clave, así que una respuesta tardía de la primera podía pasar el
  guardado de igualdad y pisar el estado de la segunda. Corregido con un
  contador de generación monotónico (`generationRef`) que nunca se repite.
  Además, el estado anterior (predicción/historial/feedback/errores) ahora
  se limpia de forma **síncrona** al cambiar de selección, no solo se
  reemplaza cuando la nueva respuesta llega — antes, el resultado del corte
  previo permanecía visible durante toda la carga del nuevo. Una escritura
  de feedback (`createFeedback`) iniciada para una selección y resuelta
  después de navegar a otra ya no puede poblarla (mismo mecanismo de
  generación). Probado con 8 pruebas de promesas controladas
  (`HistoricalReplayPage.test.tsx`).
- **Defecto real en la condición de habilitación del formulario.**
  `revealed = predictionStatus === "ready" && prediction?.target_observed !== undefined`
  habilitaba el formulario también cuando `target_observed === false` (el
  objetivo nunca maduró), no solo cuando había una observación real que
  comparar. Corregido a `prediction?.target_observed === true`. Probado en
  `HistoricalReplayPage.test.tsx::does not show the feedback form when
  target_observed is false`.
- **Errores de historial/feedback ya no se confunden con "sin datos".**
  Antes, un fallo HTTP en `getHistory`/`getFeedback` se convertía en el
  mismo estado que una respuesta vacía exitosa (`catch` seteaba `[]`). Ahora
  son estados distintos (`loading`/`error`/`ready`); un error de feedback no
  habilita silenciosamente el formulario de alta como si se hubiera
  confirmado la ausencia de un registro previo.
- **Lenguaje corregido, verificado contra la evidencia documentada antes de
  escribirlo.** `manifest.label_rule.rule ==
  "observed_value_at_t_plus_h_less_than_frozen_threshold"` (verificado en
  `replay_packages/base-seed4-1157696b7b-v2/manifest.json` antes de traducirlo,
  no inventado): clase 1 = "por debajo del umbral de humedad", clase 0 = "no
  inferior al umbral de humedad". Expuesto por la API
  (`ReplayCandidateInfo.regla_etiqueta`); el backend rechaza con 500
  cualquier regla no reconocida en `_LABEL_RULE_OPERATORS` en vez de
  inventar un texto genérico.
- **`split_date` vs. fecha máxima de entrenamiento, verificadas por
  separado.** `effective_configuration.json::training_dates` tiene como
  máximo `2024-10-15`, cuatro días antes de `split_date=2024-10-19`: no son
  la misma fecha en este candidato. Antes la ficha de trazabilidad solo
  mostraba `split_date` bajo la etiqueta "Corte de entrenamiento", lo que
  invitaba a leerla como si fuera la última fecha de entrenamiento. Ahora
  `ReplayEvidenceCard` expone ambas por separado
  (`split_date`/`training_max_date`), y el frontend las etiqueta "Corte de
  partición (train/test)" y "Última fecha realmente usada para entrenar".
  Probado en `test_historical_replay_package_loader.py` y
  `backend/tests/test_replay.py::test_candidate_includes_expandable_evidence_card`.
- **Selector operativo separado.** El selector "sensor-a" y los controles
  operativos del formulario de sensor (que no gobiernan este recorrido)
  ahora se ocultan explícitamente en la ruta `#reproduccion-historica`
  (`App.tsx`).
- **Ejes legibles.** El gráfico de historial ahora dibuja ejes con fechas y
  humedad en m³/m³, además de la leyenda textual ya existente
  (`MoistureHistoryChart.tsx`).
- **Arranque reproducible.** `scripts/demo_replay_up.sh`/`demo_replay_down.sh`:
  puertos y directorio de feedback aislados por sesión (nunca sobrescriben
  sesiones anteriores), CORS configurado por `CORS_EXTRA_ORIGINS` (variable
  de entorno agregada a `backend/app/main.py`, no una edición manual de la
  lista de orígenes en cada sesión), el paquete científico se monta sin
  modificarse, y solo se detienen los procesos que la propia sesión
  arrancó.

Verificación en navegador real repetida con el código corregido (misma
disciplina de contenedor descartable, nunca el compartido): antes de
revelar → revelado con discrepancia real (`y_pred=0` vs. `y_true=1`,
`medicion_original=0.279` m³/m³) → feedback registrado
(`rechazada`, observación real) → retroceso oculta observación y feedback
sin borrar el registro persistido
(`replay_feedback/demo-session-browsercheck/base-seed4-1157696b7b-v2.jsonl`).
Capturas en `openspec/scientific-closure/causal-historical-replay-2026-09-22/paso4-1-capturas/`.

## Cierre de dos pendientes concretos (Paso 4.1.1)

Detalle completo en `paso4-1-1-cierre.md`. Dos correcciones reales:

1. La "limpieza síncrona antes del render" que este mismo documento describía
   arriba corría en realidad dentro de un `useEffect` (efecto pasivo, posterior
   al render) — no era la garantía que se afirmaba. Corregido con un filtro
   puro de selección vigente (`selectionScope.ts`), verificado con 5 pruebas
   unitarias directas más una prueba de integración que deja las promesas de
   la nueva selección colgadas para siempre y confirma que ningún dato de la
   selección anterior queda visible. Al implementar la limpieza al desmontar
   pedida en esta misma corrección, se introdujo y luego se encontró (en un
   navegador real, no por ningún test) un defecto de `StrictMode`: una guarda
   `mountedRef` que solo se ponía en `false` en la limpieza, sin reafirmar
   `true` en el montaje, quedaba permanentemente bloqueada tras el doble
   montaje que React hace a propósito en desarrollo — corregido y cubierto
   con una prueba dirigida que reproduce el defecto en RED antes de la
   corrección.
2. Los scripts de arranque del Paso 4.1 nunca se habían ejecutado de verdad
   (asumían Python/Node locales, ausentes en este host). Reescritos para
   orquestar los dos contenedores Docker desechables ya verificados
   funcionando en el Paso 4, y ejecutados esta vez tal cual, dos veces, con
   evidencia real: `sesion-a` (cambio de origen, feedback registrado) →
   detenida → `sesion-b` (vacía, arrancada en puertos distintos) → feedback
   de `sesion-a` preservado en disco y ausente en `sesion-b`. Un defecto real
   del propio chequeo de disponibilidad (`curl -f` reportando fallo pese a un
   200 real recibido) se encontró y corrigió al ejecutar los scripts por
   primera vez.

Además, se retracta una afirmación del cierre anterior: "el backend ya cubre
la concurrencia de `ReplayFeedbackStore` a nivel de archivo" no está
respaldada por ningún test — no existe ninguna prueba de escritura
concurrente. No se afirma que esté resuelta ni cubierta; solo que no se
probó, en ningún sentido.
