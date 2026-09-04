# Multi-Sensor Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Soportar múltiples sensores (mock, sin sensores reales todavía) enviando lecturas en paralelo al backend de `alerting-ui`, con aislamiento total de dataset, feedback, caché de selección de modelo y modelo recalibrado entre sensores.

**Architecture:** Se introduce `sensor_id` como segmento de ruta obligatorio en los cuatro routers de `alerting-ui`. Una única función de naming (`src/data_ingestion/sensor_naming.py`) valida `sensor_id` y deriva, por convención de prefijo, el nombre de dataset (`sensor__{id}`), de feedback log (`feedback__{id}`) y de modelo registrado en MLflow (`alerting_ui_recalibrated_model__{id}`) — nunca colisionan entre sí ni con el dataset histórico de investigación. `backend/app/pipeline.py::_selection_cache` pasa de un único valor global a un dict indexado por `sensor_id`. Ningún módulo de `predictive_modeling`/`architecture_integration` cambia: cada sensor sigue siendo una serie temporal independiente, el caso que esas capas ya soportan.

**Tech Stack:** Python (FastAPI/Pydantic para rutas y validación, MLflow para el registro de modelos), pytest. Sin dependencias nuevas.

**Spec:** `openspec/changes/add-multi-sensor-ingestion/proposal.md`, `openspec/changes/add-multi-sensor-ingestion/specs/alerting-ui/spec.md`, `openspec/changes/add-multi-sensor-ingestion/specs/data-ingestion/spec.md`, `docs/adr/0008-ruteo-y-aislamiento-multi-sensor.md`.

## Global Constraints

- Sin dependencias nuevas.
- `sensor_id` se valida en un único lugar (`data_ingestion.sensor_naming.validate_sensor_id`, regex `^[a-zA-Z0-9_-]{1,64}$`) — ningún router ni script reimplementa esa regex.
- Ningún `sensor_id` válido puede producir el nombre del dataset histórico (`melchor_romero_2024_consolidado`) — se verifica con un test dedicado, no se confía solo en la inspección visual del prefijo.
- Breaking change deliberado y aceptado (ADR-0008): ningún endpoint de `alerting-ui` queda accesible sin `sensor_id` en la ruta. No se agregan rutas "sin sensor" ni un `sensor_id` default.
- `src/architecture_integration/pipeline.py`, `src/predictive_modeling/*`, `src/human_feedback/registry.py`, `src/human_feedback/recalibration.py`, `src/data_ingestion/mock_sensor.py`, `src/data_ingestion/storage.py`, `data_ingestion/schema.py` NO se modifican — todos ya reciben el nombre de recurso como parámetro, no necesitan saber que existe un `sensor_id`.
- `frontend/` no se toca en este plan (selector de sensor queda fuera de alcance, ADR-0008).
- Cada tarea termina con sus tests en verde. Dentro de una tarea, un test puede estar en rojo temporalmente entre sub-pasos (ciclo TDD normal) — lo que debe estar en verde es el estado final de la tarea, verificado corriendo `pytest -q` (raíz) y `cd backend && python -m pytest tests -q`.
- Las Tareas 1 y 2 son interdependientes (el router de recalibración usa el modelo registrado por sensor) y se entregan en un único commit por tarea, como ya es la convención de este repo para cambios de ruteo transversales (ver `docs/superpowers/plans/2026-08-23-mock-sensor-ingestion.md`, Tarea 3).

---

### Task 1: Convención de nombres de recursos por sensor

**Files:**
- Create: `src/data_ingestion/sensor_naming.py`
- Test: `tests/test_sensor_naming.py`

**Interfaces:**
- Consumes: nada (módulo de base, sin dependencias del proyecto).
- Produces: `validate_sensor_id(sensor_id: str) -> str` (levanta `ValueError` si es inválido), `dataset_name_for(sensor_id: str) -> str`, `feedback_log_name_for(sensor_id: str) -> str`, `registered_model_name_for(sensor_id: str) -> str`. Consumidos por Tarea 2 (`model_registry.py`, `backend/app/pipeline.py`, los cuatro routers, `backend/app/dependencies.py`) y Tarea 3 (scripts).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_sensor_naming.py`:

```python
import pytest

from data_ingestion.sensor_naming import (
    dataset_name_for,
    feedback_log_name_for,
    registered_model_name_for,
    validate_sensor_id,
)


def test_validate_sensor_id_accepts_alphanumeric_dash_underscore():
    assert validate_sensor_id("sensor-melchor_1") == "sensor-melchor_1"


@pytest.mark.parametrize(
    "invalid_id",
    ["", "a" * 65, "sensor/1", "../etc/passwd", "sensor con espacio", "sensor.1"],
)
def test_validate_sensor_id_rejects_invalid_ids(invalid_id):
    with pytest.raises(ValueError):
        validate_sensor_id(invalid_id)


def test_dataset_name_for_includes_sensor_id_and_prefix():
    assert dataset_name_for("melchor-1") == "sensor__melchor-1"


def test_feedback_log_name_for_includes_sensor_id_and_prefix():
    assert feedback_log_name_for("melchor-1") == "feedback__melchor-1"


def test_registered_model_name_for_includes_sensor_id_and_prefix():
    assert registered_model_name_for("melchor-1") == "alerting_ui_recalibrated_model__melchor-1"


def test_different_sensor_ids_never_collide_on_any_resource_name():
    for namer in (dataset_name_for, feedback_log_name_for, registered_model_name_for):
        assert namer("sensor-a") != namer("sensor-b")


def test_dataset_name_for_can_never_equal_the_historical_dataset_name():
    historical = "melchor_romero_2024_consolidado"
    for sensor_id in ("melchor_romero_2024_consolidado", "a", "sensor-1", "melchor"):
        assert dataset_name_for(sensor_id) != historical


def test_invalid_sensor_id_raises_before_deriving_any_name():
    for namer in (dataset_name_for, feedback_log_name_for, registered_model_name_for):
        with pytest.raises(ValueError):
            namer("invalido/con/barras")
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_sensor_naming.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data_ingestion.sensor_naming'`.

- [ ] **Step 3: Implementar el módulo**

Crear `src/data_ingestion/sensor_naming.py`:

```python
"""Convención de nombres de recursos por sensor (ADR-0008): deriva, a
partir de un `sensor_id` validado, el dataset, el feedback log y el
modelo registrado propios de ese sensor, de forma que dos sensores
nunca colisionen entre sí ni con el dataset histórico de investigación
(`melchor_romero_2024_consolidado`, que nunca empieza con `sensor__`).
"""

from __future__ import annotations

import re

_SENSOR_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_sensor_id(sensor_id: str) -> str:
    """Devuelve `sensor_id` sin modificar si cumple
    `^[a-zA-Z0-9_-]{1,64}$`; levanta `ValueError` si no.
    """
    if not _SENSOR_ID_PATTERN.match(sensor_id):
        raise ValueError(
            f"sensor_id inválido: '{sensor_id}'. Debe cumplir "
            f"'{_SENSOR_ID_PATTERN.pattern}' (alfanumérico, '-' y '_', 1 a 64 caracteres)."
        )
    return sensor_id


def dataset_name_for(sensor_id: str) -> str:
    """Nombre del dataset propio de `sensor_id`."""
    return f"sensor__{validate_sensor_id(sensor_id)}"


def feedback_log_name_for(sensor_id: str) -> str:
    """Nombre del registro de retroalimentación propio de `sensor_id`."""
    return f"feedback__{validate_sensor_id(sensor_id)}"


def registered_model_name_for(sensor_id: str) -> str:
    """Nombre del modelo registrado en MLflow propio de `sensor_id`."""
    return f"alerting_ui_recalibrated_model__{validate_sensor_id(sensor_id)}"
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_sensor_naming.py -v`
Expected: PASS (los 12 tests, contando los 6 casos parametrizados).

- [ ] **Step 5: Commit**

```bash
git add src/data_ingestion/sensor_naming.py tests/test_sensor_naming.py
git commit -m "feat: agrega la convencion de nombres de recursos por sensor"
```

---

### Task 2: Ruteo y aislamiento por sensor en el backend

**Files:**
- Modify: `src/human_feedback/model_registry.py`
- Test: `tests/test_model_registry.py`
- Create: `backend/app/dependencies.py`
- Test: `backend/tests/test_dependencies.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/pipeline.py`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/test_pipeline.py`
- Modify: `backend/app/routers/sensors.py`
- Test: `backend/tests/test_sensors.py`
- Modify: `backend/app/routers/feedback.py`
- Test: `backend/tests/test_feedback.py`
- Modify: `backend/app/routers/forecast.py`
- Test: `backend/tests/test_forecast.py`
- Modify: `backend/app/routers/recalibration.py`
- Test: `backend/tests/test_recalibration.py`

**Interfaces:**
- Consumes: `data_ingestion.sensor_naming.{validate_sensor_id, dataset_name_for, feedback_log_name_for, registered_model_name_for}` (Tarea 1).
- Produces: `register_recalibrated_model(sensor_id, model, params, metrics) -> str`, `load_latest_recalibrated_model(sensor_id) -> object | None`; `get_valid_sensor_id(sensor_id: str) -> str` (dependencia FastAPI); `load_dataset_or_raise(sensor_id, data_dir=DEFAULT_DATA_DIR) -> tuple[pd.DataFrame, tuple[float, int]]`, `execute_configured_pipeline(df, sensor_id, fingerprint=None, data_dir=DEFAULT_DATA_DIR) -> dict`; rutas `POST /sensors/{sensor_id}/readings`, `POST /forecast/{sensor_id}/run`, `GET /feedback/{sensor_id}`, `POST /feedback/{sensor_id}/{fecha}/confirm`, `POST /feedback/{sensor_id}/{fecha}/reject`, `POST /recalibrate/{sensor_id}`. Consumidos por Tarea 3 (scripts) y por cualquier futuro frontend (fuera de alcance).

#### Sub-tarea 2.1: `model_registry` por sensor

- [ ] **Step 1: Escribir los tests que fallan**

Reemplazar `tests/test_model_registry.py` completo por:

```python
import mlflow
import pandas as pd
import pytest
from mlflow.exceptions import MlflowException
from sklearn.linear_model import LogisticRegression

from human_feedback.model_registry import (
    load_latest_recalibrated_model,
    register_recalibrated_model,
)


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def test_register_and_load_latest_recalibrated_model(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-register-and-load")
    X = pd.DataFrame({"feature": [0, 1, 2, 3]})
    y = pd.Series([0, 0, 1, 1])
    model = LogisticRegression().fit(X, y)

    version = register_recalibrated_model(
        "sensor-a", model, params={"n_correcciones": 1}, metrics={"n_filas_entrenamiento": 4}
    )

    assert version == "1"
    loaded = load_latest_recalibrated_model("sensor-a")
    assert hasattr(loaded, "predict")
    assert list(loaded.predict(X)) == list(model.predict(X))


def test_load_latest_recalibrated_model_returns_none_when_nothing_registered(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-nothing-registered")

    assert load_latest_recalibrated_model("sensor-a") is None


def test_register_recalibrated_model_twice_returns_incrementing_versions(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-incrementing-versions")
    X = pd.DataFrame({"feature": [0, 1, 2, 3]})
    y = pd.Series([0, 0, 1, 1])
    model = LogisticRegression().fit(X, y)

    v1 = register_recalibrated_model("sensor-a", model, params={}, metrics={})
    v2 = register_recalibrated_model("sensor-a", model, params={}, metrics={})

    assert v1 == "1"
    assert v2 == "2"
    loaded = load_latest_recalibrated_model("sensor-a")
    assert hasattr(loaded, "predict")


def test_recalibrated_models_are_isolated_per_sensor(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-isolated-per-sensor")
    X = pd.DataFrame({"feature": [0, 1, 2, 3]})
    y = pd.Series([0, 0, 1, 1])
    model = LogisticRegression().fit(X, y)

    register_recalibrated_model("sensor-a", model, params={}, metrics={})

    assert load_latest_recalibrated_model("sensor-a") is not None
    assert load_latest_recalibrated_model("sensor-b") is None


def test_load_latest_recalibrated_model_raises_when_mlflow_is_unreachable(monkeypatch):
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    mlflow.set_tracking_uri("http://localhost:59999")

    with pytest.raises(MlflowException):
        load_latest_recalibrated_model("sensor-a")
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_model_registry.py -v`
Expected: FAIL — `TypeError: register_recalibrated_model() takes 3 positional arguments but 4 were given` (la firma actual no acepta `sensor_id`).

- [ ] **Step 3: Implementar el cambio**

Reemplazar `src/human_feedback/model_registry.py` completo por:

```python
"""Registro y recuperación de versiones del modelo recalibrado en el
Model Registry de MLflow (spec alerting-ui, requirement "Disparo
manual de recalibración desde la interfaz, por sensor"). El nombre de
modelo registrado se deriva por sensor (ADR-0008) — nunca es fijo.
"""

from __future__ import annotations

import mlflow
import mlflow.sklearn

from data_ingestion.sensor_naming import registered_model_name_for


def register_recalibrated_model(
    sensor_id: str, model: object, params: dict, metrics: dict
) -> str:
    """Registra `model` como una nueva versión en el Model Registry de
    MLflow bajo el nombre propio de `sensor_id`, junto con `params` y
    `metrics` en un run propio. Devuelve el número de versión
    registrada.
    """
    registered_model_name = registered_model_name_for(sensor_id)
    with mlflow.start_run(run_name="recalibracion") as run:
        for key, value in params.items():
            mlflow.log_param(key, value)
        for key, value in metrics.items():
            mlflow.log_metric(key, value)
        mlflow.sklearn.log_model(
            model, artifact_path="model", registered_model_name=registered_model_name
        )
        run_id = run.info.run_id

    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{registered_model_name}'")
    matching = [v for v in versions if v.run_id == run_id]
    return str(matching[0].version)


def load_latest_recalibrated_model(sensor_id: str) -> object | None:
    """Recupera la versión más reciente registrada para `sensor_id`, o
    `None` si todavía no se registró ninguna. Si MLflow no está
    disponible, la excepción se propaga sin capturarse (ADR-0006).
    """
    registered_model_name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{registered_model_name}'")
    if not versions:
        return None
    latest = max(versions, key=lambda v: int(v.version))
    return mlflow.sklearn.load_model(f"models:/{registered_model_name}/{latest.version}")
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_model_registry.py -v`
Expected: PASS (los 5 tests).

#### Sub-tarea 2.2: dependencia de validación de `sensor_id`

- [ ] **Step 5: Escribir el test que falla**

Crear `backend/tests/test_dependencies.py`:

```python
import pytest
from fastapi import HTTPException

from app.dependencies import get_valid_sensor_id


def test_get_valid_sensor_id_returns_valid_id():
    assert get_valid_sensor_id("sensor-a") == "sensor-a"


def test_get_valid_sensor_id_raises_422_for_invalid_id():
    with pytest.raises(HTTPException) as exc_info:
        get_valid_sensor_id("invalido.con.puntos")
    assert exc_info.value.status_code == 422
```

- [ ] **Step 6: Correr el test y verificar que falla**

Run: `cd backend && python -m pytest tests/test_dependencies.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.dependencies'`.

- [ ] **Step 7: Implementar la dependencia**

Crear `backend/app/dependencies.py`:

```python
"""Dependencia compartida de FastAPI para validar `sensor_id` en los
cuatro routers de `alerting-ui` (ADR-0008): un único punto de
validación, reusando `data_ingestion.sensor_naming.validate_sensor_id`.
"""

from __future__ import annotations

from fastapi import HTTPException

from data_ingestion.sensor_naming import validate_sensor_id


def get_valid_sensor_id(sensor_id: str) -> str:
    try:
        return validate_sensor_id(sensor_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
```

- [ ] **Step 8: Correr el test y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_dependencies.py -v`
Expected: PASS (los 2 tests).

#### Sub-tarea 2.3: `backend/app/pipeline.py` y `backend/app/config.py` por sensor

- [ ] **Step 9: Escribir los tests que fallan**

Reemplazar `backend/tests/test_pipeline.py` completo por:

```python
from pathlib import Path

import numpy as np

import app.pipeline as pipeline_module
from app.config import HISTORICAL_DATASET_NAME
from app.pipeline import execute_configured_pipeline, load_dataset_or_raise
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, get_dataset_fingerprint, load_dataset, save_dataset


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_execute_configured_pipeline_trains_a_new_model_when_none_recalibrated(
    monkeypatch, tmp_path
):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda sensor_id: None)
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    result = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert hasattr(result["model"], "predict_proba")
    assert len(result["test"]) > 0


def test_execute_configured_pipeline_reuses_recalibrated_model_without_refitting(
    monkeypatch, tmp_path
):
    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("no debería reentrenar cuando hay un modelo recalibrado")

        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    fake_model = _FitRaisesModel()
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda sensor_id: fake_model)
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    result = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert result["model"] is fake_model


def test_load_dataset_or_raise_raises_file_not_found_with_explicit_message(tmp_path):
    try:
        load_dataset_or_raise("sensor-inexistente", data_dir=tmp_path)
        assert False, "debería haber levantado FileNotFoundError"
    except FileNotFoundError as error:
        assert "sensor__sensor-inexistente" in str(error)


def test_execute_configured_pipeline_selects_a_model_automatically_when_none_recalibrated(
    monkeypatch, tmp_path
):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda sensor_id: None)
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    result = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert result["model_name"] in {"logistic_regression", "random_forest"}


def test_execute_configured_pipeline_reuses_cached_selection_when_dataset_unchanged(
    monkeypatch, tmp_path
):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda sensor_id: None)
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    received_models = []
    original = pipeline_module.run_end_to_end_pipeline

    def _spy(*args, **kwargs):
        received_models.append(kwargs.get("model"))
        return original(*args, **kwargs)

    monkeypatch.setattr("app.pipeline.run_end_to_end_pipeline", _spy)

    first = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)
    second = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert received_models == [None, first["model"]]
    assert second["model"] is first["model"]
    assert second["model_name"] == first["model_name"]


def test_execute_configured_pipeline_reselects_when_dataset_fingerprint_changes(
    monkeypatch, tmp_path
):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda sensor_id: None)
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

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

    execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)
    execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert received_models == [None, None]


def test_execute_configured_pipeline_recalibrated_model_ignores_selection_cache(
    monkeypatch, tmp_path
):
    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("no debería reentrenar cuando hay un modelo recalibrado")

        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    cached_model = _FitRaisesModel()
    monkeypatch.setattr(
        "app.pipeline._selection_cache",
        {
            "sensor-a": {
                "model": cached_model,
                "model_name": "random_forest",
                "fingerprint": (0.0, 0),
            }
        },
    )
    fake_recalibrated = _FitRaisesModel()
    monkeypatch.setattr(
        "app.pipeline.load_latest_recalibrated_model", lambda sensor_id: fake_recalibrated
    )
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    result = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert result["model"] is fake_recalibrated


def test_load_dataset_or_raise_returns_dataframe_and_matching_fingerprint(tmp_path):
    _seed_sensor_dataset("sensor-a", tmp_path)

    df, fingerprint = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    assert len(df) > 0
    assert fingerprint == get_dataset_fingerprint(dataset_name_for("sensor-a"), data_dir=tmp_path)


def test_selection_cache_is_isolated_per_sensor(monkeypatch, tmp_path):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda sensor_id: None)
    _seed_sensor_dataset("sensor-a", tmp_path)
    _seed_sensor_dataset("sensor-b", tmp_path)
    df_a, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)
    df_b, _ = load_dataset_or_raise("sensor-b", data_dir=tmp_path)

    received_models = []
    original = pipeline_module.run_end_to_end_pipeline

    def _spy(*args, **kwargs):
        received_models.append(kwargs.get("model"))
        return original(*args, **kwargs)

    monkeypatch.setattr("app.pipeline.run_end_to_end_pipeline", _spy)

    execute_configured_pipeline(df_a, "sensor-a", data_dir=tmp_path)
    execute_configured_pipeline(df_b, "sensor-b", data_dir=tmp_path)

    # ambos entrenan desde cero (model=None): el caché de "sensor-a" no se
    # reutilizó para "sensor-b"
    assert received_models == [None, None]
    assert set(pipeline_module._selection_cache.keys()) == {"sensor-a", "sensor-b"}
```

Reemplazar `backend/tests/conftest.py` completo por:

```python
import pytest


@pytest.fixture(autouse=True)
def _reset_selection_cache():
    import app.pipeline as pipeline_module

    pipeline_module._selection_cache = {}
    yield
    pipeline_module._selection_cache = {}
```

- [ ] **Step 10: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `TypeError: load_dataset_or_raise() got an unexpected keyword argument 'data_dir'` (o similar, la firma actual no acepta `sensor_id` ni `data_dir`).

- [ ] **Step 11: Implementar el cambio**

Reemplazar `backend/app/config.py` completo por:

```python
"""Configuración del backend (fachada delgada, ADR-0003). Los nombres
de dataset, feedback log y modelo registrado ya no son globales por
deployment: se derivan por sensor (ADR-0008,
`data_ingestion.sensor_naming`).
"""

from __future__ import annotations

from pathlib import Path

from data_ingestion.storage import DEFAULT_DATA_DIR

HISTORICAL_DATASET_NAME = "melchor_romero_2024_consolidado"

FEATURE_COLUMNS = ["soil_moisture", "solar_radiation", "relative_humidity"]
LABEL_COLUMN = "soil_moisture"
RANDOM_STATE = 42


def get_feedback_data_dir() -> Path:
    """Dependencia de FastAPI: directorio donde persisten los registros
    de retroalimentación. Overrideable en tests
    (`app.dependency_overrides`) para no escribir en el `data/` real
    del proyecto.
    """
    return DEFAULT_DATA_DIR


def get_dataset_data_dir() -> Path:
    """Dependencia de FastAPI: directorio donde persisten los datasets
    de sensor. Overrideable en tests (`app.dependency_overrides`) para
    no escribir en el `data/` real del proyecto.
    """
    return DEFAULT_DATA_DIR
```

Reemplazar `backend/app/pipeline.py` completo por:

```python
"""Helper compartido de ejecución del pipeline de pronóstico, por
sensor (spec alerting-ui, requirements "Uso del modelo recalibrado en
el próximo pronóstico, por sensor" y "Reutilización del modelo
auto-seleccionado mientras el dataset de un sensor no cambie"). Usado
por `/forecast/{sensor_id}/run` y `/recalibrate/{sensor_id}` para no
duplicar la lógica de elección de modelo y llamada al pipeline.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, get_dataset_fingerprint, load_dataset
from human_feedback.model_registry import load_latest_recalibrated_model

from .config import FEATURE_COLUMNS, LABEL_COLUMN, RANDOM_STATE

_selection_cache_lock = threading.Lock()
_selection_cache: dict[str, dict[str, Any]] = {}


def load_dataset_or_raise(
    sensor_id: str, data_dir: Path = DEFAULT_DATA_DIR
) -> tuple[pd.DataFrame, tuple[float, int]]:
    """Carga el dataset propio de `sensor_id` junto con su fingerprint
    (capturado inmediatamente después de la lectura), o levanta
    `FileNotFoundError` con un mensaje explícito si no existe.
    """
    dataset_name = dataset_name_for(sensor_id)
    try:
        df = load_dataset(dataset_name, data_dir=data_dir)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"No existe el dataset '{dataset_name}'.") from error
    return df, get_dataset_fingerprint(dataset_name, data_dir=data_dir)


def execute_configured_pipeline(
    df: pd.DataFrame,
    sensor_id: str,
    fingerprint: tuple[float, int] | None = None,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, Any]:
    """Ejecuta el pipeline completo sobre `df` para `sensor_id`: si hay
    un modelo recalibrado registrado para ese sensor en MLflow, lo usa
    sin reentrenar (`skip_fit=True`), ignorando el caché de selección
    de ese sensor. Si no, reutiliza el último modelo auto-seleccionado
    de ese sensor mientras su dataset no haya cambiado (comparando su
    fingerprint); si cambió o todavía no hay ninguno cacheado para ese
    sensor, deja que `run_end_to_end_pipeline` seleccione
    automáticamente el mejor modelo candidato y guarda el resultado en
    el caché, bajo la clave de ese sensor. El caché de selección
    (`_selection_cache`) es un dict por `sensor_id` — nunca se
    comparte entre sensores.
    """
    global _selection_cache

    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    recalibrated_model = load_latest_recalibrated_model(sensor_id)
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

    if fingerprint is None:
        fingerprint = get_dataset_fingerprint(dataset_name_for(sensor_id), data_dir=data_dir)
    with _selection_cache_lock:
        cached = _selection_cache.get(sensor_id)
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
            _selection_cache[sensor_id] = {
                "model": result["model"],
                "model_name": result["model_name"],
                "fingerprint": fingerprint,
            }
    else:
        result["model_name"] = cached_model_name

    return result
```

- [ ] **Step 12: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: PASS (los 9 tests).

#### Sub-tarea 2.4: router de ingesta (`/sensors/{sensor_id}/readings`)

- [ ] **Step 13: Escribir los tests que fallan**

Reemplazar `backend/tests/test_sensors.py` completo por:

```python
import pandas as pd
from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir
from app.main import app
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import load_dataset, save_dataset
from fastapi.testclient import TestClient


def test_ingest_reading_creates_dataset_when_missing(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        "/sensors/sensor-a/readings",
        json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0, "procedencia": "sintetico"},
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 1

    app.dependency_overrides.clear()


def test_ingest_reading_appends_to_existing_dataset(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )
    response = client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-02T00:00:00", "temperature": 26.0}
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 2

    app.dependency_overrides.clear()


def test_ingest_reading_defaults_procedencia_to_real(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )

    df = load_dataset(dataset_name_for("sensor-a"), data_dir=tmp_path)
    assert df.loc[0, "origen"] == "real"

    app.dependency_overrides.clear()


def test_ingest_reading_same_day_different_time_replaces_row(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )
    response = client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T14:30:00", "temperature": 30.0}
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 1

    app.dependency_overrides.clear()


def test_ingest_reading_rejects_invalid_sensor_id(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        "/sensors/sensor.uno/readings",
        json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0},
    )

    assert response.status_code == 422

    app.dependency_overrides.clear()


def test_ingest_reading_isolates_datasets_between_sensors(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )
    client.post(
        "/sensors/sensor-b/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 40.0}
    )

    df_a = load_dataset(dataset_name_for("sensor-a"), data_dir=tmp_path)
    df_b = load_dataset(dataset_name_for("sensor-b"), data_dir=tmp_path)
    assert len(df_a) == 1
    assert len(df_b) == 1
    assert df_a.loc[0, "temperature"] == 25.0
    assert df_b.loc[0, "temperature"] == 40.0

    app.dependency_overrides.clear()


def test_ingest_reading_never_touches_the_historical_dataset(tmp_path):
    historical = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01"]), "temperature": [20.0]})
    save_dataset(HISTORICAL_DATASET_NAME, historical, data_dir=tmp_path)

    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )

    reloaded_historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=tmp_path)
    pd.testing.assert_frame_equal(reloaded_historical, historical)

    app.dependency_overrides.clear()
```

- [ ] **Step 14: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_sensors.py -v`
Expected: FAIL — `404 Not Found` en todos (la ruta sigue siendo `/sensors/readings`, sin `{sensor_id}`).

- [ ] **Step 15: Implementar el cambio**

Reemplazar `backend/app/routers/sensors.py` completo por:

```python
"""Router de ingesta de lecturas de sensores (spec alerting-ui,
requirement "Ingesta de lecturas de sensores desde la interfaz de
datos, aislada por sensor"). Genérico: no distingue si el llamador es
un sensor real o un generador sintético (ADR-0007); aislado por
`sensor_id` (ADR-0008) — nunca puede escribir sobre el dataset
histórico, por construcción del esquema de nombres.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends

from data_ingestion.schema import PROVENANCE_COLUMN
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import append_reading

from ..config import get_dataset_data_dir
from ..dependencies import get_valid_sensor_id
from ..schemas import SensorReadingRequest, SensorReadingResponse

router = APIRouter()


def _normalize_to_day(timestamp: datetime) -> pd.Timestamp:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


@router.post("/sensors/{sensor_id}/readings", response_model=SensorReadingResponse)
def ingest_reading(
    reading: SensorReadingRequest,
    sensor_id: str = Depends(get_valid_sensor_id),
    data_dir: Path = Depends(get_dataset_data_dir),
) -> SensorReadingResponse:
    normalized_timestamp = _normalize_to_day(reading.timestamp)

    row = reading.model_dump(exclude={"procedencia"})
    row["timestamp"] = normalized_timestamp
    row[PROVENANCE_COLUMN] = reading.procedencia

    updated = append_reading(dataset_name_for(sensor_id), row, data_dir=data_dir)

    return SensorReadingResponse(timestamp=normalized_timestamp, filas_totales=len(updated))
```

- [ ] **Step 16: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_sensors.py -v`
Expected: PASS (los 7 tests).

#### Sub-tarea 2.5: router de feedback (`/feedback/{sensor_id}`)

- [ ] **Step 17: Escribir los tests que fallan**

Reemplazar `backend/tests/test_feedback.py` completo por:

```python
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app.config import get_feedback_data_dir
from app.main import app
from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.registry import save_feedback_log
from human_feedback.schema import init_feedback_log


def _seed_feedback_log(sensor_id: str, data_dir: Path) -> str:
    dates = pd.to_datetime(["2024-10-19", "2024-10-20"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)
    save_feedback_log(feedback_log_name_for(sensor_id), log, data_dir=data_dir)
    return "2024-10-19"


def test_list_feedback_returns_404_when_no_forecast_ran_yet(tmp_path: Path):
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/feedback/sensor-a")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_list_feedback_returns_persisted_rows(tmp_path: Path):
    _seed_feedback_log("sensor-a", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/feedback/sensor-a")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 2
    assert rows[0]["estado_validacion"] == "pendiente"
    app.dependency_overrides.clear()


def test_confirm_feedback_updates_state(tmp_path: Path):
    fecha = _seed_feedback_log("sensor-a", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(f"/feedback/sensor-a/{fecha}/confirm")

    assert response.status_code == 200
    assert response.json()["estado_validacion"] == "confirmada"

    persisted = client.get("/feedback/sensor-a").json()["rows"]
    updated_row = next(r for r in persisted if r["fecha"] == fecha)
    assert updated_row["estado_validacion"] == "confirmada"
    app.dependency_overrides.clear()


def test_reject_feedback_stores_correction_and_observation(tmp_path: Path):
    fecha = _seed_feedback_log("sensor-a", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "no habia estres real"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["estado_validacion"] == "rechazada"
    assert body["etiqueta_corregida"] == 0
    assert body["observacion"] == "no habia estres real"
    app.dependency_overrides.clear()


def test_confirm_unknown_date_returns_404(tmp_path: Path):
    _seed_feedback_log("sensor-a", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/feedback/sensor-a/2099-01-01/confirm")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_feedback_logs_are_isolated_per_sensor(tmp_path: Path):
    fecha = _seed_feedback_log("sensor-a", tmp_path)
    _seed_feedback_log("sensor-b", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(f"/feedback/sensor-a/{fecha}/confirm")

    rows_a = client.get("/feedback/sensor-a").json()["rows"]
    rows_b = client.get("/feedback/sensor-b").json()["rows"]
    confirmed_a = next(r for r in rows_a if r["fecha"] == fecha)
    still_pending_b = next(r for r in rows_b if r["fecha"] == fecha)
    assert confirmed_a["estado_validacion"] == "confirmada"
    assert still_pending_b["estado_validacion"] == "pendiente"
    app.dependency_overrides.clear()
```

- [ ] **Step 18: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_feedback.py -v`
Expected: FAIL — `404 Not Found` (las rutas siguen siendo `/feedback`, sin `{sensor_id}`).

- [ ] **Step 19: Implementar el cambio**

Reemplazar `backend/app/routers/feedback.py` completo por:

```python
"""Router de consulta y validación humana de alertas (spec alerting-ui,
requirement "Consulta y validación humana de alertas, por sensor").
"""

from __future__ import annotations

from datetime import date as date_type
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.registry import load_feedback_log, save_feedback_log
from human_feedback.schema import update_feedback

from ..config import get_feedback_data_dir
from ..dependencies import get_valid_sensor_id
from ..schemas import FeedbackListResponse, FeedbackRow, RejectRequest

router = APIRouter()


def _load_or_404(sensor_id: str, data_dir: Path) -> pd.DataFrame:
    try:
        return load_feedback_log(feedback_log_name_for(sensor_id), data_dir=data_dir)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Todavía no se corrió ningún pronóstico."
        ) from error


def _find_date_or_404(log: pd.DataFrame, fecha: date_type) -> pd.Timestamp:
    target = pd.Timestamp(fecha)
    if not (log["fecha"] == target).any():
        raise HTTPException(status_code=404, detail=f"No hay una alerta para la fecha {fecha}.")
    return target


def _row_to_schema(row: pd.Series) -> FeedbackRow:
    etiqueta = row["etiqueta_corregida"]
    observacion = row["observacion"]
    return FeedbackRow(
        fecha=row["fecha"].date(),
        alerta_generada=int(row["alerta_generada"]),
        estado_validacion=row["estado_validacion"],
        etiqueta_corregida=None if pd.isna(etiqueta) else int(etiqueta),
        observacion=None if observacion is None else observacion,
    )


@router.get("/feedback/{sensor_id}", response_model=FeedbackListResponse)
def list_feedback(
    sensor_id: str = Depends(get_valid_sensor_id), data_dir: Path = Depends(get_feedback_data_dir)
) -> FeedbackListResponse:
    log = _load_or_404(sensor_id, data_dir)
    return FeedbackListResponse(rows=[_row_to_schema(row) for _, row in log.iterrows()])


@router.post("/feedback/{sensor_id}/{fecha}/confirm", response_model=FeedbackRow)
def confirm_feedback(
    fecha: date_type,
    sensor_id: str = Depends(get_valid_sensor_id),
    data_dir: Path = Depends(get_feedback_data_dir),
) -> FeedbackRow:
    log = _load_or_404(sensor_id, data_dir)
    target = _find_date_or_404(log, fecha)
    updated = update_feedback(log, fecha=target, estado_validacion="confirmada")
    save_feedback_log(feedback_log_name_for(sensor_id), updated, data_dir=data_dir)
    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)


@router.post("/feedback/{sensor_id}/{fecha}/reject", response_model=FeedbackRow)
def reject_feedback(
    fecha: date_type,
    body: RejectRequest,
    sensor_id: str = Depends(get_valid_sensor_id),
    data_dir: Path = Depends(get_feedback_data_dir),
) -> FeedbackRow:
    log = _load_or_404(sensor_id, data_dir)
    target = _find_date_or_404(log, fecha)
    updated = update_feedback(
        log,
        fecha=target,
        estado_validacion="rechazada",
        etiqueta_corregida=body.etiqueta_corregida,
        observacion=body.observacion,
    )
    save_feedback_log(feedback_log_name_for(sensor_id), updated, data_dir=data_dir)
    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)
```

- [ ] **Step 20: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_feedback.py -v`
Expected: PASS (los 7 tests).

#### Sub-tarea 2.6: router de pronóstico (`/forecast/{sensor_id}/run`)

- [ ] **Step 21: Escribir los tests que fallan**

Reemplazar `backend/tests/test_forecast.py` completo por:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir, get_feedback_data_dir
from app.main import app
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset, save_dataset


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_run_forecast_returns_verdicts(tmp_path: Path):
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/forecast/sensor-a/run")

    assert response.status_code == 200
    body = response.json()
    assert body["train_rows"] > 0
    assert body["test_rows"] > 0
    assert len(body["verdicts"]) == body["test_rows"]
    first = body["verdicts"][0]
    assert set(first.keys()) == {"fecha", "alerta", "probabilidad"}

    app.dependency_overrides.clear()


def test_run_forecast_returns_404_when_dataset_missing(tmp_path: Path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/forecast/sensor-inexistente/run")

    assert response.status_code == 404
    assert "sensor__sensor-inexistente" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_run_forecast_isolates_feedback_between_sensors(tmp_path: Path):
    _seed_sensor_dataset("sensor-a", tmp_path)
    _seed_sensor_dataset("sensor-b", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/forecast/sensor-a/run")
    response_b = client.post("/forecast/sensor-b/run")

    assert response_b.status_code == 200
    feedback_a = client.get("/feedback/sensor-a").json()["rows"]
    feedback_b = client.get("/feedback/sensor-b").json()["rows"]
    assert len(feedback_a) > 0
    assert len(feedback_b) > 0

    app.dependency_overrides.clear()
```

- [ ] **Step 22: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_forecast.py -v`
Expected: FAIL — `404 Not Found` (la ruta sigue siendo `/forecast/run`, sin `{sensor_id}`).

- [ ] **Step 23: Implementar el cambio**

Reemplazar `backend/app/routers/forecast.py` completo por:

```python
"""Router de ejecución de pronóstico (spec alerting-ui, requirement
"Ejecución de pronóstico desde la interfaz, por sensor").
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.registry import load_feedback_log, save_feedback_log, upsert_feedback_log
from human_feedback.schema import init_feedback_log

from ..config import get_dataset_data_dir, get_feedback_data_dir
from ..dependencies import get_valid_sensor_id
from ..pipeline import execute_configured_pipeline, load_dataset_or_raise
from ..schemas import ForecastRunResponse, Verdict

router = APIRouter()


@router.post("/forecast/{sensor_id}/run", response_model=ForecastRunResponse)
def run_forecast(
    sensor_id: str = Depends(get_valid_sensor_id),
    dataset_dir: Path = Depends(get_dataset_data_dir),
    feedback_dir: Path = Depends(get_feedback_data_dir),
) -> ForecastRunResponse:
    try:
        df, fingerprint = load_dataset_or_raise(sensor_id, data_dir=dataset_dir)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    result = execute_configured_pipeline(df, sensor_id, fingerprint, data_dir=dataset_dir)

    dates = result["test"]["timestamp"].reset_index(drop=True)
    alerts = result["alerts"].reset_index(drop=True)
    y_proba = result["y_proba"].reset_index(drop=True)

    feedback_log_name = feedback_log_name_for(sensor_id)
    try:
        existing_feedback = load_feedback_log(feedback_log_name, data_dir=feedback_dir)
        merged_feedback = upsert_feedback_log(existing_feedback, dates, alerts)
    except FileNotFoundError:
        merged_feedback = init_feedback_log(dates, alerts)
    save_feedback_log(feedback_log_name, merged_feedback, data_dir=feedback_dir)

    verdicts = [
        Verdict(fecha=d.date(), alerta=bool(a), probabilidad=float(p))
        for d, a, p in zip(dates, alerts, y_proba)
    ]
    return ForecastRunResponse(
        verdicts=verdicts,
        train_rows=len(result["train"]),
        test_rows=len(result["test"]),
    )
```

- [ ] **Step 24: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_forecast.py -v`
Expected: PASS (los 3 tests).

#### Sub-tarea 2.7: router de recalibración (`/recalibrate/{sensor_id}`)

- [ ] **Step 25: Escribir los tests que fallan**

Reemplazar `backend/tests/test_recalibration.py` completo por:

```python
from pathlib import Path

import mlflow
from fastapi.testclient import TestClient

from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir, get_feedback_data_dir
from app.main import app
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset, save_dataset


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_recalibrate_returns_400_without_pending_corrections(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-no-corrections")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/forecast/sensor-a/run")
    response = client.post("/recalibrate/sensor-a")

    assert response.status_code == 400
    assert "correcciones" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_recalibrate_returns_404_when_no_forecast_ran_yet(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-no-feedback")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/recalibrate/sensor-a")

    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_recalibrate_registers_a_new_model_version_after_a_rejection(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-registers-version")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    forecast = client.post("/forecast/sensor-a/run").json()
    fecha = forecast["verdicts"][0]["fecha"]
    client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "test"},
    )

    response = client.post("/recalibrate/sensor-a")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1"
    assert body["n_correcciones"] == 1
    assert body["fechas_corregidas"] == [fecha]

    app.dependency_overrides.clear()


def test_recalibrating_one_sensor_does_not_affect_another(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-isolated-per-sensor")
    _seed_sensor_dataset("sensor-a", tmp_path)
    _seed_sensor_dataset("sensor-b", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    forecast_a = client.post("/forecast/sensor-a/run").json()
    client.post("/forecast/sensor-b/run")
    fecha = forecast_a["verdicts"][0]["fecha"]
    client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "test"},
    )
    client.post("/recalibrate/sensor-a")

    response_b = client.post("/recalibrate/sensor-b")

    assert response_b.status_code == 400  # sensor-b nunca tuvo rechazos propios

    app.dependency_overrides.clear()
```

- [ ] **Step 26: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_recalibration.py -v`
Expected: FAIL — `404 Not Found` (la ruta sigue siendo `/recalibrate`, sin `{sensor_id}`).

- [ ] **Step 27: Implementar el cambio**

Reemplazar `backend/app/routers/recalibration.py` completo por:

```python
"""Router de recalibración manual del modelo (spec alerting-ui,
requirement "Disparo manual de recalibración desde la interfaz, por
sensor").
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.model_registry import register_recalibrated_model
from human_feedback.recalibration import recalibrate_model, select_recalibration_observations
from human_feedback.registry import integrate_feedback_with_predictions, load_feedback_log

from ..config import get_dataset_data_dir, get_feedback_data_dir
from ..dependencies import get_valid_sensor_id
from ..pipeline import execute_configured_pipeline, load_dataset_or_raise
from ..schemas import RecalibrationResponse

router = APIRouter()


@router.post("/recalibrate/{sensor_id}", response_model=RecalibrationResponse)
def recalibrate(
    sensor_id: str = Depends(get_valid_sensor_id),
    dataset_dir: Path = Depends(get_dataset_data_dir),
    feedback_dir: Path = Depends(get_feedback_data_dir),
) -> RecalibrationResponse:
    try:
        feedback_log = load_feedback_log(feedback_log_name_for(sensor_id), data_dir=feedback_dir)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Todavía no se corrió ningún pronóstico."
        ) from error

    try:
        df, fingerprint = load_dataset_or_raise(sensor_id, data_dir=dataset_dir)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    result = execute_configured_pipeline(df, sensor_id, fingerprint, data_dir=dataset_dir)
    feature_cols = result["feature_columns"]
    train = result["train"]
    test = result["test"]

    predictions = pd.DataFrame(
        {
            "fecha": test["timestamp"].reset_index(drop=True),
            "y_proba": result["y_proba"].reset_index(drop=True),
            "stress_label": test["stress_label"].reset_index(drop=True),
        }
    )
    integrated = integrate_feedback_with_predictions(feedback_log, predictions)
    recalibration_obs = select_recalibration_observations(integrated)

    if recalibration_obs.empty:
        raise HTTPException(status_code=400, detail="No hay correcciones pendientes de aplicar.")

    X_recal = pd.concat([train[feature_cols], test[feature_cols]], ignore_index=True)
    y_recal = pd.concat([train["stress_label"], test["stress_label"]], ignore_index=True)
    dates_recal = pd.concat([train["timestamp"], test["timestamp"]], ignore_index=True)

    recalibrated_model, _ = recalibrate_model(
        result["model"], X_recal, y_recal, dates_recal, recalibration_obs
    )

    version = register_recalibrated_model(
        sensor_id,
        recalibrated_model,
        params={
            "n_correcciones": len(recalibration_obs),
            "model_name_previo": result["model_name"] or "modelo_recalibrado_previo",
        },
        metrics={"n_filas_entrenamiento": len(X_recal)},
    )

    return RecalibrationResponse(
        version=version,
        n_correcciones=len(recalibration_obs),
        fechas_corregidas=[d.date() for d in recalibration_obs["fecha"]],
    )
```

- [ ] **Step 28: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_recalibration.py -v`
Expected: PASS (los 4 tests).

- [ ] **Step 29: Correr toda la suite del proyecto**

Run: `pytest -q` (raíz) y `cd backend && python -m pytest tests -q`
Expected: PASS en ambos, sin romper nada de `add-mock-et0-derivation` ni de ningún change anterior.

- [ ] **Step 30: Commit**

```bash
git add src/human_feedback/model_registry.py tests/test_model_registry.py \
  backend/app/dependencies.py backend/tests/test_dependencies.py \
  backend/app/config.py backend/app/pipeline.py backend/tests/conftest.py backend/tests/test_pipeline.py \
  backend/app/routers/sensors.py backend/tests/test_sensors.py \
  backend/app/routers/feedback.py backend/tests/test_feedback.py \
  backend/app/routers/forecast.py backend/tests/test_forecast.py \
  backend/app/routers/recalibration.py backend/tests/test_recalibration.py
git commit -m "feat: agrega ruteo y aislamiento multi-sensor en el backend de alerting-ui"
```

---

### Task 3: Scripts de backfill y simulación de tráfico concurrente

**Files:**
- Modify: `scripts/seed_mock_sensor_dataset.py`
- Modify: `scripts/simulate_sensor_readings.py`
- Create: `scripts/simulate_multiple_sensors.py`

**Interfaces:**
- Consumes: `data_ingestion.mock_sensor.{seed_mock_dataset, generate_next_reading}` (ya existentes), `data_ingestion.sensor_naming.dataset_name_for` (Tarea 1), `POST /sensors/{sensor_id}/readings` (Tarea 2, vía HTTP).
- Produces: nada consumido por otro código — última tarea con dependencias del plan (Tarea 4 solo documenta).

- [ ] **Step 1: Actualizar el script de backfill**

Reemplazar `scripts/seed_mock_sensor_dataset.py` completo por:

```python
"""Genera un backfill inicial de lecturas sintéticas de sensor,
encadenadas por random walk acotado, y las guarda como el dataset
propio de `--sensor-id` (ADR-0007, ADR-0008).

Uso:
    python scripts/seed_mock_sensor_dataset.py --sensor-id sensor-melchor-1 \
        --start 2026-05-01 --end 2026-07-29
"""

from __future__ import annotations

import argparse
from datetime import date

from data_ingestion.mock_sensor import seed_mock_dataset
from data_ingestion.sensor_naming import dataset_name_for


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensor-id", required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_name = dataset_name_for(args.sensor_id)
    generated = seed_mock_dataset(
        dataset_name, start_date=args.start, end_date=args.end, random_state=args.random_state
    )
    print(f"Backfill generado: {len(generated)} filas, sensor '{args.sensor_id}' ({dataset_name}).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Actualizar el script de simulación de tráfico**

Reemplazar `scripts/simulate_sensor_readings.py` completo por:

```python
"""Simula una lectura de sensor y la envía al backend real vía HTTP
(ADR-0007) — cliente sintético del endpoint genérico
POST /sensors/{sensor_id}/readings (ADR-0008), que no sabe que el
llamador es un mock.

Uso:
    python scripts/simulate_sensor_readings.py --sensor-id sensor-melchor-1 \
        --backend-url http://localhost:8000
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import requests

from data_ingestion.mock_sensor import generate_next_reading
from data_ingestion.schema import PROVENANCE_COLUMN
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensor-id", required=True)
    parser.add_argument("--backend-url", default="http://localhost:8000")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        existing = load_dataset(dataset_name_for(args.sensor_id))
        previous = existing.sort_values("timestamp").iloc[-1]
    except FileNotFoundError:
        previous = None

    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    reading = generate_next_reading(previous, timestamp)

    payload = {
        "timestamp": reading["timestamp"].isoformat(),
        "soil_moisture": reading.get("soil_moisture"),
        "temperature": reading.get("temperature"),
        "relative_humidity": reading.get("relative_humidity"),
        "precipitation": reading.get("precipitation"),
        "solar_radiation": reading.get("solar_radiation"),
        "wind_speed": reading.get("wind_speed"),
        "procedencia": reading[PROVENANCE_COLUMN],
    }
    response = requests.post(
        f"{args.backend_url}/sensors/{args.sensor_id}/readings", json=payload, timeout=30
    )
    response.raise_for_status()
    print(f"Lectura enviada (sensor '{args.sensor_id}'): {response.json()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Crear el orquestador de sensores en paralelo**

Crear `scripts/simulate_multiple_sensors.py`:

```python
"""Lanza N instancias de `simulate_sensor_readings.py` en paralelo, una
por sensor, para generar tráfico concurrente real contra el backend
(ADR-0008) y poder observar cómo se comporta la arquitectura con
varios sensores en simultáneo.

Uso:
    python scripts/simulate_multiple_sensors.py \
        --sensor-ids sensor-melchor-1,sensor-melchor-2,sensor-melchor-3 \
        --backend-url http://localhost:8000 --rounds 5 --interval-seconds 2
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent / "simulate_sensor_readings.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensor-ids", required=True, help="Lista separada por comas.")
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--rounds", type=int, default=1, help="Lecturas a enviar por sensor.")
    parser.add_argument("--interval-seconds", type=float, default=0.0)
    return parser.parse_args()


def _send_one_reading(sensor_id: str, backend_url: str) -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--sensor-id", sensor_id, "--backend-url", backend_url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[{sensor_id}] ERROR: {result.stderr.strip()}")
    else:
        print(f"[{sensor_id}] {result.stdout.strip()}")


def main() -> None:
    args = parse_args()
    sensor_ids = [s.strip() for s in args.sensor_ids.split(",") if s.strip()]

    for round_number in range(1, args.rounds + 1):
        print(f"--- Ronda {round_number}/{args.rounds} ---")
        with ThreadPoolExecutor(max_workers=len(sensor_ids)) as executor:
            list(
                executor.map(
                    lambda sensor_id: _send_one_reading(sensor_id, args.backend_url), sensor_ids
                )
            )
        if round_number < args.rounds and args.interval_seconds > 0:
            time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verificación manual de punta a punta con múltiples sensores**

Con el stack corriendo (`docker compose up -d --build`, o `uvicorn app.main:app --port 8000` local desde `backend/`, y MLflow accesible):

```bash
python scripts/seed_mock_sensor_dataset.py --sensor-id sensor-melchor-1 --start 2026-05-01 --end 2026-07-29
python scripts/seed_mock_sensor_dataset.py --sensor-id sensor-melchor-2 --start 2026-05-01 --end 2026-07-29

python scripts/simulate_multiple_sensors.py \
  --sensor-ids sensor-melchor-1,sensor-melchor-2 \
  --backend-url http://localhost:8000 --rounds 3 --interval-seconds 1

curl -X POST http://localhost:8000/forecast/sensor-melchor-1/run
curl -X POST http://localhost:8000/forecast/sensor-melchor-2/run
```

Confirmar y documentar en el commit de este step (con los valores reales observados, no asumidos):
1. Los dos comandos de backfill imprimen `Backfill generado: 90 filas, sensor '...' (sensor__...)`.
2. `simulate_multiple_sensors.py` imprime 2 líneas por ronda (una por sensor), sin errores, y `filas_totales` de cada sensor sube de forma independiente ronda a ronda (91, 92, 93 para cada uno, en paralelo).
3. Los dos `curl` a `/forecast/{sensor_id}/run` devuelven `train_rows`/`test_rows`/alertas — confirmar que cada uno corre sobre su propio dataset (comparar `test_rows` de cada sensor contra la cantidad de filas de su propio backfill+tráfico).
4. Verificar en el archivo `data/` (o el volumen del contenedor) que existen `sensor__sensor-melchor-1.parquet` y `sensor__sensor-melchor-2.parquet` como archivos separados.

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_mock_sensor_dataset.py scripts/simulate_sensor_readings.py scripts/simulate_multiple_sensors.py
git commit -m "feat: agrega sensor_id a los scripts de sensor mock y un orquestador de sensores en paralelo"
```

---

### Task 4: Documentación de trazabilidad

**Files:**
- Modify: `docs/seguimiento-tareas.md`

**Interfaces:**
- Consumes: los resultados reales observados en la Tarea 3, Step 4.
- Produces: nada — última tarea del plan. Requerida por el hook `check-pr-traceability.sh` (bloquea `gh pr create` si se tocó `src/` sin actualizar este documento).

- [ ] **Step 1: Agregar una fila a la tabla de "Interfaz de usuario (alerting-ui, HU5+HU6)"**

En `docs/seguimiento-tareas.md`, agregar una fila nueva a la tabla de esa sección (después de la fila "Derivación de `et0` para lecturas de sensor mock"), con esta estructura — el primer y segundo párrafo de la columna "Evidencia / motivo" se copian tal cual (son afirmaciones sobre el código, ya verdaderas al terminar la Tarea 2), y el tercer párrafo ("Verificado con...") se redacta desde cero con los números reales que arrojó la Tarea 3, Step 4 (no se puede conocer su contenido antes de correr esa verificación):

```markdown
| Ingesta multi-sensor en paralelo | ✅ | `src/data_ingestion/sensor_naming.py` deriva nombres de dataset/feedback/modelo por `sensor_id`, validado contra `^[a-zA-Z0-9_-]{1,64}$`. Los cuatro routers de `alerting-ui` pasan a requerir `sensor_id` en la ruta (`POST /sensors/{sensor_id}/readings`, `POST /forecast/{sensor_id}/run`, `GET/POST /feedback/{sensor_id}/...`, `POST /recalibrate/{sensor_id}`); el caché de selección de modelo (`backend/app/pipeline.py::_selection_cache`) y el modelo recalibrado registrado en MLflow (`human_feedback/model_registry.py`) pasan a estar particionados por sensor. Ver `docs/adr/0008-ruteo-y-aislamiento-multi-sensor.md` y `openspec/changes/add-multi-sensor-ingestion/`. **Breaking change deliberado**: `frontend/ForecastPage.tsx` deja de funcionar contra este backend hasta que se le agregue un selector de sensor (fuera de alcance de este *change*, ver ADR-0008). |
```

Inmediatamente después de esa oración, agregar (en la misma celda) el párrafo de verificación real, redactado a partir de lo observado en la Tarea 3, Step 4. Debe incluir, con los valores concretos obtenidos (no antes de haberlos corrido): cuántas filas tenía cada dataset de sensor tras el backfill y tras las rondas de `simulate_multiple_sensors.py`; el `train_rows`/`test_rows`/cantidad de alertas que devolvió `POST /forecast/{sensor_id}/run` para cada uno de los dos sensores; y la confirmación de que `sensor__sensor-melchor-1.parquet` y `sensor__sensor-melchor-2.parquet` quedaron como archivos separados en `data/` (o en el volumen del contenedor). Seguir el estilo de las filas ya existentes en esta misma tabla (por ejemplo la fila "Ingesta de sensores en vivo (mock)") como referencia de nivel de detalle y tono.

- [ ] **Step 2: Actualizar la línea de "Fuera de alcance" de la misma sección**

Ubicar la línea que empieza con "**Fuera de alcance, documentado para la próxima iteración**" (al final de la sección "Interfaz de usuario") y agregarle, antes del punto final:

```markdown
; selector de sensor en el frontend (necesario porque los endpoints ahora requieren `sensor_id`, ver fila "Ingesta multi-sensor en paralelo").
```

- [ ] **Step 3: Commit**

```bash
git add docs/seguimiento-tareas.md
git commit -m "docs: registra la ingesta multi-sensor en seguimiento-tareas"
```
