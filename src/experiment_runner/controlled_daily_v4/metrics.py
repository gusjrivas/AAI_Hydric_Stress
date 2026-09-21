"""Métricas y convenciones ante casos degenerados (protocolo, sección 12).

Ningún `NaN` se reemplaza silenciosamente por 0 ni por un resultado
favorable. `MCC global` se recalcula siempre sobre la concatenación OOF
completa, nunca como promedio de los MCC por fold.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

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

from experiment_runner.controlled_daily_v4.config import HORIZON_DAYS

LABELS = [0, 1]


def is_monoclass(y_true) -> bool:
    return len(np.unique(np.asarray(y_true))) < 2


def mcc_strict(y_true, y_pred) -> float:
    """`NaN` explícito si `y_true` es monoclase, o si scikit-learn emite el
    warning de denominador indefinido (nunca el `0.0` silencioso por defecto)."""
    y_true = np.asarray(y_true)
    if is_monoclass(y_true) or is_monoclass(y_pred):
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
    if is_monoclass(y_true):
        return float("nan")
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


# --------------------------------------------------------------------------
# Serialización de métricas con estado explícito (protocolo, sección 12)
# --------------------------------------------------------------------------

METRIC_STATUS_DEFINED = "defined"
METRIC_STATUS_UNDEFINED = "undefined"

REASON_MONOCLASS = "monoclass_y_true"
REASON_NO_POSITIVES = "no_positive_labels_in_y_true"
REASON_NO_PREDICTED_OR_TRUE_POSITIVES = "no_predicted_and_no_true_positives"
REASON_NO_EPISODES = "no_stress_episodes_in_y_true"
REASON_EMPTY = "empty_evaluation_set"
REASON_EMPTY_BIN = "no_observations_in_bin"
REASON_UNSPECIFIED = "unspecified"

PERCENTILE_METHOD = "linear"
"""Método de interpolación de percentiles usado para Q1/Q3, fijado
explícitamente para que la mediana y el IQR sean deterministas y
reproducibles entre versiones de NumPy."""

CALIBRATION_N_BINS = 10


def metric_envelope(value, undefined_reason: str = REASON_UNSPECIFIED) -> dict[str, Any]:
    """Envoltura serializable de una métrica.

    Una métrica definida se representa como `{"value": x, "status": "defined"}`;
    una indefinida como `{"value": null, "status": "undefined",
    "undefined_reason": ...}`. Ningún valor indefinido se convierte en 0."""
    if value is None or not np.isfinite(float(value)):
        return {
            "value": None,
            "status": METRIC_STATUS_UNDEFINED,
            "undefined_reason": undefined_reason,
        }
    return {"value": float(value), "status": METRIC_STATUS_DEFINED}


def calibration_curve_10_bins(y_true, y_score) -> list[dict[str, Any]]:
    """Reliability diagram de 10 bins equiespaciados en `[0, 1]`.

    Los bins sin observaciones reportan frecuencia observada y probabilidad
    media predicha indefinidas, nunca 0."""
    y_true = np.asarray(y_true, dtype=float)
    y_score = np.asarray(y_score, dtype=float)
    edges = np.linspace(0.0, 1.0, CALIBRATION_N_BINS + 1)
    bins: list[dict[str, Any]] = []
    for i in range(CALIBRATION_N_BINS):
        low, high = edges[i], edges[i + 1]
        # El último bin incluye el borde superior para no perder score == 1.0.
        in_bin = (y_score >= low) & (
            (y_score < high) if i < CALIBRATION_N_BINS - 1 else (y_score <= high)
        )
        count = int(in_bin.sum())
        bins.append(
            {
                "bin_index": i,
                "bin_lower": float(low),
                "bin_upper": float(high),
                "count": count,
                "mean_predicted_probability": metric_envelope(
                    float(y_score[in_bin].mean()) if count else float("nan"), REASON_EMPTY_BIN
                ),
                "observed_frequency": metric_envelope(
                    float(y_true[in_bin].mean()) if count else float("nan"), REASON_EMPTY_BIN
                ),
            }
        )
    return bins


def metrics_payload(
    y_true, y_pred, y_score, *, feature_timestamps=None, segment_ids=None
) -> dict[str, Any]:
    """Todas las métricas del protocolo sobre un conjunto evaluado, con estado
    explícito por métrica y la razón de cada indefinición."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    y_score = np.asarray(y_score)

    empty = len(y_true) == 0
    monoclass_reason = REASON_EMPTY if empty else REASON_MONOCLASS
    zero_division_reason = REASON_EMPTY if empty else REASON_NO_PREDICTED_OR_TRUE_POSITIVES
    bundle = compute_metrics(y_true, y_pred, y_score) if not empty else None
    operational = compute_operational_metrics(y_true, y_pred) if not empty else None

    def value(attribute):
        return getattr(bundle, attribute) if bundle is not None else float("nan")

    def operational_value(attribute):
        return getattr(operational, attribute) if operational is not None else float("nan")

    return {
        "n_observations": int(len(y_true)),
        "n_positive_labels": int((y_true == 1).sum()),
        "n_predicted_positive": int((y_pred == 1).sum()),
        "mcc": metric_envelope(
            value("mcc"),
            monoclass_reason if empty or is_monoclass(y_true) else "constant_prediction",
        ),
        "average_precision": metric_envelope(
            value("average_precision"), REASON_EMPTY if empty else REASON_NO_POSITIVES
        ),
        "balanced_accuracy": metric_envelope(value("balanced_accuracy"), monoclass_reason),
        "f1": metric_envelope(value("f1"), zero_division_reason),
        "precision": metric_envelope(
            value("precision"), REASON_EMPTY if empty else "no_predicted_positives"
        ),
        "recall": metric_envelope(value("recall"), REASON_EMPTY if empty else REASON_NO_POSITIVES),
        "roc_auc": metric_envelope(value("roc_auc"), monoclass_reason),
        "brier_score": metric_envelope(value("brier_score"), REASON_EMPTY),
        "log_loss": metric_envelope(value("log_loss"), REASON_EMPTY),
        "confusion_matrix": (
            confusion_matrix_2x2(y_true, y_pred).tolist() if not empty else [[0, 0], [0, 0]]
        ),
        "confusion_matrix_labels": list(LABELS),
        "operational": {
            "alert_rate": metric_envelope(operational_value("alert_rate"), REASON_EMPTY),
            "false_positives_per_30_days": metric_envelope(
                operational_value("false_positives_per_30_days"), REASON_EMPTY
            ),
            "false_negatives_per_30_days": metric_envelope(
                operational_value("false_negatives_per_30_days"), REASON_EMPTY
            ),
            "episode_recall": metric_envelope(
                operational_value("episode_recall"),
                REASON_EMPTY if empty else REASON_NO_EPISODES,
            ),
            "alert_precision": metric_envelope(
                operational_value("alert_precision"), zero_division_reason
            ),
        },
        "onset": onset_metrics(y_true, y_pred, feature_timestamps, segment_ids),
        "calibration": calibration_curve_10_bins(y_true, y_score),
    }


def summarize_fold_mcc(fold_mcc: list[float]) -> dict[str, Any]:
    """Diagnóstico por outer fold (protocolo, sección 8.4): mediana, cuartiles
    e IQR de los MCC por fold, con recuento explícito de folds indefinidos.

    Nunca reemplaza el MCC global: este bloque es descriptivo y no decide."""
    values = [float(v) for v in fold_mcc]
    defined = [v for v in values if np.isfinite(v)]
    n_undefined = len(values) - len(defined)

    if defined:
        median = float(np.percentile(defined, 50, method=PERCENTILE_METHOD))
        q1 = float(np.percentile(defined, 25, method=PERCENTILE_METHOD))
        q3 = float(np.percentile(defined, 75, method=PERCENTILE_METHOD))
        iqr = q3 - q1
    else:
        median = q1 = q3 = iqr = float("nan")

    reason = REASON_EMPTY if not values else REASON_MONOCLASS
    return {
        "per_fold": [metric_envelope(v, REASON_MONOCLASS) for v in values],
        "median": metric_envelope(median, reason),
        "q1": metric_envelope(q1, reason),
        "q3": metric_envelope(q3, reason),
        "iqr": metric_envelope(iqr, reason),
        "n_folds": len(values),
        "n_folds_defined": len(defined),
        "n_folds_undefined": n_undefined,
        "percentile_method": PERCENTILE_METHOD,
    }


REASON_NO_OWN_GRID = "soft_voting_has_no_own_grid"
"""El Soft Voting no tiene grilla propia (protocolo, sección 7.5): su mediana
de MCC inner es indefinida por construcción, no por un fold degenerado."""


def onset_metrics(y_true, y_pred, feature_timestamps, segment_ids=None):
    """Descriptive onset metrics; censored starts never enter the denominator."""
    import pandas as pd

    y, alerts = np.asarray(y_true), np.asarray(y_pred)
    if feature_timestamps is None:
        return {"status": "undefined", "undefined_reason": "missing_timestamps"}
    dates = pd.DatetimeIndex(feature_timestamps)
    segments = np.zeros(len(y), dtype=int) if segment_ids is None else np.asarray(segment_ids)
    if not (len(y) == len(alerts) == len(dates) == len(segments)):
        raise ValueError("Onset arrays must have identical lengths")
    if dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("Onset timestamps must be unique and ordered")
    if not dates.equals(dates.normalize()):
        raise ValueError("Onset timestamps must be daily midnight")
    if not np.isin(y, [0, 1]).all() or not np.isin(alerts, [0, 1]).all():
        raise ValueError("Onset labels must be binary")
    targets = dates + pd.Timedelta(days=HORIZON_DAYS)
    breaks = np.ones(len(y), dtype=bool)
    if len(y) > 1:
        breaks[1:] = (np.diff(dates.values) != np.timedelta64(1, "D")) | (
            segments[1:] != segments[:-1]
        )
    counts = dict(total=0, evaluable=0, censored=0, anticipated=0, same_day=0, late=0, missed=0)
    records, leads = [], []
    i = 0
    while i < len(y):
        if y[i] != 1:
            i += 1
            continue
        start = i
        i += 1
        while i < len(y) and y[i] == 1 and not breaks[i]:
            i += 1
        counts["total"] += 1
        if breaks[start]:
            counts["censored"] += 1
            continue
        counts["evaluable"] += 1
        hits = np.flatnonzero(alerts[start:i]) + start
        lead = None
        outcome = "missed"
        if len(hits):
            lead = int((targets[start] - dates[hits[0]]).days)
            leads.append(lead)
            outcome = "anticipated" if lead > 0 else "same_day" if lead == 0 else "late"
        counts[outcome] += 1
        records.append({"onset": str(targets[start]), "outcome": outcome, "lead_days": lead})
    false = (alerts == 1) & (y == 0)
    false_runs = sum(bool(false[j]) and (breaks[j] or not false[j - 1]) for j in range(len(y)))
    return {
        "definition_version": "episode_onset.v1",
        "n_days": len(y),
        "n_positive_days": int(y.sum()),
        "episodes": counts,
        "records": records,
        "false_notice_days": int(false.sum()),
        "false_notice_runs": int(false_runs),
        "anticipation_rate": metric_envelope(
            counts["anticipated"] / counts["evaluable"] if counts["evaluable"] else None,
            "no_evaluable_episode_onsets",
        ),
        "median_signed_lead_days": metric_envelope(
            np.median(leads) if leads else None, "no_detected_evaluable_episodes"
        ),
    }
