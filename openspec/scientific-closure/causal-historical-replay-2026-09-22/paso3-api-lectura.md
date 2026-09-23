# PASO 3 — Admisión del candidato y API de reproducción histórica de solo lectura

Fecha: 2026-09-23.
Rama `feat/causal-historical-replay`, worktree
`C:\Repo\AAI_Hydric_Stress_causal_historical_replay`. Continúa
`paso2-correccion-validaciones.md`. No se amplió el alcance científico, no
se ejecutó ningún modelo, no se recalculó ninguna métrica, no se accedió al
holdout v4, no se modificó gobernanza ni evidencia científica. No se hizo
commit, push, PR ni merge.

## Aislamiento

Se usó el mismo directorio aislado del Paso 2 (`/tmp/hr_workspace`), ahora
con una copia completa y actualizada de `src/` (no solo `historical_replay/`)
para poder importar `backend/app/main.py` con todos sus routers existentes
sin depender del `/workspace/src` del contenedor — que resultó ser una
imagen desactualizada, sin `data_ingestion.catalog`/`data_ingestion.history`/
`human_feedback.operational_repository` (confirmado al intentar importar la
app completa). No se escribió nada en `/workspace/src` ni en `/workspace/backend`
del contenedor activo; se copió `backend/` completo (con las ediciones de
este paso) a `/tmp/hr_workspace/backend`, y `pytest` lo descubre gracias a
`backend/conftest.py`, ya existente, que agrega `backend/` a `sys.path`
(mismo mecanismo que usan `backend/tests/test_lineage.py` y análogos). No se
reinició ni se modificó ningún servicio.

## 1. Corrección del defecto de admisión

**Defecto confirmado, tal como fue identificado en la consigna:**
`_verify_admission_contract` (Paso 2) leía `verified_candidates` del mismo
manifiesto que estaba validando — un candidato arbitrario pasaba ese
control con solo incluirse en su propia lista.
`scripts/build_replay_package.py` generaba además esa declaración de
revisión manual para el `run_id_child` recibido como argumento de línea de
comandos, sin restringirla al candidato realmente revisado.

**Corroboración de los valores dados** (antes de incorporarlos, tal como
pide la consigna) contra `paso1-revision-dirigida.md` y el manifiesto real
ya existente:

| Campo | Valor dado | Fuente ya registrada | Coincide |
|---|---|---|---|
| experimento | `4` | `paso1-revision-dirigida.md` §1, §2.1 | Sí |
| run hijo | `1157696b7bb941e394c5af530c762b07` | ídem | Sí |
| run padre | `6d516bb9f778450f8fbe2e5492818e57` | ídem | Sí |
| configuración/semilla | `base-seed4` (`config_name="base"`, `seed=4`) | ídem | Sí |
| commit de ejecución | `2a40ee68c52d2eb5e2040a36b1029f756f9c048a` | `paso1-revision-dirigida.md` §2.2 | Sí |
| `dataset_sha256` | `121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e` | `paso1-revision-dirigida.md` §2.1 | Sí |

**Sin discrepancias.** Ningún valor se corrigió por inferencia porque
ninguno lo requirió.

**Corrección implementada:** `src/historical_replay/admission_policy.py`,
nueva — política de admisión mantenida **fuera** del paquete, en código
versionado del proyecto: una tupla con un único `AdmittedCandidate`
hardcodeado (no un registro extensible ni un sistema general de firmas), y
`verify_admitted(...)` que exige coincidencia exacta de los siete campos
(no solo de `experiment_id`/`run_id_child`).

- **Lector** (`src/historical_replay/package_loader.py`): se eliminó
  `_verify_admission_contract` (leía el manifiesto). La nueva
  `_verify_admission_policy(run_metadata)` se ejecuta inmediatamente después
  de leer `run_metadata.json` y **antes** de `_verify_parent_child_metadata`
  — fuente exclusiva: los campos capturados de MLflow en `run_metadata.json`
  (`child.experiment_id`, `child.run_id`, `parent.run_id`,
  `child.params.config_name`/`seed`, `parent.params.commit_sha`/`dataset_sha256`),
  nunca `manifest["candidate"]` ni `manifest["admission_contract"]`.
- **Constructor** (`scripts/build_replay_package.py`): `build_package` llama
  a `verify_admitted(...)` con los valores efectivamente descubiertos del
  run (vía `client.get_run`/tags/params) **antes** de crear el directorio
  temporal y antes de descargar ningún artefacto. El bloque
  `admission_contract` del manifiesto ahora se arma a partir del
  `AdmittedCandidate` ya verificado (`admitted.note`,
  `admitted.model_identity_verified_by`), nunca reconstruido a mano para el
  argumento recibido.

**Prueba central** (`tests/test_historical_replay_package_loader.py::test_unknown_candidate_is_rejected_even_if_everything_agrees_internally`):
un manifiesto cuyo `candidate`, `admission_contract.verified_candidates` y
`run_metadata.json` concuerdan perfectamente entre sí, pero describen un
`run_id_child` que no es el admitido, se rechaza igual —
`AdmissionPolicyError`. Pruebas adicionales para el constructor
(`tests/test_build_replay_package.py`, con un cliente MLflow simulado, sin
red): rechazo antes de cualquier descarga para un run nunca revisado, y
rechazo cuando el `commit_sha` efectivamente descubierto no coincide con la
política aunque el `(experiment_id, run_id_child)` sí coincida.

Se verificó que **el paquete real (`replay_packages/base-seed4-1157696b7b-v2/`)
sigue cargando sin cambios** bajo la política corregida — no fue necesario
reconstruirlo.

## 2. Endpoints y contratos

Router nuevo `backend/app/routers/replay.py`, registrado en `main.py`.
Apagado por defecto (`HISTORICAL_REPLAY_ENABLED`, `is_historical_replay_enabled`,
mismo patrón que `PRODUCER_V2_ENABLED`); habilitarlo no altera nada
existente. Carga el paquete exclusivamente desde
`get_historical_replay_package_dir()` (`HISTORICAL_REPLAY_PACKAGE_DIR` o,
por defecto, `replay_packages/base-seed4-1157696b7b-v2/` del propio
repositorio) — mismo patrón que `get_producer_bundle_root`; el cliente
nunca puede indicar una ruta, un paquete ni un run.

| Endpoint | Contrato |
|---|---|
| `GET /replay/candidate` | Experimento/run/config/semilla, `horizon_days`, `periodo_inicio`/`periodo_fin` (rango real del recorrido), `limitaciones` (las del manifiesto), `disclaimers` (reproducción retrospectiva, proxy estadístico relativo, utilidad agronómica no demostrada). |
| `GET /replay/predictions/{timestamp_origen}?simulated_date=...` | Antes del origen: `404`. Desde el origen: `timestamp_origen`, `target_timestamp`, identidad de trazabilidad, `disclaimers`, `y_pred` — sin `target_observed`/`y_true`/`coincide`/`medicion_original`, **ausentes del JSON, no `null`** (`response_model_exclude_none=True`). Desde la fecha objetivo (si `target_observed=true`): agrega los cuatro campos, con `medicion_original` resuelto por `link_observation` contra el dataset del propio paquete cargado (nunca dos nombres provistos por el cliente). `y_proba` nunca se expone. |
| `GET /replay/history?simulated_date=...` | Filas `{fecha, soil_moisture}` hasta `simulated_date` inclusive, vía `historical_replay.history_view.filtered_history` — nunca el `DataFrame` completo. |

Errores: identidad desconocida → `404`; predicción no visible aún (origen
futuro) → `404` con mensaje distinto; paquete inválido, no admitido, o
inconsistente → `503` (la carga falla en `get_historical_replay_package`,
que envuelve cualquier excepción tipada del lector); feature flag apagado →
`404` "Not Found" (mismo patrón que `require_producer_v2_enabled`). Ninguna
de estas condiciones se sustituye por un valor estimado.

## 3. Comandos y resultados de pruebas

```
python -m pytest tests backend/tests/test_replay.py -q
```

Resultado: **79 passed** (68 de `historical_replay`/`build_replay_package`
del Paso 2 corregido + 11 nuevas de la API). Se ejecutó además el resto de
`backend/tests` (excluyendo `test_producer_v2_emission.py`, que falla por
una dependencia cruzada de módulos de test ajena a este cambio —
`tests.test_operational_inference`, inexistente en esta copia aislada de
`tests/`, no relacionada con `historical_replay`) para descartar
regresiones en los routers existentes:

```
python -m pytest backend/tests -q --ignore=backend/tests/test_producer_v2_emission.py
```

Resultado: **109 passed, 1 failed**
(`test_forecast.py::test_run_forecast_returns_verdicts`). Investigado
brevemente: no relacionado con este cambio (no se tocó `forecast.py` ni
`predictive_modeling`); consistente con datos de fixture incompletos en
esta copia aislada del entorno (`/tmp/hr_workspace/data` solo tiene el
dataset consolidado, no el resto de `data/`), no con una regresión
introducida aquí. No se investigó más a fondo por estar fuera de alcance de
este paso — se declara explícitamente, no se oculta.

Controles de calidad (mismo `pyproject.toml` del repositorio):

```
python -m ruff check src/historical_replay backend/app tests backend/tests/test_replay.py scripts/build_replay_package.py
python -m black --check src/historical_replay backend/app tests backend/tests/test_replay.py scripts/build_replay_package.py
```

Resultado: limpios tras corregir un import desordenado, una línea larga y
un import sin usar.

**Hallazgo corregido durante la verificación, no antes de ella:** al generar
el ejemplo de la sección 4, la primera versión de `GET /replay/predictions`
devolvía `target_observed`/`y_true`/`coincide`/`medicion_original` como
`null` explícito en el JSON antes de la fecha objetivo — Pydantic serializa
los campos opcionales como `null` por defecto, no los omite. Esto violaba
la consigna ("ni siquiera como información derivada que revele
anticipadamente el resultado" / RH-02: "el campo está ausente... no
enmascarado"). Corregido con `response_model_exclude_none=True` en ese
endpoint; las pruebas se endurecieron para exigir ausencia real de la clave
(`forbidden not in body`), no solo `body[forbidden] is None`. Se registra
este hallazgo explícitamente porque se detectó generando evidencia real,
no por una revisión de código aislada — es exactamente el tipo de defecto
que una inspección manual del código podría no notar.

## 4. Ejemplo real: el mismo pronóstico antes y después de revelar la observación

Candidato `base-seed4`, predicción con origen `2024-10-19`
(`target_timestamp=2024-10-22`).

**`GET /replay/predictions/2024-10-19?simulated_date=2024-10-21`** (un día
antes del objetivo):

```json
{
  "timestamp_origen": "2024-10-19",
  "target_timestamp": "2024-10-22",
  "experiment_id": "4",
  "run_id": "1157696b7bb941e394c5af530c762b07",
  "config_name": "base",
  "seed": 4,
  "horizon_days": 3,
  "disclaimers": {
    "reproduccion_retrospectiva": true,
    "proxy_estadistico_relativo": true,
    "utilidad_agronomica_demostrada": false
  },
  "y_pred": 0
}
```

**`GET /replay/predictions/2024-10-19?simulated_date=2024-10-22`** (fecha
objetivo):

```json
{
  "timestamp_origen": "2024-10-19",
  "target_timestamp": "2024-10-22",
  "experiment_id": "4",
  "run_id": "1157696b7bb941e394c5af530c762b07",
  "config_name": "base",
  "seed": 4,
  "horizon_days": 3,
  "disclaimers": {
    "reproduccion_retrospectiva": true,
    "proxy_estadistico_relativo": true,
    "utilidad_agronomica_demostrada": false
  },
  "y_pred": 0,
  "target_observed": true,
  "y_true": 1.0,
  "coincide": false,
  "medicion_original": {
    "estado": "medida",
    "valor": 0.2785114645957947
  }
}
```

`y_pred=0` no coincidió con `y_true=1.0` en este caso concreto
(`coincide: false`) — un ejemplo real de discrepancia, no elegido por
acertar; confirma además que no se "recorta" para mostrar solo aciertos.

## 5. Limitaciones y pendientes para la interfaz

- **No implementado (explícitamente, para la interfaz):**
  `prediccion_seleccionada_id` y la regla determinística de selección de la
  fecha inicial del recorrido (RH-10) — la API siempre requiere
  `timestamp_origen` explícito; quien "sigue" una predicción mientras el
  reloj avanza es responsabilidad de quien consuma la API.
  Feedback de demostración (RH-07): no implementado, fuera de alcance
  explícito. Frontend: no implementado.
- **Limitaciones permanentes, no bloqueantes, ya heredadas de pasos
  anteriores:** `y_proba` sin evidencia de calibración (aquí, directamente
  omitida de la respuesta); `target_observed=false` no ejercitado por
  ningún dato real de `base-seed4`; el supuesto de disponibilidad diaria de
  insumos crudos sigue sin verificación por fila.
- **No se declara terminada ninguna demo completa.** Esta entrega es una
  API de solo lectura verificada por pruebas automatizadas y un ejemplo
  real; no incluye interfaz, no persiste feedback, no se probó con un
  navegador ni con un cliente HTTP manual fuera de `TestClient`.

## Cierre

Diff de esta tarea: `src/historical_replay/admission_policy.py` (nuevo);
`src/historical_replay/package_loader.py`,
`scripts/build_replay_package.py` (corrección de admisión);
`backend/app/config.py`, `backend/app/dependencies.py`,
`backend/app/main.py` (dependencias/registro del router nuevo);
`backend/app/routers/replay.py`, `backend/app/schemas_replay.py` (nuevos);
`tests/test_historical_replay_admission_policy.py`,
`tests/test_build_replay_package.py` (nuevos);
`tests/test_historical_replay_package_loader.py` (test de admisión
actualizado, fixture ahora usa una copia del dataset real para poder pasar
la política); `backend/tests/test_replay.py` (nuevo). No se modificó
ningún artefacto científico original ni el paquete `replay_packages/base-seed4-1157696b7b-v2/`
(se verificó su hash antes/después de las pruebas de API). No se modificó
ningún otro worktree ni `/workspace/src`/`/workspace/backend` del
contenedor activo. No se instaló nada de forma persistente. No se hizo
commit, push, PR ni merge. Se detiene aquí para revisión.
