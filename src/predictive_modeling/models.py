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


def build_candidate_models(random_state: int = 42) -> dict[str, object]:
    """Devuelve los modelos candidatos sin entrenar: regresión logística
    y Random Forest (ambos scikit-learn, ADR-0002).
    """
    return {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=random_state),
        "random_forest": RandomForestClassifier(random_state=random_state),
    }
