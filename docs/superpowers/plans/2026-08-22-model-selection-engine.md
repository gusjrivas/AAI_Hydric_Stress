# Model Selection Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el Random Forest fijo que hoy usa el pipeline en producción por un motor que elige automáticamente, entre los modelos candidatos de HU4, el de mejor `cv_mean_score` de validación cruzada temporal — sin tocar la recalibración ni ningún llamador que ya pasa un modelo explícito.

**Architecture:** Un módulo nuevo (`predictive_modeling.model_selection.select_best_candidate`) envuelve `tune_hyperparameters` (ya existente) llamándolo una vez por candidato y quedándose con el de mayor `cv_mean_score`. `run_end_to_end_pipeline` lo usa cuando `model=None`; con un `model` explícito, el comportamiento es idéntico al actual. `backend/app/pipeline.py` deja de construir un Random Forest a mano y pasa `model=None` cuando no hay modelo recalibrado.

**Tech Stack:** Python (scikit-learn `GridSearchCV`/`TimeSeriesSplit`, ya en uso), pytest.

**Spec:** `openspec/changes/add-model-selection-engine/proposal.md`, `openspec/changes/add-model-selection-engine/specs/predictive-modeling/spec.md`, `openspec/changes/add-model-selection-engine/specs/architecture-integration/spec.md`.

## Global Constraints

- No se agregan dependencias nuevas.
- `select_best_candidate` reutiliza `build_candidate_models`, `DEFAULT_HYPERPARAMETER_GRIDS` (`src/predictive_modeling/models.py`) y `tune_hyperparameters` (`src/predictive_modeling/training.py`) **sin modificarlos**.
- `run_end_to_end_pipeline` debe seguir siendo 100% retrocompatible cuando se pasa un `model` explícito: mismo comportamiento que antes de este *change*, incluyendo `skip_fit` (usado por la recalibración, `openspec/changes/add-recalibration-trigger/`) y todos los tests existentes que pasan un modelo.
- `src/experiment_runner/runner.py` (`run_configuration`) no se modifica — sigue recibiendo `model_name` fijo, para no alterar retroactivamente los resultados ya registrados de HU7/HU8.
- La respuesta HTTP de `POST /forecast/run` no cambia — sigue sin exponer qué modelo generó el pronóstico (`openspec/specs/alerting-ui/spec.md`).
- Cada tarea termina con sus tests en verde antes de pasar a la siguiente; al final de la Tarea 3, correr toda la suite (`pytest -q` + `pytest backend/tests -q`).

---

### Task 1: Motor de selección automática entre candidatos

**Files:**
- Create: `src/predictive_modeling/model_selection.py`
- Test: `tests/test_model_selection.py`

**Interfaces:**
- Consumes: `build_candidate_models`, `DEFAULT_HYPERPARAMETER_GRIDS` (`src/predictive_modeling/models.py`, ya existentes); `tune_hyperparameters` (`src/predictive_modeling/training.py`, ya existente, firma `tune_hyperparameters(model, param_grid, X_train, y_train, n_splits=5, scoring="f1") -> dict` con claves `best_estimator`, `best_params`, `cv_mean_score`, `cv_std_score`).
- Produces: `select_best_candidate(X_train: pd.DataFrame, y_train: pd.Series, candidates: dict[str, object] | None = None, param_grids: dict[str, dict[str, list]] | None = None, n_splits: int = 5, scoring: str = "f1", random_state: int = 42) -> dict[str, Any]` con claves `model` (estimador ya ajustado), `model_name` (str), `cv_mean_score` (float), `cv_std_score` (float). Consumido por Tarea 2.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_model_selection.py`:

```python
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier

from predictive_modeling.model_selection import select_best_candidate


def _separable_dataset(n=120, seed=0):
    rng = np.random.default_rng(seed)
    feature = rng.normal(0, 1, size=n)
    target = (feature > 0).astype(int)
    X = pd.DataFrame({"feature": feature})
    y = pd.Series(target, name="stress_label")
    return X, y


def test_select_best_candidate_uses_default_candidates_and_grids():
    X, y = _separable_dataset()

    result = select_best_candidate(X, y, n_splits=4)

    assert result["model_name"] in {"logistic_regression", "random_forest"}
    assert hasattr(result["model"], "predict_proba")
    assert "cv_mean_score" in result
    assert "cv_std_score" in result


def test_select_best_candidate_picks_the_higher_cv_mean_score():
    X, y = _separable_dataset(n=150, seed=1)

    candidates = {
        "bad": DummyClassifier(strategy="constant", constant=0),
        "good": RandomForestClassifier(random_state=0),
    }
    param_grids = {"bad": {}, "good": {"n_estimators": [50]}}

    result = select_best_candidate(
        X, y, candidates=candidates, param_grids=param_grids, n_splits=4
    )

    assert result["model_name"] == "good"
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_model_selection.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'predictive_modeling.model_selection'`.

- [ ] **Step 3: Implementar el módulo**

Crear `src/predictive_modeling/model_selection.py`:

```python
"""Selección automática del mejor modelo candidato por validación
cruzada temporal (spec predictive-modeling, requirement "Selección
automática del mejor modelo candidato").
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from predictive_modeling.models import DEFAULT_HYPERPARAMETER_GRIDS, build_candidate_models
from predictive_modeling.training import tune_hyperparameters


def select_best_candidate(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    candidates: dict[str, object] | None = None,
    param_grids: dict[str, dict[str, list]] | None = None,
    n_splits: int = 5,
    scoring: str = "f1",
    random_state: int = 42,
) -> dict[str, Any]:
    """Ajusta cada modelo de `candidates` con `tune_hyperparameters`
    (validación cruzada temporal) y devuelve el de mayor `cv_mean_score`,
    ya entrenado sobre `X_train`/`y_train` completos. Si no se
    especifican `candidates`/`param_grids`, usa `build_candidate_models`
    y `DEFAULT_HYPERPARAMETER_GRIDS` (HU4) por defecto.
    """
    candidates = candidates if candidates is not None else build_candidate_models(random_state)
    param_grids = param_grids if param_grids is not None else DEFAULT_HYPERPARAMETER_GRIDS

    results = {}
    for name, model in candidates.items():
        results[name] = tune_hyperparameters(
            model, param_grids[name], X_train, y_train, n_splits=n_splits, scoring=scoring
        )

    best_name = max(results, key=lambda name: results[name]["cv_mean_score"])
    best = results[best_name]

    return {
        "model": best["best_estimator"],
        "model_name": best_name,
        "cv_mean_score": best["cv_mean_score"],
        "cv_std_score": best["cv_std_score"],
    }
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_model_selection.py -v`
Expected: PASS (los 2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/predictive_modeling/model_selection.py tests/test_model_selection.py
git commit -m "feat: agrega el motor de selección automática entre modelos candidatos"
```

---

### Task 2: Usar el motor de selección en `run_end_to_end_pipeline` cuando no se especifica un modelo

**Files:**
- Modify: `src/architecture_integration/pipeline.py`
- Test: `tests/test_architecture_integration_pipeline.py`

**Interfaces:**
- Consumes: `select_best_candidate` (Tarea 1).
- Produces: `run_end_to_end_pipeline(..., model: object | None = None, ...)` — con `model` explícito, comportamiento idéntico al actual (incluyendo `skip_fit`); con `model=None`, selecciona automáticamente. `result["model_name"]` es `None` si se pasó un modelo explícito, o el nombre del candidato ganador si se seleccionó. Consumido por Tarea 3.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_architecture_integration_pipeline.py`:

```python
def test_run_end_to_end_pipeline_selects_a_model_automatically_when_none_given():
    df = _synthetic_dataset(n=150, seed=2)

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[110].date(),
        model=None,
        include_anomaly_detection=False,
    )

    assert result["model_name"] in {"logistic_regression", "random_forest"}
    assert hasattr(result["model"], "predict_proba")
    assert len(result["y_proba"]) == len(result["test"])


def test_run_end_to_end_pipeline_leaves_model_name_none_when_model_is_given():
    df = _synthetic_dataset()
    model = build_candidate_models(random_state=0)["logistic_regression"]

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[45].date(),
        model=model,
        include_anomaly_detection=False,
    )

    assert result["model_name"] is None
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_architecture_integration_pipeline.py -v`
Expected: `test_run_end_to_end_pipeline_selects_a_model_automatically_when_none_given` FAIL (hoy `model=None` termina intentando `clone(None)` dentro de la rama `else`, lo que levanta un error de scikit-learn); `test_run_end_to_end_pipeline_leaves_model_name_none_when_model_is_given` FAIL con `KeyError: 'model_name'`. Los demás tests preexistentes deben seguir en PASS.

- [ ] **Step 3: Implementar el cambio**

En `src/architecture_integration/pipeline.py`, agregar el import (después de `from predictive_modeling.labeling import add_stress_label`, línea 30):

```python
from predictive_modeling.model_selection import select_best_candidate
```

Cambiar la firma de la función (línea 38):

```python
    model: object,
```

por:

```python
    model: object | None = None,
```

Actualizar el docstring (líneas 49-56), agregando una frase: "Si `model` es `None`, selecciona automáticamente el mejor candidato (`predictive_modeling.model_selection.select_best_candidate`) en vez de usar un modelo fijo."

Reemplazar el bloque (líneas 85-89):

```python
    if skip_fit:
        fitted_model = model
    else:
        fitted_model = clone(model)
        fitted_model.fit(X_train, y_train)
```

por:

```python
    model_name = None
    if model is None:
        selection = select_best_candidate(X_train, y_train, random_state=random_state)
        fitted_model = selection["model"]
        model_name = selection["model_name"]
    elif skip_fit:
        fitted_model = model
    else:
        fitted_model = clone(model)
        fitted_model.fit(X_train, y_train)
```

Y agregar `"model_name": model_name` al diccionario de retorno (después de `"model": fitted_model,`):

```python
    return {
        "quality_report": report,
        "train": train,
        "test": test,
        "feature_columns": feature_cols,
        "model": fitted_model,
        "model_name": model_name,
        "y_proba": y_proba,
        "alerts": alerts,
        "feedback_log": feedback_log,
    }
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_architecture_integration_pipeline.py -v`
Expected: PASS (todos: los 6 preexistentes más los 2 nuevos).

- [ ] **Step 5: Commit**

```bash
git add src/architecture_integration/pipeline.py tests/test_architecture_integration_pipeline.py
git commit -m "feat: usa el motor de selección automática cuando no se especifica un modelo"
```

---

### Task 3: Conectar la selección automática al backend de `alerting-ui`

**Files:**
- Modify: `backend/app/pipeline.py`
- Test: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `run_end_to_end_pipeline(..., model=None, ...)` con `result["model_name"]` (Tarea 2).
- Produces: sin cambios de firma en `execute_configured_pipeline`. Última tarea del plan — nada consumido por tareas posteriores.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `backend/tests/test_pipeline.py`:

```python
def test_execute_configured_pipeline_selects_a_model_automatically_when_none_recalibrated(
    monkeypatch,
):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: None)
    df = load_dataset(DATASET_NAME)

    result = execute_configured_pipeline(df)

    assert result["model_name"] in {"logistic_regression", "random_forest"}
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `result["model_name"]` es `None` (hoy `execute_configured_pipeline` siempre pasa un `model` explícito de Random Forest, así que `run_end_to_end_pipeline` nunca activa la selección), y `None not in {"logistic_regression", "random_forest"}`.

- [ ] **Step 3: Implementar el cambio**

En `backend/app/pipeline.py`, quitar el import ya no usado (línea 16):

```python
from predictive_modeling.models import build_candidate_models
```

Actualizar el docstring de `execute_configured_pipeline` (líneas 32-36), reemplazando "si no, entrena un Random Forest nuevo, igual que antes de que existiera la recalibración." por "si no, deja que `run_end_to_end_pipeline` seleccione automáticamente el mejor modelo candidato (`predictive_modeling.model_selection`)."

Reemplazar el bloque (líneas 39-45):

```python
    recalibrated_model = load_latest_recalibrated_model()
    if recalibrated_model is not None:
        model = recalibrated_model
        skip_fit = True
    else:
        model = build_candidate_models(random_state=RANDOM_STATE)["random_forest"]
        skip_fit = False
```

por:

```python
    recalibrated_model = load_latest_recalibrated_model()
    if recalibrated_model is not None:
        model = recalibrated_model
        skip_fit = True
    else:
        model = None
        skip_fit = False
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: PASS (los 4 tests: los 3 preexistentes más el nuevo).

- [ ] **Step 5: Correr toda la suite del proyecto**

Run: `pytest -q` y `cd backend && python -m pytest tests/ -q`
Expected: PASS en ambos (sin romper nada de las tareas anteriores ni de `add-recalibration-trigger`/`fix-anomaly-feature-integration`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: conecta el motor de selección automática al backend de alerting-ui"
```
