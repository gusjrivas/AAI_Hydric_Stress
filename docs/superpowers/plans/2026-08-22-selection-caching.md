# Selection Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evitar que `backend/app/pipeline.py::execute_configured_pipeline` re-corra la búsqueda de hiperparámetros completa (`select_best_candidate`) en cada `/forecast/run` cuando el dataset consolidado no cambió desde la última corrida.

**Architecture:** Un fingerprint barato del dataset (mtime + tamaño del archivo, sin leer contenido) permite detectar si cambió. `execute_configured_pipeline` guarda en memoria del proceso (variable de módulo, protegida por un lock) el último modelo auto-seleccionado junto con el fingerprint con el que se seleccionó; lo reutiliza mientras el fingerprint no cambie. El camino de modelo recalibrado (prioridad más alta, ADR-0006) no cambia y nunca toca este caché.

**Tech Stack:** Python (`threading.Lock` de la librería estándar, sin dependencias nuevas), pytest.

**Spec:** `openspec/changes/add-selection-caching/proposal.md`, `openspec/changes/add-selection-caching/specs/data-ingestion/spec.md`, `openspec/changes/add-selection-caching/specs/alerting-ui/spec.md`.

## Global Constraints

- No se agregan dependencias nuevas.
- `get_dataset_fingerprint` NUNCA lee el contenido del dataset — solo `Path.stat()` (mtime + tamaño).
- El camino de modelo recalibrado no cambia: sigue teniendo la prioridad más alta y **no** interactúa con el caché de selección automática (ni lo lee ni lo escribe).
- El caché es en memoria del proceso backend — no se persiste a disco ni a MLflow (fuera de alcance de este *change*). Se pierde en cada reinicio del backend, lo cual es aceptado.
- `src/architecture_integration/pipeline.py` no se modifica.
- Cada tarea termina con sus tests en verde; al final de la Tarea 2, correr `pytest -q` (raíz) y `cd backend && python -m pytest tests -q`.

---

### Task 1: Fingerprint barato de un dataset guardado

**Files:**
- Modify: `src/data_ingestion/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: nada nuevo — usa `DEFAULT_DATA_DIR` ya existente en el mismo módulo.
- Produces: `get_dataset_fingerprint(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> tuple[float, int]` (mtime, tamaño en bytes); levanta `FileNotFoundError` si el dataset no existe, igual que `load_dataset`. Consumido por Tarea 2.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_storage.py`:

```python
import time


def test_get_dataset_fingerprint_changes_when_dataset_is_rewritten(tmp_path):
    from data_ingestion.storage import get_dataset_fingerprint

    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("mi_dataset", df, data_dir=tmp_path)
    fingerprint_before = get_dataset_fingerprint("mi_dataset", data_dir=tmp_path)

    time.sleep(0.05)
    df2 = pd.DataFrame(
        {"timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]), "temperature": [25.0, 26.0]}
    )
    save_dataset("mi_dataset", df2, data_dir=tmp_path)
    fingerprint_after = get_dataset_fingerprint("mi_dataset", data_dir=tmp_path)

    assert fingerprint_before != fingerprint_after


def test_get_dataset_fingerprint_stable_without_changes(tmp_path):
    from data_ingestion.storage import get_dataset_fingerprint

    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("mi_dataset", df, data_dir=tmp_path)

    fingerprint_1 = get_dataset_fingerprint("mi_dataset", data_dir=tmp_path)
    fingerprint_2 = get_dataset_fingerprint("mi_dataset", data_dir=tmp_path)

    assert fingerprint_1 == fingerprint_2


def test_get_dataset_fingerprint_raises_when_dataset_missing(tmp_path):
    from data_ingestion.storage import get_dataset_fingerprint

    with pytest.raises(FileNotFoundError):
        get_dataset_fingerprint("no_existe", data_dir=tmp_path)
```

(El import de `get_dataset_fingerprint` queda dentro de cada test a propósito, para que el `ImportError` de la Step 2 sea local a cada test y no rompa la colección de todo el archivo.)

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_dataset_fingerprint' from 'data_ingestion.storage'` en los 3 tests nuevos; los 2 tests preexistentes (`test_save_and_load_roundtrip`, `test_load_missing_dataset_raises`) siguen en PASS.

- [ ] **Step 3: Implementar la función**

En `src/data_ingestion/storage.py`, agregar al final del archivo:

```python
def get_dataset_fingerprint(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> tuple[float, int]:
    """Devuelve una huella barata (fecha de modificación, tamaño en
    bytes) del archivo de `name`, sin leer su contenido. Cambia si y
    solo si el archivo fue reescrito con `save_dataset`.
    """
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset '{name}' en {data_dir}")
    stat = path.stat()
    return (stat.st_mtime, stat.st_size)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (los 5 tests: los 2 preexistentes más los 3 nuevos).

- [ ] **Step 5: Commit**

```bash
git add src/data_ingestion/storage.py tests/test_storage.py
git commit -m "feat: agrega get_dataset_fingerprint para detectar cambios sin leer el dataset"
```

---

### Task 2: Cachear el modelo auto-seleccionado en el backend

**Files:**
- Modify: `backend/app/pipeline.py`
- Test: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `get_dataset_fingerprint` (Tarea 1).
- Produces: sin cambios de firma pública. `execute_configured_pipeline` sigue devolviendo el mismo dict de siempre. Última tarea del plan — nada consumido por tareas posteriores.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al inicio de `backend/tests/test_pipeline.py` (después de los imports existentes, antes del primer test) un import adicional:

```python
import app.pipeline as pipeline_module
```

Agregar al final del archivo:

```python
def test_execute_configured_pipeline_reuses_cached_selection_when_dataset_unchanged(monkeypatch):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: None)
    monkeypatch.setattr("app.pipeline._selection_cache", None)
    df = load_dataset(DATASET_NAME)

    received_models = []
    original = pipeline_module.run_end_to_end_pipeline

    def _spy(*args, **kwargs):
        received_models.append(kwargs.get("model"))
        return original(*args, **kwargs)

    monkeypatch.setattr("app.pipeline.run_end_to_end_pipeline", _spy)

    first = execute_configured_pipeline(df)
    second = execute_configured_pipeline(df)

    assert received_models == [None, first["model"]]
    assert second["model"] is first["model"]
    assert second["model_name"] == first["model_name"]


def test_execute_configured_pipeline_reselects_when_dataset_fingerprint_changes(monkeypatch):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: None)
    monkeypatch.setattr("app.pipeline._selection_cache", None)
    df = load_dataset(DATASET_NAME)

    fingerprints = iter([(1.0, 100), (2.0, 200)])
    monkeypatch.setattr(
        "app.pipeline.get_dataset_fingerprint", lambda *args, **kwargs: next(fingerprints)
    )

    received_models = []
    original = pipeline_module.run_end_to_end_pipeline

    def _spy(*args, **kwargs):
        received_models.append(kwargs.get("model"))
        return original(*args, **kwargs)

    monkeypatch.setattr("app.pipeline.run_end_to_end_pipeline", _spy)

    execute_configured_pipeline(df)
    execute_configured_pipeline(df)

    assert received_models == [None, None]


def test_execute_configured_pipeline_recalibrated_model_ignores_selection_cache(monkeypatch):
    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("no debería reentrenar cuando hay un modelo recalibrado")

        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    cached_model = _FitRaisesModel()
    monkeypatch.setattr(
        "app.pipeline._selection_cache",
        {"model": cached_model, "model_name": "random_forest", "fingerprint": (0.0, 0)},
    )
    fake_recalibrated = _FitRaisesModel()
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: fake_recalibrated)
    df = load_dataset(DATASET_NAME)

    result = execute_configured_pipeline(df)

    assert result["model"] is fake_recalibrated
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `test_execute_configured_pipeline_reuses_cached_selection_when_dataset_unchanged` y `test_execute_configured_pipeline_reselects_when_dataset_fingerprint_changes` fallan con `AttributeError: <module 'app.pipeline'> does not have the attribute '_selection_cache'` (el monkeypatch de un atributo inexistente falla así); `test_execute_configured_pipeline_recalibrated_model_ignores_selection_cache` puede fallar con el mismo error o pasar por casualidad (el camino recalibrado ya ignoraba cualquier variable no usada) — no importa, las dos primeras ya prueban que falta la implementación. Los 4 tests preexistentes siguen en PASS.

- [ ] **Step 3: Implementar el caché**

Reemplazar el contenido completo de `backend/app/pipeline.py`:

```python
"""Helper compartido de ejecución del pipeline de pronóstico (spec
alerting-ui, requirements "Uso del modelo recalibrado en el próximo
pronóstico" y "Reutilización del modelo auto-seleccionado mientras el
dataset no cambie"). Usado por `/forecast/run` y `/recalibrate` para no
duplicar la lógica de elección de modelo y llamada al pipeline.
"""

from __future__ import annotations

import threading
from typing import Any

import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.storage import get_dataset_fingerprint, load_dataset
from human_feedback.model_registry import load_latest_recalibrated_model

from .config import DATASET_NAME, FEATURE_COLUMNS, LABEL_COLUMN, RANDOM_STATE

_selection_cache_lock = threading.Lock()
_selection_cache: dict[str, Any] | None = None


def load_dataset_or_raise() -> pd.DataFrame:
    """Carga el dataset consolidado configurado, o levanta
    `FileNotFoundError` con un mensaje explícito si no existe.
    """
    try:
        return load_dataset(DATASET_NAME)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"No existe el dataset '{DATASET_NAME}'.") from error


def execute_configured_pipeline(df: pd.DataFrame) -> dict[str, Any]:
    """Ejecuta el pipeline completo sobre `df` usando la configuración
    del backend: si hay un modelo recalibrado registrado en MLflow, lo
    usa sin reentrenar (`skip_fit=True`), ignorando el caché de
    selección. Si no, reutiliza el último modelo auto-seleccionado
    mientras el dataset configurado no haya cambiado (comparando su
    fingerprint); si cambió o todavía no hay ninguno cacheado, deja que
    `run_end_to_end_pipeline` seleccione automáticamente el mejor
    modelo candidato (`predictive_modeling.model_selection`) y guarda
    el resultado en el caché.
    """
    global _selection_cache

    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    recalibrated_model = load_latest_recalibrated_model()
    if recalibrated_model is not None:
        return run_end_to_end_pipeline(
            df,
            label_column=LABEL_COLUMN,
            feature_columns=FEATURE_COLUMNS,
            split_date=split_date,
            model=recalibrated_model,
            include_anomaly_detection=False,
            random_state=RANDOM_STATE,
            skip_fit=True,
        )

    fingerprint = get_dataset_fingerprint(DATASET_NAME)
    with _selection_cache_lock:
        cached = _selection_cache
    if cached is not None and cached["fingerprint"] == fingerprint:
        model, skip_fit, cached_model_name = cached["model"], True, cached["model_name"]
    else:
        model, skip_fit, cached_model_name = None, False, None

    result = run_end_to_end_pipeline(
        df,
        label_column=LABEL_COLUMN,
        feature_columns=FEATURE_COLUMNS,
        split_date=split_date,
        model=model,
        include_anomaly_detection=False,
        random_state=RANDOM_STATE,
        skip_fit=skip_fit,
    )

    if model is None:
        with _selection_cache_lock:
            _selection_cache = {
                "model": result["model"],
                "model_name": result["model_name"],
                "fingerprint": fingerprint,
            }
    else:
        # run_end_to_end_pipeline deja model_name en None cuando skip_fit=True
        # (no hubo selección en esta corrida) — se repone desde el caché para
        # que /recalibrate siga pudiendo loguear qué modelo generó el
        # pronóstico anterior, y para que el resultado sea igual de
        # informativo que el de una corrida que sí seleccionó.
        result["model_name"] = cached_model_name

    return result
```

Nota: el lock se toma dos veces por separado (lectura del caché, luego escritura) en vez de mantenerlo tomado durante toda la ejecución de `run_end_to_end_pipeline` — a propósito, para no bloquear otros requests mientras corre una selección que puede tardar varios segundos.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: PASS (los 7 tests: los 4 preexistentes más los 3 nuevos).

- [ ] **Step 5: Correr toda la suite del proyecto**

Run: `pytest -q` (raíz) y `cd backend && python -m pytest tests -q`
Expected: PASS en ambos, sin romper nada de `add-model-selection-engine` ni `add-recalibration-trigger`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: cachea el modelo auto-seleccionado mientras el dataset no cambie"
```
