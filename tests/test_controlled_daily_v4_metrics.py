from __future__ import annotations

import math

import numpy as np

from experiment_runner.controlled_daily_v4.metrics import (
    average_precision_strict,
    compute_metrics,
    confusion_matrix_2x2,
    log_loss_strict,
    mcc_strict,
    roc_auc_strict,
)


def test_mcc_is_nan_when_y_true_is_monoclass():
    y_true = np.array([0, 0, 0, 0])
    y_pred = np.array([0, 1, 0, 1])
    assert math.isnan(mcc_strict(y_true, y_pred))


def test_mcc_is_defined_when_both_classes_present():
    y_true = np.array([0, 1, 0, 1, 0, 1])
    y_pred = np.array([0, 1, 0, 1, 1, 0])
    value = mcc_strict(y_true, y_pred)
    assert not math.isnan(value)
    assert -1.0 <= value <= 1.0


def test_average_precision_is_nan_without_positives():
    y_true = np.array([0, 0, 0])
    y_score = np.array([0.1, 0.4, 0.9])
    assert math.isnan(average_precision_strict(y_true, y_score))


def test_roc_auc_is_nan_when_monoclass():
    y_true = np.array([1, 1, 1])
    y_score = np.array([0.2, 0.6, 0.9])
    assert math.isnan(roc_auc_strict(y_true, y_score))


def test_log_loss_uses_fixed_labels_even_if_monoclass():
    y_true = np.array([0, 0, 0])
    y_score = np.array([0.1, 0.2, 0.05])
    value = log_loss_strict(y_true, y_score)
    assert not math.isnan(value)


def test_confusion_matrix_is_always_2x2():
    y_true = np.array([0, 0, 0])
    y_pred = np.array([0, 0, 0])
    cm = confusion_matrix_2x2(y_true, y_pred)
    assert cm.shape == (2, 2)


def test_compute_metrics_never_replaces_nan_with_zero():
    y_true = np.array([1, 1, 1, 1])
    y_pred = np.array([1, 0, 1, 1])
    y_score = np.array([0.9, 0.2, 0.8, 0.7])
    bundle = compute_metrics(y_true, y_pred, y_score)
    assert math.isnan(bundle.mcc)
    assert math.isnan(bundle.roc_auc)
    assert not math.isnan(bundle.brier_score)
    assert not math.isnan(bundle.log_loss)
