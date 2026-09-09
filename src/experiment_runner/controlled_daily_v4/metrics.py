"""Métricas y convenciones ante casos degenerados (protocolo, sección 12).

Ningún `NaN` se reemplaza silenciosamente por 0 ni por un resultado
favorable. `MCC global` se recalcula siempre sobre la concatenación OOF
completa, nunca como promedio de los MCC por fold.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

LABELS = [0, 1]


def is_monoclass(y_true) -> bool:
    return len(np.unique(np.asarray(y_true))) < 2


def mcc_strict(y_true, y_pred) -> float:
    """`NaN` explícito si `y_true` es monoclase, o si scikit-learn emite el
    warning de denominador indefinido (nunca el `0.0` silencioso por defecto)."""
    y_true = np.asarray(y_true)
    if is_monoclass(y_true):
        return float("nan")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = matthews_corrcoef(y_true, y_pred)
        if any("invalid value" in str(w.message) for w in caught):
            return float("nan")
    return float(value)


def average_precision_strict(y_true, y_score) -> float:
    y_true = np.asarray(y_true)
    if y_true.sum() == 0:
        return float("nan")
    return float(average_precision_score(y_true, y_score))


def roc_auc_strict(y_true, y_score) -> float:
    if is_monoclass(y_true):
        return float("nan")
    return float(roc_auc_score(y_true, y_score))


def brier_score(y_true, y_score) -> float:
    return float(brier_score_loss(y_true, y_score))


def log_loss_strict(y_true, y_score) -> float:
    return float(log_loss(y_true, y_score, labels=LABELS))


def confusion_matrix_2x2(y_true, y_pred) -> np.ndarray:
    return confusion_matrix(y_true, y_pred, labels=LABELS)


def balanced_accuracy(y_true, y_pred) -> float:
    return float(balanced_accuracy_score(y_true, y_pred))


def f1_strict(y_true, y_pred) -> float:
    return float(f1_score(y_true, y_pred, zero_division=np.nan))


def precision_strict(y_true, y_pred) -> float:
    return float(precision_score(y_true, y_pred, zero_division=np.nan))


def recall_strict(y_true, y_pred) -> float:
    return float(recall_score(y_true, y_pred, zero_division=np.nan))


@dataclass
class MetricsBundle:
    mcc: float
    average_precision: float
    balanced_accuracy: float
    f1: float
    precision: float
    recall: float
    roc_auc: float
    brier_score: float
    log_loss: float
    confusion_matrix: np.ndarray = field(repr=False)


def compute_metrics(y_true, y_pred, y_score) -> MetricsBundle:
    return MetricsBundle(
        mcc=mcc_strict(y_true, y_pred),
        average_precision=average_precision_strict(y_true, y_score),
        balanced_accuracy=balanced_accuracy(y_true, y_pred),
        f1=f1_strict(y_true, y_pred),
        precision=precision_strict(y_true, y_pred),
        recall=recall_strict(y_true, y_pred),
        roc_auc=roc_auc_strict(y_true, y_score),
        brier_score=brier_score(y_true, y_score),
        log_loss=log_loss_strict(y_true, y_score),
        confusion_matrix=confusion_matrix_2x2(y_true, y_pred),
    )


def _stress_episodes(y_true: np.ndarray) -> list[tuple[int, int]]:
    """Rachas contiguas de `y_true == 1` como pares (inicio, fin) inclusive,
    en índices posicionales ordenados temporalmente."""
    episodes = []
    start = None
    for i, value in enumerate(y_true):
        if value == 1 and start is None:
            start = i
        elif value == 0 and start is not None:
            episodes.append((start, i - 1))
            start = None
    if start is not None:
        episodes.append((start, len(y_true) - 1))
    return episodes


def episode_recall(y_true, y_pred) -> float:
    """Recall por episodio (racha contigua de estrés real), no por día
    suelto: un episodio cuenta como detectado si al menos un día dentro de
    la racha recibió alerta."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    episodes = _stress_episodes(y_true)
    if not episodes:
        return float("nan")
    detected = sum(1 for start, end in episodes if y_pred[start : end + 1].sum() > 0)
    return detected / len(episodes)


@dataclass
class OperationalMetrics:
    alert_rate: float
    false_positives_per_30_days: float
    false_negatives_per_30_days: float
    episode_recall: float
    alert_precision: float


def compute_operational_metrics(y_true, y_pred) -> OperationalMetrics:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    n = len(y_true)
    false_positives = int(((y_pred == 1) & (y_true == 0)).sum())
    false_negatives = int(((y_pred == 0) & (y_true == 1)).sum())
    scale = 30.0 / n if n else float("nan")
    return OperationalMetrics(
        alert_rate=float(y_pred.mean()) if n else float("nan"),
        false_positives_per_30_days=false_positives * scale,
        false_negatives_per_30_days=false_negatives * scale,
        episode_recall=episode_recall(y_true, y_pred),
        alert_precision=precision_strict(y_true, y_pred),
    )
