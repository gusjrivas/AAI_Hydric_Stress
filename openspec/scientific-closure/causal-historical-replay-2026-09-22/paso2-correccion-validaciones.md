# PASO 2 — Corrección de validaciones antes de exponer la API

Fecha: 2026-09-23.
Rama `feat/causal-historical-replay`, worktree
`C:\Repo\AAI_Hydric_Stress_causal_historical_replay`. Continúa
`paso2-paquete-lector.md`, corrigiendo el lector y el constructor ya
existentes — no se rehizo la arquitectura, no se amplió a otros candidatos,
no se ejecutó ningún modelo. No se implementó API ni frontend. No se hizo
commit, push, PR ni merge.

## Aislamiento (corregido respecto de la pasada anterior)

La pasada anterior copió el código a `/workspace/src/historical_replay` del
contenedor `aai-hydric-stress-backend-1` (backend activo). Esta pasada usa
en cambio un directorio independiente,
`/tmp/hr_workspace/src/historical_replay`, con
`PYTHONPATH=/tmp/hr_workspace/src:/workspace/src` — el segundo componente
solo para leer, nunca para escribir, las dependencias ya instaladas en la
imagen (`data_quality`, `data_ingestion`, `pandas`, `mlflow`, `pyarrow`).
`/workspace/src/historical_replay` (residuo de la pasada anterior) se
eliminó de la capa efímera del contenedor al empezar. No se reinició ni se
modificó ningún servicio; el contenedor sigue siendo el mismo, ya en
ejecución, de la arquitectura ADR-0004.

## 1. Procedencia histórica

- Se eliminó `historical_sha256 = expected_dataset_sha256 or actual_dataset_sha256`
  de `scripts/build_replay_package.py`. Ahora, si el run padre no declara
  `dataset_sha256`, la construcción se rechaza explícitamente
  (`ProvenanceMissingError`), sin sustituirlo por un hash calculado hoy.
- Se agregó `run_metadata.json` al paquete: metadatos mínimos verificables
  de ambos runs (`run_id`, `experiment_id`, `status`, `run_name`, `tags`
  —incluido `mlflow.parentRunId`—, `params`, `metrics`), capturados
  directamente de la API de MLflow al construir.
- El lector (`package_loader.py::_verify_parent_child_metadata`) ya no
  confía solo en lo que el manifiesto declara: contrasta
  `candidate.run_id_child/run_id_parent/experiment_id/config_name/seed` y
  `execution_identity.commit_sha` contra `run_metadata.json`, y exige
  `status == "FINISHED"` en ambos runs. Cualquier discrepancia produce
  `ParentChildInconsistencyError` con el campo exacto que no coincide.
- **Contrato de admisión explícito** (`admission_contract.verified_candidates`):
  esta versión no promete validar automáticamente la identidad de un modelo
  arbitrario (folds vs. modelo fijo) — declara qué candidatos fueron
  revisados manualmente y por qué (`model_identity_verified_by`, citando la
  revisión de código de `paso1-revision-dirigida.md` §2.2), y el lector
  rechaza (`AdmissionContractError`) cualquier candidato no listado ahí.

## 2. Inventario e integridad

- `_verify_file_integrity` ahora resuelve cada ruta con `_safe_join`, que
  rechaza (`InventoryError`) cualquier ruta que escape del directorio del
  paquete.
- Todo archivo que el lector efectivamente abre (`predictions.json`,
  `effective_configuration.json`, `run_metadata.json`, el dataset) pasa por
  `_require_inventoried`: si no figura en `manifest["files"]`, se rechaza
  antes de intentar leerlo.
- El hash histórico del dataset se contrasta ahora **tres veces**: contra la
  copia empaquetada (hash de custodia), contra `manifest.dataset.historical_sha256`,
  y contra `run_metadata.json::parent.params.dataset_sha256` — las tres
  deben coincidir.
- **Publicación validada:** `build_package` arma el paquete completo en un
  directorio temporal propio (`tempfile.mkdtemp`, hermano del destino final)
  y solo lo traslada (`Path.replace`, atómico) al `output_dir` si
  `load_package` lo carga sin error; si algo falla, el directorio temporal
  se borra y el destino final nunca se toca. No se sobrescribe ni se borra
  ningún paquete previo (`FileExistsError` si `output_dir` ya existe).

## 3. Temporalidad

- `training_dates` ausente, vacío o no siendo una lista se rechaza
  explícitamente (`TrainingDatesError`), igual que una fecha individual mal
  formada.
- Nueva comprobación: el origen de cada predicción debe ser igual o
  posterior al corte autorizado (`PredictionBeforeCutoffError`) — antes solo
  se verificaba la madurez de las fechas de *entrenamiento*, no el propio
  origen de las predicciones de *test*.
- Nueva comprobación de concordancia: `horizon_days`/`split_date` deben
  coincidir entre `manifest.temporal_semantics`,
  `effective_configuration.json::contract` y
  `run_metadata.json::parent.params` (`TemporalConcordanceError`).
- Las fechas se normalizan a `datetime.date` para toda comparación de
  identidad/orden/madurez — nunca se reescriben los JSON originales en
  disco. Dos representaciones textuales equivalentes de la misma fecha
  (`"2024-10-19"` vs. `"2024-10-19T00:00:00.000"`) ahora se detectan como el
  mismo identidad, no como predicciones distintas.
- Los registros se ordenan cronológicamente al construirse
  (`build_records`), para que una futura selección de fecha inicial (RH-10)
  no dependa del orden incidental de `predictions.json`.

## 4. Identidad y tipos

- `row.run_id` (o cualquier otro campo de identidad por fila) ya no puede
  sustituir silenciosamente al run/config/seed autorizado —
  `ForeignIdentityError` si entran en conflicto.
- Un campo de identidad requerido ausente ya no se convertía en el string
  literal `"None"` — `MissingIdentityError` explícito.
- Validación estricta agregada: `target_observed` debe ser un `bool` real
  (rechaza `"true"`, `1`, que antes pasaban por *truthiness*);
  `y_proba` numérico finito en `[0, 1]`; `y_pred`/`y_true` en `{0, 1}`;
  coherencia `target_observed` ↔ presencia de `y_true`; `horizon_days`
  positivo. Ninguno de estos casos corrige ni recalcula el valor archivado
  — solo rechaza.
- `HistoricalPredictionRecord.baselines` era un `dict` mutable dentro de un
  dataclass `frozen=True` — un dataclass congelado no protege un objeto
  anidado. Ahora es un `MappingProxyType` (inmutable de verdad); la
  proyección pública (`projection.py::project`) sigue devolviendo una copia
  independiente (`dict(record.baselines)`), verificado con un test que
  muta la vista y confirma que el registro interno no cambia.

## 5. Observaciones y derivados

- Nueva entidad `LinkedObservation` (`src/historical_replay/observations.py::link_observation`),
  que vincula el objetivo de una predicción con una medición de un
  dataset/serie declarado, rechazando (`CrossSeriesObservationError`): un
  nombre de dataset que no coincide con el declarado, una fecha objetivo
  ausente de la serie, y ambigüedad por fechas duplicadas. Detecta además
  una inconsistencia distinta (`ObservationConsistencyError`):
  `target_observed=true` sin valor crudo disponible en el dataset
  empaquetado.
- Nueva función `filtered_history` (`src/historical_replay/history_view.py`):
  historial de mediciones filtrado por el reloj simulado — nunca expone el
  `DataFrame` completo como si fuera una futura respuesta pública; las
  filas posteriores al reloj están ausentes, no solo ocultas.
- **Equivalencia de imputación documentada y verificada, no asumida:**
  `imputation_markers.py` ahora expone
  `verify_imputation_source_matches_verified_commit()`, que hashea el
  código fuente realmente importado de `data_quality.imputation`/
  `data_quality.temporal` y lo compara contra los hashes capturados al
  verificar (`git diff 2a40ee68c52d2eb5e2040a36b1029f756f9c048a HEAD --
  src/data_quality/imputation.py src/data_quality/temporal.py`, diff vacío,
  confirmado en esta pasada) — si el código cambiara sin actualizar esa
  verificación, `reconstruct_imputation_markers` falla explícitamente en
  vez de reutilizar en silencio una función que ya no es la misma.
- Test nuevo que distingue explícitamente el umbral de humedad
  (`label_rule.frozen_threshold=0.31678178906440735` m3/m3) de la regla de
  decisión del clasificador (`decision_rule.alert_threshold=0.5`) contra el
  manifiesto real — ya no se verifica solo por inspección manual.
- No se recalculó ninguna métrica ni se reemplazó ninguna etiqueta
  archivada en ningún punto de esta corrección.

## 6. Pruebas dirigidas

Se agregaron pruebas de regresión específicas para cada fallo pedido (hash
histórico ausente, identidad padre-hijo inconsistente, archivo omitido del
inventario, `training_dates` ausente/vacío, predicción anterior al corte,
identidad de fila ajena, booleano textual, probabilidad/clase inválida,
fechas equivalentes duplicadas, intento de mutación interna, observación
cruzada, historial futuro, separación de umbrales) — todas con excepciones
específicas, ninguna con `pytest.raises(Exception)` genérico.

Se agregó además una prueba que bloquea conexiones de red reales
(`monkeypatch.setattr(socket, "create_connection", ...)` que lanza si se
invoca) para probar la ausencia de red de forma más fuerte que solo quitar
`MLFLOW_TRACKING_URI`.

**Comando y resultado** (dentro del contenedor, aislado, `PYTHONPATH`
explícito):

```
python -m pytest /tmp/hr_workspace/tests -q
```

Resultado: **62 passed** (20 identidad/tipos, 9 proyección, 5 imputación
—incluida la verificación de equivalencia de fuente—, 6 observaciones, 3
historial filtrado, 19 paquete/lector).

Controles de calidad (`pyproject.toml` del propio repositorio, copiado al
directorio aislado para que `ruff`/`black` usen la configuración real del
proyecto, no los valores por defecto de las herramientas):

```
python -m ruff check src tests build_replay_package.py replay_projection_demo.py
python -m black --check src tests build_replay_package.py replay_projection_demo.py
```

Resultado: limpios tras corregir 3 líneas largas, un bloque de imports
desordenado y aplicar el formateo automático a 8 archivos — todos
sincronizados de vuelta a este worktree.

## 7. Aislamiento

Detallado arriba. Se verificó explícitamente, antes de empezar, que no
había ninguna escritura previa de esta sesión en `/workspace/data` (el
volumen del checkout principal, `C:\Repo\AAI_Hydric_Stress\data`, distinto
de este worktree) y se limpiaron los residuos de `/workspace/src`,
`/workspace/tests_replay` y `/workspace/scripts_replay` que había dejado la
pasada anterior en la capa efímera del contenedor (no persistida, no afecta
al host ni a la imagen).

## 8. Entrega

- `tasks.md` y `traceability.md` actualizados solo con lo efectivamente
  completado y probado en esta pasada (ver ambos archivos para el detalle
  exacto, incluida la lista de correcciones de regresión).
- **Paquete anterior conservado sin cambios:**
  `replay_packages/base-seed4-1157696b7b/` (`_v1`, sin `run_metadata.json`
  ni `admission_contract` — ya no es el que debe usarse, pero no se borró).
- **Nuevo paquete, formato v2:**
  `replay_packages/base-seed4-1157696b7b-v2/`
  (`schema_version=historical_replay_package_v2`), con copias fieles de los
  mismos artefactos científicos originales (`predictions.json`,
  `effective_configuration.json`, el dataset verificado por hash) y un
  manifiesto actualizado (`admission_contract`, `run_metadata.json` nuevo).
  Construido y publicado con `build_package` (validado antes de publicar,
  §2); recargado en un proceso nuevo tanto dentro del contenedor como desde
  la copia en este worktree, sin error, para confirmar que el round-trip
  `docker cp` no lo corrompió.
- Comando reproducible de demostración, verificado contra el paquete v2, sin
  ejecutar ningún modelo:

  ```
  python scripts/replay_projection_demo.py --package-dir replay_packages/base-seed4-1157696b7b-v2
  ```

  Salida real obtenida en esta pasada: la predicción
  (`timestamp_origen=2024-10-19`, `target_timestamp=2024-10-22`) se muestra
  sin `y_true`/`target_observed`/`baselines` un día antes del objetivo, y
  con esos tres campos revelados exactamente en la fecha objetivo.

## Limitaciones que persisten (no bloqueantes, ya documentadas en `traceability.md`)

- `y_proba` sin evidencia de calibración — permanente, redactado como "no
  acreditada para este run", sin afirmar imposibilidad por la fecha de
  incorporación del módulo de calibración.
- `target_observed=false` y los estados `sin_dato_en_fuente`/`no_determinado`
  de `link_observation`: implementados y probados con casos construidos,
  no ejercitados por ningún dato real de `base-seed4`.
- El contrato de admisión de identidad de modelo es una lista manualmente
  verificada, explícitamente no genérica — se documenta como límite de
  esta versión, no como pendiente oculto.
- Todo lo de API/interfaz/feedback sigue sin iniciar (fuera de alcance de
  este paso).

## Próxima tarea concreta

Sin cambios respecto de lo ya identificado: implementar el endpoint de
solo lectura que expone el recorrido (RH-10, selección determinística de
fecha inicial + `prediccion_seleccionada_id`), ahora sobre una base de
validaciones más sólida (`link_observation`, `filtered_history`,
`admission_contract` ya disponibles para que la API los use en vez de
tener que resolverlos de nuevo).

## Cierre

Diff de esta tarea: los archivos de código corregidos (`src/historical_replay/*.py`,
`scripts/build_replay_package.py`, `scripts/replay_projection_demo.py`,
`tests/test_historical_replay_*.py`, dos módulos nuevos —`observations.py`,
`history_view.py`— con sus tests), el nuevo paquete
`replay_packages/base-seed4-1157696b7b-v2/`, la actualización de
`tasks.md`/`traceability.md`, y este informe. El paquete `_v1` y los
informes de Pasos 0/1 no se modificaron. No se tocó ningún otro worktree ni
`/workspace/data`. No se instaló nada de forma persistente. No se hizo
commit, push, PR ni merge. Se detiene aquí para revisión.
