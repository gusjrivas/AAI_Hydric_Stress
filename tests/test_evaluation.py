import numpy as np
import pandas as pd

from predictive_modeling.evaluation import compare_models, evaluate_classifier


def test_evaluate_classifier_reports_stress_class_metrics():
    y_true = pd.Series([1, 0, 1, 0, 1, 0])
    y_pred = pd.Series([1, 0, 0, 0, 1, 1])
    y_proba = pd.Series([0.9, 0.2, 0.4, 0.1, 0.8, 0.6])

    metrics = evaluate_classifier(y_true, y_pred, y_proba)

    assert set(["precision", "recall", "f1", "roc_auc"]).issubset(metrics.keys())
    for key in ("precision", "recall", "f1", "roc_auc"):
        assert 0.0 <= metrics[key] <= 1.0


def test_evaluate_classifier_reports_balanced_accuracy_mcc_and_average_precision():
    y_true = pd.Series([1, 0, 1, 0, 1, 0])
    y_pred = pd.Series([1, 0, 0, 0, 1, 1])
    y_proba = pd.Series([0.9, 0.2, 0.4, 0.1, 0.8, 0.6])

    metrics = evaluate_classifier(y_true, y_pred, y_proba)

    assert set(["balanced_accuracy", "mcc", "average_precision"]).issubset(metrics.keys())
    assert 0.0 <= metrics["balanced_accuracy"] <= 1.0
    assert -1.0 <= metrics["mcc"] <= 1.0
    assert 0.0 <= metrics["average_precision"] <= 1.0


def test_evaluate_classifier_mcc_and_balanced_accuracy_available_without_y_proba():
    y_true = pd.Series([1, 0, 1, 0])
    y_pred = pd.Series([1, 0, 1, 1])

    metrics = evaluate_classifier(y_true, y_pred)

    assert "mcc" in metrics
    assert "balanced_accuracy" in metrics
    assert "average_precision" not in metrics  # requiere y_proba
    assert "roc_auc" not in metrics


def test_evaluate_classifier_flags_a_trivial_always_positive_prediction_with_low_mcc():
    # con clase positiva minoritaria, "siempre estrés" puede dar F1/recall
    # altos por prevalencia, pero MCC (que penaliza no distinguir clases)
    # debe quedar bajo -- ese es justamente el objetivo de agregar MCC.
    y_true = pd.Series([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    y_pred = pd.Series([1] * 10)  # siempre predice estrés

    metrics = evaluate_classifier(y_true, y_pred)

    assert metrics["mcc"] == 0.0
    assert metrics["f1"] > 0.0  # el F1 por sí solo no revela el problema


def test_compare_models_returns_table_with_performance_stability_and_complexity():
    y_true = pd.Series([1, 0, 1, 0, 1, 0])

    model_predictions = {
        "persistence": {"y_pred": pd.Series([1, 0, 1, 0, 0, 0])},
        "logistic_regression": {
            "y_pred": pd.Series([1, 0, 1, 1, 1, 0]),
            "y_proba": pd.Series([0.8, 0.3, 0.7, 0.6, 0.9, 0.2]),
            "cv_std_score": 0.05,
            "complexity": 1,
        },
        "random_forest": {
            "y_pred": pd.Series([1, 0, 0, 0, 1, 0]),
            "y_proba": pd.Series([0.7, 0.1, 0.4, 0.2, 0.85, 0.3]),
            "cv_std_score": 0.02,
            "complexity": 100,
        },
    }

    table = compare_models(y_true, model_predictions)

    assert isinstance(table, pd.DataFrame)
    assert set(table.index) == {"persistence", "logistic_regression", "random_forest"}
    for column in ("precision", "recall", "f1", "cv_std_score", "complexity"):
        assert column in table.columns
    assert np.isnan(table.loc["persistence", "cv_std_score"])
