"""Entrenamiento de modelos candidatos y ajuste de hiperparámetros con
validación temporal (spec predictive-modeling, requirements
"Entrenamiento de modelos candidatos" y "Ajuste de hiperparámetros con
validación temporal").
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.base import clone
from sklearn.metrics import f1_score
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


def _binary_f1(estimator, X, y):
    """Explicit stress class even when a fold's fitted model only knows class 0."""
    return f1_score(y, estimator.predict(X), pos_label=1, zero_division=0)


def tune_hyperparameters(
    model: object,
    param_grid: dict[str, list],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int = 5,
    scoring: str = "f1",
    gap: int = 0,
) -> dict[str, Any]:
    """Ajusta los hiperparámetros de `model` con `GridSearchCV` usando
    `TimeSeriesSplit` (respeta el orden temporal: cada fold de
    validación es posterior a su fold de entrenamiento correspondiente,
    sin mezclar ni recortar el conjunto de entrenamiento original).
    `gap` (por defecto 0, sin cambio de comportamiento previo) excluye
    las últimas `gap` filas de cada fold de entrenamiento interno:
    necesario cuando el target de una fila depende de una fila
    `horizon_days` adelante (`predictive_modeling.labeling
    .add_stress_label`), para que ningún target de entrenamiento se
    solape temporalmente con su propio fold de validación — pasar
    `gap=horizon_days` en ese caso. Devuelve el mejor estimador ya
    entrenado, sus mejores parámetros, y la media/desvío de `scoring`
    entre los folds de validación cruzada (indicador de estabilidad).
    """
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    scorer = _binary_f1 if scoring == "f1" else scoring
    search = GridSearchCV(clone(model), param_grid=param_grid, cv=splitter, scoring=scorer)
    search.fit(X_train, y_train)

    best_index = search.best_index_
    cv_results = search.cv_results_

    return {
        "best_estimator": search.best_estimator_,
        "best_params": search.best_params_,
        "cv_mean_score": float(cv_results["mean_test_score"][best_index]),
        "cv_std_score": float(cv_results["std_test_score"][best_index]),
    }


def diagnose_time_series_folds(
    y: pd.Series, n_splits: int = 5, gap: int = 0
) -> list[dict[str, int]]:
    """Diagnostica cada fold de `TimeSeriesSplit(n_splits, gap)` sobre
    `y`: cantidad de positivos y negativos en el fold de entrenamiento y
    en el de validación. Un fold de validación sin ningún positivo hace
    que una métrica como F1 (con `zero_division=0`) sea 0 por
    construcción, no porque el modelo evaluado sea malo — sin este
    diagnóstico, ese 0 es indistinguible de una evaluación genuina.
    """
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    y_array = y.to_numpy()

    diagnostics = []
    for fold_index, (train_idx, val_idx) in enumerate(splitter.split(y_array)):
        train_positives = int(y_array[train_idx].sum())
        val_positives = int(y_array[val_idx].sum())
        diagnostics.append(
            {
                "fold": fold_index,
                "train_positives": train_positives,
                "train_negatives": len(train_idx) - train_positives,
                "val_positives": val_positives,
                "val_negatives": len(val_idx) - val_positives,
            }
        )
    return diagnostics
