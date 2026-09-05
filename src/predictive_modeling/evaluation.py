"""Comparación de desempeño, estabilidad y complejidad de modelos
(spec predictive-modeling, requirement "Comparación de desempeño,
estabilidad y complejidad, con métricas robustas al desbalance de
clases").
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_classifier(
    y_true: pd.Series, y_pred: pd.Series, y_proba: pd.Series | None = None
) -> dict[str, float]:
    """Calcula precisión, recall y F1 sobre la clase de estrés (1),
    balanced accuracy y el coeficiente de correlación de Matthews (MCC,
    en [-1, 1]) siempre, y ROC-AUC + average precision (PR-AUC) si se
    provee `y_proba` (probabilidad de la clase de estrés). MCC en
    particular penaliza a un clasificador trivial (ej. "siempre estrés")
    que puede lograr F1/recall altos únicamente por la prevalencia de la
    clase positiva en el conjunto evaluado, sin capacidad predictiva real
    — auditoría metodológica de la memoria técnica, ver
    `docs/research/hu8-analisis-resultados.md`, sección 11.
    """
    if len(y_true) == 0:
        names = ["precision", "recall", "f1", "balanced_accuracy", "mcc"]
        if y_proba is not None:
            names += ["roc_auc", "average_precision"]
        return dict.fromkeys(names, float("nan"))
    metrics = {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "mcc": matthews_corrcoef(y_true, y_pred),
    }
    if y_proba is not None:
        metrics["roc_auc"] = (
            roc_auc_score(y_true, y_proba) if y_true.nunique() == 2 else float("nan")
        )
        metrics["average_precision"] = (
            average_precision_score(y_true, y_proba) if (y_true == 1).any() else float("nan")
        )
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
