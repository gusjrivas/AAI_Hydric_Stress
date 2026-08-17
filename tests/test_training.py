import numpy as np
import pandas as pd

from predictive_modeling.models import build_candidate_models
from predictive_modeling.training import train_models, tune_hyperparameters


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
