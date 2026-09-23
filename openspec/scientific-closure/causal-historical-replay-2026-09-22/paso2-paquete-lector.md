# PASO 2 — Paquete reproducible, lector y validaciones

Fecha: 2026-09-23.
Rama `feat/causal-historical-replay`, worktree
`C:\Repo\AAI_Hydric_Stress_causal_historical_replay`. Continúa
`paso1-revision-dirigida.md` sobre el mismo candidato fijado (no se sustituyó,
no se generalizó, no se inspeccionaron otros runs). Alcance autorizado:
escribir código, generar el paquete local y ejecutar pruebas dirigidas. No se
entrenó, no se infirió, no se recalculó ninguna métrica científica, no se
accedió al holdout C, no se implementó API, interfaz ni persistencia de
feedback. No se hizo commit, push, PR ni merge.

## Entorno de ejecución (nota necesaria)

Este worktree no tiene intérprete Python (confirmado ya en Paso 0). Para
escribir código con TDD real (RED antes de implementar) y para construir el
paquete, se usó el contenedor `aai-hydric-stress-backend-1`, que ya estaba en
ejecución (arquitectura real ADR-0004) — no se levantó ningún servicio nuevo.
Se instalaron **de forma efímera, solo en la capa de escritura del
contenedor** (no en el host, no en la imagen, no persistido): `pytest`,
`ruff`, `black` — necesarios para "ejecutar las pruebas dirigidas y los
controles de calidad exigidos por las instrucciones del repositorio", tal
como autoriza esta consigna. Esos paquetes desaparecen si el contenedor se
recrea; no se modificó el `Dockerfile` ni ninguna imagen.

Los archivos de este repositorio se sincronizaron al contenedor con
`docker cp` (solo a rutas efímeras: `/workspace/src`, que es una capa
*writable* no persistida del contenedor, y `/tmp/replay_build`), nunca al
volumen `/workspace/data` (montado desde `C:\Repo\AAI_Hydric_Stress\data`,
que pertenece al checkout principal, **no** a este worktree) — se verificó
explícitamente que ningún comando de esta sesión escribió ahí. El dataset
real se tomó siempre de la copia de este worktree
(`data/melchor_romero_2024_consolidado.parquet`), verificada por hash
(§2 más abajo), nunca del volumen del otro checkout.

Se detectó que `aai-hydric-stress-backend-1` (proyecto Compose
`aai-hydric-stress`, `MLFLOW_TRACKING_URI=http://mlflow:5000` interno) está
conectado a un servidor MLflow **distinto** del que expone el
`experiment_id=4` verificado en el Paso 1 (ese es el publicado en el puerto
5000 del host, de otro proyecto Compose). Se accedió al servidor correcto
vía `http://host.docker.internal:5000` desde dentro del contenedor — mismo
servidor que se consultó por `curl` desde el host en el Paso 1, confirmado
por los mismos valores exactos (`dataset_sha256`, `commit_sha`, métricas).
Esto se registra explícitamente porque podría inducir a error en una
continuación futura: el `MLFLOW_TRACKING_URI` por defecto de este contenedor
**no** es el servidor que contiene la evidencia de este candidato.

## 1. Archivos creados o modificados

Todo nuevo, ningún archivo existente modificado (fuera de la actualización de
`tasks.md`/`traceability.md`, ya documentales, del *change* de Paso 1):

- `src/historical_replay/__init__.py`
- `src/historical_replay/records.py` — `PredictionIdentity`,
  `HistoricalPredictionRecord`, `build_records` (RH-01, RH-11 horizonte).
- `src/historical_replay/projection.py` — `project()`, proyección pura
  (RH-02–RH-05).
- `src/historical_replay/imputation_markers.py` —
  `reconstruct_imputation_markers()` (RH-05, §6 de esta consigna).
- `src/historical_replay/package_loader.py` — `load_package()` y sus
  excepciones tipadas (`IntegrityError`, `ProvenanceError`,
  `TrainingMaturityError`, `UnsupportedManifestVersionError`) (RH-06, RH-11
  madurez).
- `scripts/build_replay_package.py` — script de construcción del paquete
  (I/O: MLflow + dataset local → paquete en disco).
- `scripts/replay_projection_demo.py` — comando reproducible de demostración
  (§ más abajo).
- `tests/test_historical_replay_records.py` (5 tests)
- `tests/test_historical_replay_projection.py` (8 tests)
- `tests/test_historical_replay_imputation_markers.py` (3 tests)
- `tests/test_historical_replay_package_loader.py` (7 tests)
- `replay_packages/base-seed4-1157696b7b/` — el paquete real construido
  (nueva ubicación, análoga en espíritu a `demo_sessions/<id>/`, dentro del
  worktree; no sobrescribe nada existente).
- `openspec/changes/add-causal-historical-replay/tasks.md`,
  `traceability.md` — actualizados solo con lo efectivamente completado.

## 2. Ubicación y contenido del paquete

`replay_packages/base-seed4-1157696b7b/`:

```
manifest.json
predictions.json                          (copia fiel del artefacto del run hijo)
effective_configuration.json              (copia fiel del artefacto del run hijo)
parent_run_params.json                    (params + metrics del run padre)
dataset/melchor_romero_2024_consolidado.parquet   (copia del dataset, verificada por hash)
derived/imputation_markers.parquet        (derivado: marcador <col>_imputado recomputado)
```

Ningún archivo de credenciales, ningún modelo `pickle`. `manifest.json` no
recalcula ni sobrescribe `y_true`/`y_proba`/`y_pred` — son los valores
archivados, copiados tal cual desde `predictions.json`.

## 3. Procedencia y hashes

- `candidate`: `experiment_id=4` (`hu7-controlled-daily-v3-formal`),
  `run_id_child=1157696b7bb941e394c5af530c762b07`,
  `run_id_parent=6d516bb9f778450f8fbe2e5492818e57`, `config_name=base`,
  `seed=4` — resuelto siguiendo `mlflow.parentRunId`, verificado contra el
  `experiment_id` esperado antes de construir nada (`build_package` detiene
  la construcción si no coincide, sin sustituir el candidato).
- `dataset.historical_sha256 = 121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e`
  — hash capturado por la canalización original en la ejecución
  (2026-09-05), tomado del parámetro `dataset_sha256` del run padre.
  `build_package` compara este valor contra el hash real del archivo
  provisto (`data/melchor_romero_2024_consolidado.parquet` de este worktree)
  **antes** de copiarlo al paquete, y se detiene con error si no coincidieran
  (no ocurrió: coinciden exactamente).
- `execution_identity.commit_sha = 2a40ee68c52d2eb5e2040a36b1029f756f9c048a`,
  `working_tree_status=""` — igual que en el Paso 1.
- **Hashes de custodia** (`files.*.custody_sha256`, en el manifiesto): SHA-256
  de cada archivo tal como quedó en el paquete al construirlo — distintos en
  propósito del `dataset_sha256` histórico (uno prueba integridad de la
  copia exportada; el otro prueba qué consumió el run en 2026-09-05). Se
  verificó el round-trip completo: se copió el paquete de vuelta a un
  directorio nuevo dentro del contenedor y `load_package` volvió a validar
  todos los hashes sin error.

## 4. Validaciones implementadas

- **Rechazo de identidad duplicada** (RH-01): `build_records` — probado.
- **Horizonte incompatible** (RH-11): fila cuyo
  `target_timestamp - timestamp != horizon_days` declarado — probado.
- **Madurez de etiquetas de entrenamiento respecto del corte** (RH-11):
  `_verify_training_maturity` en `package_loader.py` — probado, incluido el
  caso negativo (fecha de entrenamiento cuyo objetivo no madura antes del
  corte).
- **Integridad de archivos** (hash de custodia): `_verify_file_integrity` —
  probado con un archivo alterado después de calcular el manifiesto.
- **Consistencia del hash histórico del dataset vs. su copia empaquetada**:
  `_verify_dataset_provenance` — probado con una inconsistencia forzada.
- **Versión de manifiesto soportada**: `UnsupportedManifestVersionError` —
  probado.
- **Carga sin MLflow ni red**: confirmado estructuralmente (ningún módulo de
  `historical_replay` importa `mlflow`) y funcionalmente (`load_package`
  probado con `MLFLOW_TRACKING_URI` ausente y, en el contenedor, con un host
  de tracking inexistente — carga exitosa en ambos casos).

**No implementado en este paso** (ver `tasks.md`/`traceability.md` para el
detalle exacto, separado de lo anterior):

- Rechazo de "identidad de modelo ambigua" (RH-11): para `base-seed4` el
  modelo fijo se estableció por revisión de código (Paso 1), no por una
  regla automática y reutilizable del lector.
- Rechazo de vinculación cruzada de observación (RH-12): no existe todavía
  la entidad `ReplayObservation`; solo se construyó la predicción archivada.

Ninguna de estas dos ausencias se disfrazó de "No disponible" ni se declaró
resuelta — quedan explícitas como próximas tareas, no como limitaciones
permanentes ni como bloqueo del candidato.

## 5. Proyección temporal — comportamiento verificado

`historical_replay.projection.project(record, fecha_simulada)`:

| Caso | Resultado verificado |
|---|---|
| `reloj < origen` | predicción ausente de la respuesta (no solo oculta: no está) |
| `origen <= reloj < objetivo` | predicción visible (`y_proba`, `y_pred`, trazabilidad); `y_true`/`target_observed`/baselines ausentes |
| `reloj == objetivo` (igualdad) | observación revelada |
| Salto del reloj muy por encima del objetivo | misma revelación que avanzando día por día |
| `target_observed=false` (caso construido, no real en `base-seed4`) | solo el estado, sin comparación fabricada |
| Retroceso antes del objetivo | observación vuelve a ocultarse; el registro interno no cambia |
| Reavance tras un retroceso | misma revelación exacta que la primera vez |

No se filtra la fila completa solo porque el objetivo sea futuro (se
corrigió respecto del diseño del Paso 1). El registro interno
(`HistoricalPredictionRecord`) y el objeto público (el `dict` que devuelve
`project`) están separados: `project` nunca muta el registro.

## 6. Imputación

`reconstruct_imputation_markers` reproduce exactamente el orden del pipeline
original verificado en el Paso 1 (`validate_daily_series` seguido de
`interpolate_missing_causal`, sobre la serie completa de una sola vez, nunca
por partición train/test — así es como el código original la aplicaba,
confirmado en `architecture_integration/pipeline.py::prepare_daily_features`).
Se aplicó realmente sobre la copia del dataset ya verificada por hash dentro
del paquete, para las columnas `raw_input_features` del contrato
(`soil_moisture`, `solar_radiation`, `relative_humidity`), y el resultado
(`derived/imputation_markers.parquet`) se guarda separado del dataset
original (`dataset/`), identificado en el manifiesto como derivado
post-hoc, no persistido por la corrida original.

## 7. Comandos y resultados de pruebas

```
python -m pytest /workspace/tests_replay -q
```

Resultado: **23 passed** (5 identidad/duplicados, 8 proyección, 3
imputación, 7 paquete/lector). Se corrió también el suite completo junto
(no solo archivo por archivo) para descartar interferencia entre módulos.

Controles de calidad del repositorio (`pyproject.toml`: `ruff` con
`E,F,I,UP`, línea 100; `black`, línea 100):

```
python -m ruff check src/historical_replay scripts_replay tests_replay
python -m black --check src/historical_replay scripts_replay tests_replay
```

Resultado: ambos limpios tras dos correcciones (una línea larga en
`build_replay_package.py`, una importación sin usar en un test) y el
formateo automático de dos archivos con `black` — los archivos corregidos se
sincronizaron de vuelta a este worktree.

## 8. Precisiones documentales aplicadas

- La limitación de calibración se redactó como **"calibración no acreditada
  para este run"**, sin afirmar que la evaluación es imposible por la fecha
  de incorporación del módulo — esa fecha es contexto de por qué no hay
  evidencia, no una prueba de imposibilidad. Corregido en
  `scripts/build_replay_package.py::KNOWN_LIMITATIONS` y en el manifiesto
  real (se reconstruyó el paquete tras la corrección).
- Se mantienen distinguidos, en todo momento: (i) custodia e integridad del
  paquete (hashes de custodia, calculados al construirlo); (ii) evidencia
  temporal del backtest (hash histórico del dataset, madurez de
  entrenamiento, horizonte — propiedades del run ya ejecutado); (iii)
  filtrado del reloj de reproducción (propiedad de `project()`, código
  nuevo de este *change*, no del backtest original). Probar (iii) no prueba
  (ii): son afirmaciones independientes, verificadas por separado.
- No se modificó ningún capítulo anterior de la memoria. Esta entrega **no**
  es una demo completa: faltan API, interfaz y persistencia de feedback,
  explícitamente fuera de alcance de este paso.

## 9. Comando reproducible de demostración

```
python scripts/replay_projection_demo.py --package-dir replay_packages/base-seed4-1157696b7b
```

No ejecuta ningún modelo — solo carga el paquete y proyecta la misma
predicción (`timestamp_origen=2024-10-19`, `target_timestamp=2024-10-22`) un
día antes de su fecha objetivo y en la fecha objetivo misma. Salida real
obtenida en esta pasada (dentro del contenedor, paquete ya copiado al
worktree y verificado desde ahí):

```
--- proyeccion en 2024-10-21 (antes del objetivo) ---
{ "timestamp_origen": "2024-10-19T00:00:00.000", "target_timestamp": "2024-10-22T00:00:00.000",
  "y_proba": 0.44, "y_pred": 0, "experiment_id": "4",
  "run_id": "1157696b7bb941e394c5af530c762b07", "config_name": "base", "seed": 4 }

--- proyeccion en 2024-10-22 (fecha objetivo) ---
{ ...igual que arriba..., "target_observed": true, "y_true": 1.0,
  "baselines": { "persistence": 1, "majority_class": 0, "always_stress": 1 } }

campos revelados solo en la segunda proyeccion: ['baselines', 'target_observed', 'y_true']
```

## 10. Limitaciones pendientes

- Identidad de modelo ambigua (RH-11) y vinculación cruzada de observación
  (RH-12): no implementadas (§4).
- `target_observed=false` y el estado `no_determinado` de imputación: el
  comportamiento está implementado y probado con casos construidos, pero
  ningún ejemplo real de `base-seed4` los ejercita (0/67 filas con
  `target_observed=false`; el marcador de imputación siempre se recomputó
  con éxito para este dataset).
- Separación de umbrales (RH-13): verificada por inspección del manifiesto
  real; falta un test dirigido propio y aislado.
- Todo lo de API/interfaz/feedback (secciones 3–5 de `tasks.md`): sin
  iniciar, fuera de alcance de este paso.

## 11. Próxima tarea concreta

Implementar el endpoint de solo lectura que expone el recorrido (análogo a
`GET /lineage/{sensor_id}`) sobre el paquete ya construido y validado,
incluyendo la regla determinística de selección de fecha inicial (RH-10) y
`prediccion_seleccionada_id` separado de la fecha simulada — primer ítem no
tachado de `tasks.md` §3. Antes de eso, decidir si se resuelve primero el
rechazo de "identidad de modelo ambigua" (RH-11) como validación reutilizable
del lector, dado que hoy depende de una revisión manual de código no
repetible automáticamente para un candidato futuro.

## Cierre

Diff de esta tarea: los archivos listados en §1 (todos nuevos, salvo la
actualización de `tasks.md`/`traceability.md` del *change* de Paso 1) y este
informe. No se modificó ningún artefacto científico original (`predictions.json`,
`effective_configuration.json` y el dataset se copiaron, nunca se
sobrescribieron ni recalcularon). No se modificó ningún otro worktree ni el
volumen `/workspace/data` del checkout principal (verificado). No se
instaló nada de forma persistente (pytest/ruff/black quedaron solo en la
capa efímera del contenedor). No se hizo commit, push, PR ni merge. Se
detiene aquí para revisión.
