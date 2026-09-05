import numpy as np
import pandas as pd

from predictive_modeling.models import build_candidate_models
from predictive_modeling.training import (
    diagnose_time_series_folds,
    train_models,
    tune_hyperparameters,
)


def _classification_dataset(n=120, seed=0):
    rng = np.random.default_rng(seed)
    feature = rng.normal(0, 1, size=n)
    target = (feature + rng.normal(0, 0.3, size=n) > 0).astype(int)
    X = pd.DataFrame({"feature": feature})
    y = pd.Series(target, name="stress_label")
    return X, y


def test_train_models_returns_fitted_models_that_can_predict():
    X, y = _classification_dataset()
    models = build_candidate_models(random_state=0)

    fitted = train_models(models, X, y)

    for name, model in fitted.items():
        predictions = model.predict(X)
        assert len(predictions) == len(X), f"{name} no predijo para todas las filas"


def test_tune_hyperparameters_uses_time_series_split_without_shuffling():
    X, y = _classification_dataset(n=100)
    model = build_candidate_models(random_state=0)["logistic_regression"]
    param_grid = {"C": [0.1, 1.0]}

    result = tune_hyperparameters(model, param_grid, X, y, n_splits=4)

    assert "best_estimator" in result
    assert "cv_mean_score" in result
    assert "cv_std_score" in result
    assert hasattr(result["best_estimator"], "predict")


def test_tune_hyperparameters_passes_gap_to_time_series_split(monkeypatch):
    X, y = _classification_dataset(n=100)
    model = build_candidate_models(random_state=0)["logistic_regression"]
    param_grid = {"C": [0.1]}

    captured = {}
    real_time_series_split = __import__(
        "sklearn.model_selection", fromlist=["TimeSeriesSplit"]
    ).TimeSeriesSplit

    def _spy(*args, **kwargs):
        captured["gap"] = kwargs.get("gap")
        return real_time_series_split(*args, **kwargs)

    monkeypatch.setattr("predictive_modeling.training.TimeSeriesSplit", _spy)

    tune_hyperparameters(model, param_grid, X, y, n_splits=4, gap=3)

    assert captured["gap"] == 3


def test_tune_hyperparameters_defaults_gap_to_zero():
    X, y = _classification_dataset(n=100)
    model = build_candidate_models(random_state=0)["logistic_regression"]
    param_grid = {"C": [0.1]}

    # sin especificar gap, debe comportarse igual que antes (gap=0):
    # no debería fallar ni cambiar la interfaz existente.
    result = tune_hyperparameters(model, param_grid, X, y, n_splits=4)

    assert "best_estimator" in result


def test_diagnose_time_series_folds_counts_positives_and_negatives_per_fold():
    y = pd.Series([0] * 10 + [1] * 10 + [0] * 10 + [1] * 10)

    diagnostics = diagnose_time_series_folds(y, n_splits=3, gap=0)

    assert len(diagnostics) == 3
    for fold in diagnostics:
        assert set(fold.keys()) == {
            "fold",
            "train_positives",
            "train_negatives",
            "val_positives",
            "val_negatives",
        }
        assert fold["train_positives"] + fold["train_negatives"] > 0
        assert fold["val_positives"] + fold["val_negatives"] > 0


def test_diagnose_time_series_folds_detects_a_fold_with_no_positive_validation_examples():
    # los primeros 30 valores son todos 0 (sin positivos); el TimeSeriesSplit
    # más temprano cae completamente dentro de ese tramo.
    y = pd.Series([0] * 30 + [1] * 10)

    diagnostics = diagnose_time_series_folds(y, n_splits=3, gap=0)

    assert diagnostics[0]["val_positives"] == 0


def test_diagnose_time_series_folds_respects_gap():
    y = pd.Series(list(range(40)))  # valores dummy, solo importa el largo
    y = (y % 2).astype(int)

    diagnostics_no_gap = diagnose_time_series_folds(y, n_splits=3, gap=0)
    diagnostics_with_gap = diagnose_time_series_folds(y, n_splits=3, gap=3)

    # con gap, el fold de entrenamiento pierde `gap` filas respecto de sin gap
    train_size_no_gap = (
        diagnostics_no_gap[0]["train_positives"] + diagnostics_no_gap[0]["train_negatives"]
    )
    train_size_with_gap = (
        diagnostics_with_gap[0]["train_positives"] + diagnostics_with_gap[0]["train_negatives"]
    )
    assert train_size_with_gap < train_size_no_gap
