"""Modelo de referencia y modelos candidatos (spec predictive-modeling,
requirements "Modelo de referencia por persistencia" y "Entrenamiento
de modelos candidatos").
"""

from __future__ import annotations

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

DEFAULT_HYPERPARAMETER_GRIDS: dict[str, dict[str, list]] = {
    "logistic_regression": {"C": [0.01, 0.1, 1.0, 10.0]},
    "random_forest": {"n_estimators": [50, 100, 200], "max_depth": [3, 5, None]},
}


def predict_persistence_baseline(df: pd.DataFrame, column: str, threshold: float) -> pd.Series:
    """Modelo de referencia: predice estrés (1) si el valor actual de
    `column` está por debajo de `threshold`, sin requerir entrenamiento.
    """
    return (df[column] < threshold).astype(int)


def predict_majority_class_baseline(y_train: pd.Series, n_predictions: int) -> pd.Series:
    """Baseline de clase mayoritaria: predice, para `n_predictions` filas,
    siempre la clase (0/1) más frecuente observada en `y_train`. Sirve
    para distinguir si una métrica alta se explica por la prevalencia de
    una clase en la evaluación y no por capacidad predictiva del modelo.
    """
    majority_class = int(y_train.mode().iloc[0])
    return pd.Series([majority_class] * n_predictions)


def predict_always_stress_baseline(n_predictions: int) -> pd.Series:
    """Baseline trivial: predice siempre estrés (1) para `n_predictions`
    filas, sin usar ningún dato. Mismo propósito que
    `predict_majority_class_baseline`: un piso de comparación para
    detectar cuándo el desempeño aparente de un modelo es en realidad un
    artefacto del desbalance de clases en evaluación.
    """
    return pd.Series([1] * n_predictions)


def build_candidate_models(random_state: int = 42) -> dict[str, object]:
    """Devuelve los modelos candidatos sin entrenar: regresión logística
    y Random Forest (ambos scikit-learn, ADR-0002).
    """
    return {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=random_state),
        "random_forest": RandomForestClassifier(random_state=random_state),
    }
