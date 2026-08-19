# Recalibration Trigger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar el loop de retroalimentación humana de alerting-ui: un botón "Recalibrar modelo" en la UI reentrena el modelo con las alertas rechazadas y corregidas, registra el resultado en el Model Registry de MLflow, y el próximo pronóstico usa ese modelo recalibrado en vez de entrenar uno nuevo desde cero.

**Architecture:** El mecanismo de recalibración (`src/human_feedback/recalibration.py`) ya existe y está testeado desde HU5. Este plan agrega: (1) un flag `skip_fit` en `architecture_integration.run_end_to_end_pipeline` para poder predecir con un modelo ya entrenado sin descartar su ajuste; (2) un módulo `src/human_feedback/model_registry.py` que registra/recupera versiones en el Model Registry de MLflow; (3) un helper compartido en el backend que decide, en cada corrida, si usar el modelo recalibrado más reciente o entrenar uno nuevo; (4) un endpoint `POST /recalibrate` que junta train+test (con las etiquetas reales, corregidas donde el humano rechazó una alerta), selecciona las correcciones y registra el modelo resultante; (5) un botón en el frontend que dispara ese endpoint, visible solo cuando hay correcciones pendientes.

**Tech Stack:** Python (scikit-learn, mlflow>=2.14,<3, FastAPI), React + TypeScript (Vite), Docker Compose.

**Spec:** `openspec/changes/add-recalibration-trigger/proposal.md` y `openspec/changes/add-recalibration-trigger/specs/alerting-ui/spec.md`. Decisión arquitectónica: `docs/adr/0006-recalibracion-disparada-desde-la-ui.md`.

## Global Constraints

- El backend sigue siendo una fachada delgada (ADR-0003): toda la lógica de selección de observaciones, reentrenamiento y registro de modelo vive en `src/`; el backend solo orquesta y traduce a HTTP.
- MLflow lee su tracking URI de la variable de entorno `MLFLOW_TRACKING_URI` automáticamente — nunca hardcodear `mlflow.set_tracking_uri(...)` en código de producción (`src/` o `backend/app/`), solo en tests.
- Los tests que usan MLflow DEBEN usar un tracking store SQLite aislado por test (`sqlite:///{tmp_path}/mlflow.db`) y `mlflow.set_experiment(...)` con un nombre de experimento propio del test. Nunca usar un tracking store `file://` para estos tests: el Model Registry de MLflow no funciona con ese tipo de store (requiere un backend con base de datos). Nunca depender del servidor MLflow real de Docker en los tests.
- La recalibración es manual (un botón explícito en la UI) — no se dispara automáticamente por ningún umbral en esta iteración.
- No se agregan dependencias nuevas al frontend (`frontend/package.json` no cambia).
- Cada tarea termina con los tests de esa tarea en verde antes de pasar a la siguiente.

---

### Task 1: Flag `skip_fit` en `run_end_to_end_pipeline`

**Files:**
- Modify: `src/architecture_integration/pipeline.py:33-97`
- Test: `tests/test_architecture_integration_pipeline.py`

**Interfaces:**
- Consumes: nada nuevo — usa la firma existente de `run_end_to_end_pipeline`.
- Produces: `run_end_to_end_pipeline(..., skip_fit: bool = False)`. Cuando `skip_fit=True`, el `model` recibido se usa tal cual (ya entrenado) para predecir, sin `clone()` ni `.fit()`. El resto de tareas de este plan consumen este parámetro.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `tests/test_architecture_integration_pipeline.py`:

```python
def test_run_end_to_end_pipeline_with_skip_fit_true_does_not_refit_the_model():
    df = _synthetic_dataset()

    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("fit no debería llamarse cuando skip_fit=True")

        def predict_proba(self, X):
            return np.tile([0.3, 0.7], (len(X), 1))

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[45].date(),
        model=_FitRaisesModel(),
        include_anomaly_detection=False,
        skip_fit=True,
    )

    assert len(result["y_proba"]) == len(result["test"])
    assert all(p == 0.7 for p in result["y_proba"])
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_architecture_integration_pipeline.py::test_run_end_to_end_pipeline_with_skip_fit_true_does_not_refit_the_model -v`
Expected: FAIL — `run_end_to_end_pipeline() got an unexpected keyword argument 'skip_fit'` (o, si se agrega el parámetro sin la lógica, falla porque `_FitRaisesModel.fit` levanta `AssertionError`, ya que el código actual siempre clona y entrena).

- [ ] **Step 3: Implementar el flag**

En `src/architecture_integration/pipeline.py`, cambiar la firma de `run_end_to_end_pipeline` (línea 33) agregando el parámetro al final:

```python
def run_end_to_end_pipeline(
    df: pd.DataFrame,
    label_column: str,
    feature_columns: list[str],
    split_date: date,
    model: object,
    horizon_days: int = 3,
    percentile: float = 20.0,
    lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
    alert_threshold: float = 0.5,
    include_anomaly_detection: bool = True,
    contamination: float = 0.05,
    random_state: int = 42,
    skip_fit: bool = False,
) -> dict[str, Any]:
```

Y reemplazar el bloque de entrenamiento (líneas 81-82):

```python
    fitted_model = clone(model)
    fitted_model.fit(X_train, y_train)
```

por:

```python
    if skip_fit:
        fitted_model = model
    else:
        fitted_model = clone(model)
        fitted_model.fit(X_train, y_train)
```

Actualizar también el docstring de la función para mencionar el nuevo parámetro (una línea: "Si `skip_fit` es `True`, usa `model` tal cual, ya entrenado, sin reentrenar.").

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_architecture_integration_pipeline.py -v`
Expected: PASS (todos, incluyendo los 2 tests preexistentes en ese archivo — no deben romperse).

- [ ] **Step 5: Commit**

```bash
git add src/architecture_integration/pipeline.py tests/test_architecture_integration_pipeline.py
git commit -m "feat: agrega skip_fit a run_end_to_end_pipeline para reusar un modelo ya entrenado"
```

---

### Task 2: Registro y recuperación de modelos recalibrados en MLflow

**Files:**
- Create: `src/human_feedback/model_registry.py`
- Test: `tests/test_model_registry.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `register_recalibrated_model(model: object, params: dict, metrics: dict) -> str` (devuelve el número de versión como string) y `load_latest_recalibrated_model() -> object | None`. Consumidos por `backend/app/pipeline.py` (Task 3) y `backend/app/routers/recalibration.py` (Task 4).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_model_registry.py`:

```python
import mlflow
import pandas as pd
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
        model, params={"n_correcciones": 1}, metrics={"n_filas_entrenamiento": 4}
    )

    assert version == "1"
    loaded = load_latest_recalibrated_model()
    assert hasattr(loaded, "predict")
    assert list(loaded.predict(X)) == list(model.predict(X))


def test_load_latest_recalibrated_model_returns_none_when_nothing_registered(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-nothing-registered")

    assert load_latest_recalibrated_model() is None


def test_register_recalibrated_model_twice_returns_incrementing_versions(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-incrementing-versions")
    X = pd.DataFrame({"feature": [0, 1, 2, 3]})
    y = pd.Series([0, 0, 1, 1])
    model = LogisticRegression().fit(X, y)

    v1 = register_recalibrated_model(model, params={}, metrics={})
    v2 = register_recalibrated_model(model, params={}, metrics={})

    assert v1 == "1"
    assert v2 == "2"
    loaded = load_latest_recalibrated_model()
    assert hasattr(loaded, "predict")
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_model_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'human_feedback.model_registry'`.

- [ ] **Step 3: Implementar el módulo**

Crear `src/human_feedback/model_registry.py`:

```python
"""Registro y recuperación de versiones del modelo recalibrado en el
Model Registry de MLflow (spec alerting-ui, requirement "Disparo
manual de recalibración desde la interfaz" y "Uso del modelo
recalibrado en el próximo pronóstico").
"""

from __future__ import annotations

import mlflow
import mlflow.sklearn
from mlflow.exceptions import MlflowException

REGISTERED_MODEL_NAME = "alerting_ui_recalibrated_model"


def register_recalibrated_model(model: object, params: dict, metrics: dict) -> str:
    """Registra `model` como una nueva versión en el Model Registry de
    MLflow bajo `REGISTERED_MODEL_NAME`, junto con `params` y `metrics`
    en un run propio. Devuelve el número de versión registrada.
    """
    with mlflow.start_run(run_name="recalibracion") as run:
        for key, value in params.items():
            mlflow.log_param(key, value)
        for key, value in metrics.items():
            mlflow.log_metric(key, value)
        mlflow.sklearn.log_model(
            model, artifact_path="model", registered_model_name=REGISTERED_MODEL_NAME
        )
        run_id = run.info.run_id

    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
    matching = [v for v in versions if v.run_id == run_id]
    return matching[0].version


def load_latest_recalibrated_model() -> object | None:
    """Recupera la versión más reciente registrada en
    `REGISTERED_MODEL_NAME`, o `None` si todavía no se registró
    ninguna (primera corrida, sin recalibración previa).
    """
    client = mlflow.MlflowClient()
    try:
        versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
    except MlflowException:
        return None
    if not versions:
        return None
    latest = max(versions, key=lambda v: int(v.version))
    return mlflow.sklearn.load_model(f"models:/{REGISTERED_MODEL_NAME}/{latest.version}")
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_model_registry.py -v`
Expected: PASS (los 3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/human_feedback/model_registry.py tests/test_model_registry.py
git commit -m "feat: agrega registro y recuperación de modelos recalibrados en MLflow"
```

---

### Task 3: Helper compartido del backend y uso del modelo recalibrado en `/forecast/run`

**Files:**
- Create: `backend/app/pipeline.py`
- Modify: `backend/app/routers/forecast.py`
- Modify: `backend/tests/test_forecast.py`
- Test: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `run_end_to_end_pipeline(..., skip_fit=...)` (Task 1), `load_latest_recalibrated_model()` (Task 2).
- Produces: `execute_configured_pipeline(df: pd.DataFrame) -> dict` y `load_dataset_or_raise() -> pd.DataFrame` (levanta `FileNotFoundError` con mensaje explícito). Consumidos por `backend/app/routers/recalibration.py` (Task 4).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_pipeline.py`:

```python
import numpy as np

from app.config import DATASET_NAME
from app.pipeline import execute_configured_pipeline, load_dataset_or_raise
from data_ingestion.storage import load_dataset


def test_execute_configured_pipeline_trains_a_new_model_when_none_recalibrated(monkeypatch):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: None)
    df = load_dataset(DATASET_NAME)

    result = execute_configured_pipeline(df)

    assert hasattr(result["model"], "predict_proba")
    assert len(result["test"]) > 0


def test_execute_configured_pipeline_reuses_recalibrated_model_without_refitting(monkeypatch):
    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("no debería reentrenar cuando hay un modelo recalibrado")

        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    fake_model = _FitRaisesModel()
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: fake_model)
    df = load_dataset(DATASET_NAME)

    result = execute_configured_pipeline(df)

    assert result["model"] is fake_model


def test_load_dataset_or_raise_raises_file_not_found_with_explicit_message(monkeypatch):
    monkeypatch.setattr("app.pipeline.DATASET_NAME", "esto_no_existe")

    try:
        load_dataset_or_raise()
        assert False, "debería haber levantado FileNotFoundError"
    except FileNotFoundError as error:
        assert "esto_no_existe" in str(error)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.pipeline'`.

- [ ] **Step 3: Implementar el helper**

Crear `backend/app/pipeline.py`:

```python
"""Helper compartido de ejecución del pipeline de pronóstico (spec
alerting-ui, requirement "Uso del modelo recalibrado en el próximo
pronóstico"). Usado por `/forecast/run` y `/recalibrate` para no
duplicar la lógica de elección de modelo y llamada al pipeline.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.storage import load_dataset
from human_feedback.model_registry import load_latest_recalibrated_model
from predictive_modeling.models import build_candidate_models

from .config import DATASET_NAME, FEATURE_COLUMNS, LABEL_COLUMN, RANDOM_STATE


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
    usa sin reentrenar (`skip_fit=True`); si no, entrena un Random
    Forest nuevo, igual que antes de que existiera la recalibración.
    """
    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    recalibrated_model = load_latest_recalibrated_model()
    if recalibrated_model is not None:
        model = recalibrated_model
        skip_fit = True
    else:
        model = build_candidate_models(random_state=RANDOM_STATE)["random_forest"]
        skip_fit = False

    return run_end_to_end_pipeline(
        df,
        label_column=LABEL_COLUMN,
        feature_columns=FEATURE_COLUMNS,
        split_date=split_date,
        model=model,
        include_anomaly_detection=False,
        random_state=RANDOM_STATE,
        skip_fit=skip_fit,
    )
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: PASS (los 3 tests).

- [ ] **Step 5: Refactorizar `/forecast/run` para usar el helper**

Reemplazar el contenido completo de `backend/app/routers/forecast.py`:

```python
"""Router de ejecución de pronóstico (spec alerting-ui, requirement
"Ejecución de pronóstico desde la interfaz").
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from human_feedback.registry import load_feedback_log, save_feedback_log, upsert_feedback_log
from human_feedback.schema import init_feedback_log

from ..config import FEEDBACK_LOG_NAME, get_feedback_data_dir
from ..pipeline import execute_configured_pipeline, load_dataset_or_raise
from ..schemas import ForecastRunResponse, Verdict

router = APIRouter()


@router.post("/forecast/run", response_model=ForecastRunResponse)
def run_forecast(data_dir: Path = Depends(get_feedback_data_dir)) -> ForecastRunResponse:
    try:
        df = load_dataset_or_raise()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    result = execute_configured_pipeline(df)

    dates = result["test"]["timestamp"].reset_index(drop=True)
    alerts = result["alerts"].reset_index(drop=True)
    y_proba = result["y_proba"].reset_index(drop=True)

    try:
        existing_feedback = load_feedback_log(FEEDBACK_LOG_NAME, data_dir=data_dir)
        merged_feedback = upsert_feedback_log(existing_feedback, dates, alerts)
    except FileNotFoundError:
        merged_feedback = init_feedback_log(dates, alerts)
    save_feedback_log(FEEDBACK_LOG_NAME, merged_feedback, data_dir=data_dir)

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

**Nota importante:** este refactor mueve `DATASET_NAME` de `app.routers.forecast` a `app.pipeline`. El test existente `backend/tests/test_forecast.py::test_run_forecast_returns_404_when_dataset_missing` hace `monkeypatch.setattr("app.routers.forecast.DATASET_NAME", "esto_no_existe")`, que ya no tiene efecto porque ese atributo ya no existe en ese módulo. Actualizar ese test para apuntar al nuevo lugar:

En `backend/tests/test_forecast.py`, cambiar:

```python
    monkeypatch.setattr("app.routers.forecast.DATASET_NAME", "esto_no_existe")
```

por:

```python
    monkeypatch.setattr("app.pipeline.DATASET_NAME", "esto_no_existe")
```

- [ ] **Step 6: Correr toda la suite del backend y verificar que pasa**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS (todos los tests existentes de `test_forecast.py` y `test_feedback.py`, más los nuevos de `test_pipeline.py`).

- [ ] **Step 7: Commit**

```bash
git add backend/app/pipeline.py backend/app/routers/forecast.py backend/tests/test_pipeline.py backend/tests/test_forecast.py
git commit -m "refactor: extrae la ejecución del pipeline a un helper compartido y usa el modelo recalibrado si existe"
```

---

### Task 4: Endpoint `POST /recalibrate`

**Files:**
- Create: `backend/app/routers/recalibration.py`
- Create: `backend/tests/test_recalibration.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `execute_configured_pipeline`, `load_dataset_or_raise` (Task 3); `register_recalibrated_model` (Task 2); `select_recalibration_observations`, `recalibrate_model` (ya existentes en `src/human_feedback/recalibration.py`); `integrate_feedback_with_predictions`, `load_feedback_log` (ya existentes en `src/human_feedback/registry.py`).
- Produces: `POST /recalibrate` devolviendo `RecalibrationResponse`. Consumido por el frontend (Task 5).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_recalibration.py`:

```python
from pathlib import Path

import mlflow
from fastapi.testclient import TestClient

from app.config import get_feedback_data_dir
from app.main import app


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def test_recalibrate_returns_400_without_pending_corrections(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-no-corrections")
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/forecast/run")
    response = client.post("/recalibrate")

    assert response.status_code == 400
    assert "correcciones" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_recalibrate_returns_404_when_no_forecast_ran_yet(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-no-feedback")
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/recalibrate")

    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_recalibrate_registers_a_new_model_version_after_a_rejection(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-registers-version")
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    forecast = client.post("/forecast/run").json()
    fecha = forecast["verdicts"][0]["fecha"]
    client.post(
        f"/feedback/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "test"},
    )

    response = client.post("/recalibrate")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1"
    assert body["n_correcciones"] == 1
    assert body["fechas_corregidas"] == [fecha]

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_recalibration.py -v`
Expected: FAIL — `404 Not Found` en todos (la ruta `/recalibrate` no existe todavía).

- [ ] **Step 3: Agregar el schema de respuesta**

En `backend/app/schemas.py`, agregar al final:

```python
class RecalibrationResponse(BaseModel):
    version: str
    n_correcciones: int
    fechas_corregidas: list[date]
```

- [ ] **Step 4: Implementar el router**

Crear `backend/app/routers/recalibration.py`:

```python
"""Router de recalibración manual del modelo (spec alerting-ui,
requirement "Disparo manual de recalibración desde la interfaz").
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from human_feedback.model_registry import register_recalibrated_model
from human_feedback.recalibration import recalibrate_model, select_recalibration_observations
from human_feedback.registry import integrate_feedback_with_predictions, load_feedback_log

from ..config import FEEDBACK_LOG_NAME, get_feedback_data_dir
from ..pipeline import execute_configured_pipeline, load_dataset_or_raise
from ..schemas import RecalibrationResponse

router = APIRouter()


@router.post("/recalibrate", response_model=RecalibrationResponse)
def recalibrate(data_dir: Path = Depends(get_feedback_data_dir)) -> RecalibrationResponse:
    try:
        feedback_log = load_feedback_log(FEEDBACK_LOG_NAME, data_dir=data_dir)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Todavía no se corrió ningún pronóstico."
        ) from error

    try:
        df = load_dataset_or_raise()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    result = execute_configured_pipeline(df)
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
        raise HTTPException(
            status_code=400, detail="No hay correcciones pendientes de aplicar."
        )

    X_recal = pd.concat([train[feature_cols], test[feature_cols]], ignore_index=True)
    y_recal = pd.concat([train["stress_label"], test["stress_label"]], ignore_index=True)
    dates_recal = pd.concat([train["timestamp"], test["timestamp"]], ignore_index=True)

    recalibrated_model, _ = recalibrate_model(
        result["model"], X_recal, y_recal, dates_recal, recalibration_obs
    )

    version = register_recalibrated_model(
        recalibrated_model,
        params={"n_correcciones": len(recalibration_obs)},
        metrics={"n_filas_entrenamiento": len(X_recal)},
    )

    return RecalibrationResponse(
        version=version,
        n_correcciones=len(recalibration_obs),
        fechas_corregidas=[d.date() for d in recalibration_obs["fecha"]],
    )
```

- [ ] **Step 5: Registrar el router en la app**

En `backend/app/main.py`, cambiar:

```python
from .routers import feedback, forecast
```

por:

```python
from .routers import feedback, forecast, recalibration
```

y agregar, después de `app.include_router(feedback.router)`:

```python
app.include_router(recalibration.router)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_recalibration.py -v`
Expected: PASS (los 3 tests).

- [ ] **Step 7: Correr toda la suite del backend**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS (todos, sin romper nada de las tareas anteriores).

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/recalibration.py backend/tests/test_recalibration.py backend/app/schemas.py backend/app/main.py
git commit -m "feat: agrega el endpoint POST /recalibrate"
```

---

### Task 5: Botón "Recalibrar modelo" en el frontend

**Files:**
- Modify: `frontend/src/features/forecast/api.ts`
- Modify: `frontend/src/features/forecast/ForecastPage.tsx`
- Modify: `frontend/src/features/forecast/ForecastPage.css`
- Modify: `frontend/src/features/forecast/ForecastPage.test.tsx`

**Interfaces:**
- Consumes: `POST /recalibrate` (Task 4).
- Produces: nada consumido por tareas posteriores (última tarea de código de este plan).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `frontend/src/features/forecast/ForecastPage.test.tsx`:

```tsx
  it("shows a recalibrate button only when there is a pending correction, and using it shows the registered version", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "rechazada",
          etiqueta_corregida: 0,
          observacion: "test",
        },
      ],
    });
    vi.spyOn(api, "recalibrate").mockResolvedValue({
      version: "1",
      n_correcciones: 1,
      fechas_corregidas: ["2024-10-31"],
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));
    await waitFor(() => screen.getByRole("button", { name: /recalibrar modelo/i }));

    await userEvent.click(screen.getByRole("button", { name: /recalibrar modelo/i }));

    await waitFor(() => {
      expect(screen.getByText(/versión 1/i)).toBeInTheDocument();
    });
  });

  it("does not show the recalibrate button when there are no pending corrections", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
        },
      ],
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));
    await waitFor(() => screen.getByText("2024-10-31"));

    expect(
      screen.queryByRole("button", { name: /recalibrar modelo/i }),
    ).not.toBeInTheDocument();
  });
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd frontend && npm run test`
Expected: FAIL — `api.recalibrate` no existe (`TypeError` o el botón nunca aparece).

- [ ] **Step 3: Agregar `recalibrate` a la API**

En `frontend/src/features/forecast/api.ts`, agregar después de `rejectAlert`:

```ts
export interface RecalibrationResponse {
  version: string;
  n_correcciones: number;
  fechas_corregidas: string[];
}

export async function recalibrate(): Promise<RecalibrationResponse> {
  const response = await fetch(`${API_BASE_URL}/recalibrate`, { method: "POST" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Error al recalibrar el modelo: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 4: Agregar el botón y el estado en `ForecastPage.tsx`**

Reemplazar el contenido completo de `frontend/src/features/forecast/ForecastPage.tsx`:

```tsx
import { useState } from "react";
import "./ForecastPage.css";
import {
  confirmAlert,
  listFeedback,
  recalibrate,
  rejectAlert,
  runForecast,
} from "./api";
import type { FeedbackRow, Verdict } from "./api";

export function ForecastPage() {
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [feedback, setFeedback] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [recalibrating, setRecalibrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const pendingCorrections = feedback.filter(
    (row) => row.estado_validacion === "rechazada" && row.etiqueta_corregida !== null,
  ).length;

  async function handleRunForecast() {
    setLoading(true);
    setError(null);
    setActionMessage(null);
    try {
      const result = await runForecast();
      setVerdicts(result.verdicts);
      const feedbackResult = await listFeedback();
      setFeedback(feedbackResult.rows);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(fecha: string) {
    const updated = await confirmAlert(fecha);
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
    setActionMessage(`Guardada la validación del ${fecha} — el modelo no se actualizó.`);
  }

  async function handleReject(fecha: string) {
    const updated = await rejectAlert(fecha, 0, "Rechazada desde la interfaz");
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
    setActionMessage(`Guardada la validación del ${fecha} — el modelo no se actualizó.`);
  }

  async function handleRecalibrate() {
    setRecalibrating(true);
    setError(null);
    try {
      const result = await recalibrate();
      setActionMessage(
        `Modelo recalibrado (versión ${result.version}) usando ${result.n_correcciones} corrección(es) — el próximo pronóstico usará este modelo.`,
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRecalibrating(false);
    }
  }

  function stateFor(fecha: string): string {
    return feedback.find((row) => row.fecha === fecha)?.estado_validacion ?? "pendiente";
  }

  return (
    <div className="fp-page">
      <header className="fp-header">
        <div>
          <h1 className="fp-title">Pronóstico de estrés hídrico</h1>
          <p className="fp-subtitle">Validación humana de alertas sobre el dataset consolidado</p>
        </div>
        <div className="fp-header-actions">
          {pendingCorrections > 0 && (
            <button
              className="fp-recalibrate-btn"
              onClick={handleRecalibrate}
              disabled={recalibrating}
            >
              {recalibrating ? "Recalibrando..." : `Recalibrar modelo (${pendingCorrections})`}
            </button>
          )}
          <button className="fp-run-btn" onClick={handleRunForecast} disabled={loading}>
            {loading ? "Corriendo..." : "Correr pronóstico"}
          </button>
        </div>
      </header>

      <div className="fp-banner" role="note">
        <strong>Qué prueba esta pantalla:</strong> confirmar o rechazar guarda tu validación en
        el registro de retroalimentación. Recalibrar reentrena el modelo con las correcciones
        acumuladas y registra una nueva versión — el próximo pronóstico usará esa versión.
      </div>

      {error && <p role="alert" className="fp-error">{error}</p>}
      {actionMessage && (
        <p role="status" className="fp-action-message">
          {actionMessage}
        </p>
      )}

      <ul className="fp-list">
        {verdicts.map((verdict) => {
          const estado = stateFor(verdict.fecha);
          const severity = verdict.alerta ? "alert" : "safe";
          return (
            <li key={verdict.fecha} className={`fp-row fp-row--${severity}`}>
              <span className="fp-signal" aria-hidden="true" />
              <div className="fp-row-main">
                <div className="fp-row-date">{verdict.fecha}</div>
                <div className="fp-row-verdict">{verdict.alerta ? "Alerta" : "Sin alerta"}</div>
              </div>
              <div className="fp-gauge">
                <span className="fp-gauge-value">{verdict.probabilidad.toFixed(2)}</span>
                <span className="fp-gauge-bar">
                  <span
                    className="fp-gauge-fill"
                    style={{ width: `${Math.round(verdict.probabilidad * 100)}%` }}
                  />
                </span>
              </div>
              <span className={`fp-badge fp-badge--${estado}`}>{estado}</span>
              <div className="fp-actions">
                <button onClick={() => handleConfirm(verdict.fecha)}>Confirmar</button>
                <button onClick={() => handleReject(verdict.fecha)}>Rechazar</button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

Nota sobre el texto del banner: cambia respecto de la versión anterior porque ahora recalibrar **sí** tiene un efecto real sobre el modelo — no se debe dejar el texto viejo ("no se reentrena el modelo automáticamente") que quedaría contradicho por este mismo cambio.

- [ ] **Step 5: Agregar estilos para el nuevo botón**

En `frontend/src/features/forecast/ForecastPage.css`, agregar después de la regla `.fp-run-btn:disabled`:

```css
.fp-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.fp-recalibrate-btn {
  padding: 0.7rem 1.4rem;
  border: 1px solid var(--fp-action);
  border-radius: 6px;
  background: var(--fp-action-bg);
  color: var(--fp-action);
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
}

.fp-recalibrate-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `cd frontend && npm run test`
Expected: PASS (los 4 tests: los 2 preexistentes más los 2 nuevos).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/forecast/api.ts frontend/src/features/forecast/ForecastPage.tsx frontend/src/features/forecast/ForecastPage.css frontend/src/features/forecast/ForecastPage.test.tsx
git commit -m "feat: agrega el botón de recalibrar modelo al frontend"
```

---

### Task 6: Infraestructura Docker y documentación

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `openspec/specs/human-feedback/spec.md`
- Modify: `openspec/specs/alerting-ui/spec.md`
- Modify: `docs/seguimiento-tareas.md`

**Interfaces:**
- Consumes: nada de código — cierra el plan con infraestructura y documentación de las tareas 1-5.
- Produces: nada consumido por otras tareas.

- [ ] **Step 1: Acoplar `backend` a `mlflow` en `docker-compose.yml`**

En `docker-compose.yml`, reemplazar el bloque del servicio `backend`:

```yaml
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    depends_on:
      - mlflow
    environment:
      ALERTING_UI_DATASET: ${ALERTING_UI_DATASET:-melchor_romero_2024_consolidado}
      MLFLOW_TRACKING_URI: http://mlflow:5000
    ports:
      - "8000:8000"
    volumes:
      - ./data:/workspace/data
```

- [ ] **Step 2: Documentar la nueva variable en `.env.example`**

En `.env.example`, después del comentario "Variables que debe leer el código de HU3/HU4 al registrar experimentos:", agregar una línea de comentario:

```
# También la lee el backend de alerting-ui desde ADR-0006 (recalibración).
```

- [ ] **Step 3: Actualizar la limitación resuelta en `openspec/specs/human-feedback/spec.md`**

En la sección "## Limitaciones conocidas", reemplazar la línea:

```
- La recalibración no se dispara automáticamente desde la interfaz de usuario ni se persiste el modelo recalibrado; ambas cosas requieren un flujo de despliegue que todavía no existe.
```

por:

```
- ~~La recalibración no se dispara automáticamente desde la interfaz de usuario ni se persiste el modelo recalibrado; ambas cosas requieren un flujo de despliegue que todavía no existe.~~ **Actualización (2026-08-19):** resuelto — ver `openspec/specs/alerting-ui/spec.md`, requirement "Disparo manual de recalibración desde la interfaz" (`POST /recalibrate`, registro versionado en el Model Registry de MLflow, ADR-0006).
```

- [ ] **Step 4: Fusionar los requirements nuevos en `openspec/specs/alerting-ui/spec.md`**

Agregar al final de `openspec/specs/alerting-ui/spec.md`, después del último requirement existente, los dos requirements de `openspec/changes/add-recalibration-trigger/specs/alerting-ui/spec.md` (copiar tal cual: "Disparo manual de recalibración desde la interfaz" y "Uso del modelo recalibrado en el próximo pronóstico"), agregando debajo de cada uno una línea de implementación con evidencia, siguiendo el formato ya usado en el resto del archivo, por ejemplo:

```
Implementado en `backend/app/routers/recalibration.py` (`POST /recalibrate`) y `src/human_feedback/model_registry.py`. Testeado en `backend/tests/test_recalibration.py` y `tests/test_model_registry.py`. Verificado sobre datos reales: ver `docs/seguimiento-tareas.md`.
```

(el implementador debe ajustar esta línea si los nombres de archivo reales difieren de los de este plan).

- [ ] **Step 5: Actualizar `docs/seguimiento-tareas.md`**

En la sección "## Interfaz de usuario (alerting-ui, HU5+HU6)", agregar una fila a la tabla:

```
| Disparo de recalibración desde la UI | ✅ | `src/human_feedback/model_registry.py`, `backend/app/routers/recalibration.py`, botón "Recalibrar modelo" en `ForecastPage.tsx`. Ver `docs/adr/0006-recalibracion-disparada-desde-la-ui.md`. Verificado: se rechazó una alerta real, se recalibró (versión 1 registrada en MLflow), y el siguiente pronóstico usó ese modelo sin reentrenar. |
```

Y quitar "disparo de recalibración desde la UI" de la lista de "Fuera de alcance, documentado para la próxima iteración" al final de esa sección (ya se implementó).

- [ ] **Step 6: Verificación manual de punta a punta**

Levantar el stack completo (`docker compose up -d --build`), confirmar que `backend` arranca después de `mlflow` sin error de conexión, correr un pronóstico desde la UI, rechazar una alerta, apretar "Recalibrar modelo", confirmar que aparece el mensaje con la versión registrada, correr el pronóstico de nuevo y confirmar (por los logs del backend o por comportamiento) que no vuelve a entrenar desde cero. Documentar el resultado real (no asumido) en el Step 5 de este mismo commit si difiere de lo esperado.

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml .env.example openspec/specs/human-feedback/spec.md openspec/specs/alerting-ui/spec.md docs/seguimiento-tareas.md
git commit -m "docs: documenta el disparo de recalibración y acopla backend a mlflow en docker-compose"
```
