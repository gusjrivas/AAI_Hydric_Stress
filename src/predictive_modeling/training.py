"""Entrenamiento de modelos candidatos y ajuste de hiperparámetros con
validación temporal (spec predictive-modeling, requirements
"Entrenamiento de modelos candidatos" y "Ajuste de hiperparámetros con
validación temporal").
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit


def train_models(
    models: dict[str, object], X_train: pd.DataFrame, y_train: pd.Series
) -> dict[str, object]:
    """Entrena una copia de cada modelo en `models` sobre `X_train`/`y_train`
    y devuelve los modelos ya entrenados.
    """
    fitted = {}
    for name, model in models.items():
        trained = clone(model)
        trained.fit(X_train, y_train)
        fitted[name] = trained
    return fitted


def tune_hyperparameters(
    model: object,
    param_grid: dict[str, list],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int = 5,
    scoring: str = "f1",
) -> dict[str, Any]:
    """Ajusta los hiperparámetros de `model` con `GridSearchCV` usando
    `TimeSeriesSplit` (respeta el orden temporal: cada fold de
    validación es posterior a su fold de entrenamiento correspondiente,
    sin mezclar ni recortar el conjunto de entrenamiento original).
    Devuelve el mejor estimador ya entrenado, sus mejores parámetros, y
    la media/desvío de `scoring` entre los folds de validación cruzada
    (indicador de estabilidad).
    """
    splitter = TimeSeriesSplit(n_splits=n_splits)
    search = GridSearchCV(clone(model), param_grid=param_grid, cv=splitter, scoring=scoring)
    search.fit(X_train, y_train)

    best_index = search.best_index_
    cv_results = search.cv_results_

    return {
        "best_estimator": search.best_estimator_,
        "best_params": search.best_params_,
        "cv_mean_score": float(cv_results["mean_test_score"][best_index]),
        "cv_std_score": float(cv_results["std_test_score"][best_index]),
    }
