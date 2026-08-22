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

    best_name = max(
        results,
        key=lambda name: (results[name]["cv_mean_score"], name == "random_forest"),
    )
    best = results[best_name]

    return {
        "model": best["best_estimator"],
        "model_name": best_name,
        "cv_mean_score": best["cv_mean_score"],
        "cv_std_score": best["cv_std_score"],
    }
