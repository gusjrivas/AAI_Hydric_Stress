"""Comparación de desempeño, estabilidad y complejidad de modelos
(spec predictive-modeling, requirement "Comparación de desempeño,
estabilidad y complejidad").
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score


def evaluate_classifier(
    y_true: pd.Series, y_pred: pd.Series, y_proba: pd.Series | None = None
) -> dict[str, float]:
    """Calcula precisión, recall y F1 sobre la clase de estrés (1), y
    ROC-AUC si se provee `y_proba` (probabilidad de la clase de estrés).
    """
    metrics = {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    if y_proba is not None:
        metrics["roc_auc"] = roc_auc_score(y_true, y_proba)
    return metrics


def compare_models(y_true: pd.Series, model_predictions: dict[str, dict]) -> pd.DataFrame:
    """Compara el modelo de referencia y los modelos candidatos: para
    cada uno, reporta desempeño (precisión/recall/F1/ROC-AUC),
    estabilidad (`cv_std_score`, NaN si no aplica, como en el modelo de
    referencia sin validación cruzada) y complejidad (`complexity`, NaN
    si no se provee).
    """
    rows = {}
    for name, predictions in model_predictions.items():
        metrics = evaluate_classifier(y_true, predictions["y_pred"], predictions.get("y_proba"))
        rows[name] = {
            **metrics,
            "cv_std_score": predictions.get("cv_std_score", np.nan),
            "complexity": predictions.get("complexity", np.nan),
        }
    return pd.DataFrame.from_dict(rows, orient="index")
