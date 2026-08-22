import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier

from predictive_modeling.model_selection import select_best_candidate


def _separable_dataset(n=120, seed=0):
    rng = np.random.default_rng(seed)
    feature = rng.normal(0, 1, size=n)
    target = (feature > 0).astype(int)
    X = pd.DataFrame({"feature": feature})
    y = pd.Series(target, name="stress_label")
    return X, y


def test_select_best_candidate_uses_default_candidates_and_grids():
    X, y = _separable_dataset()

    result = select_best_candidate(X, y, n_splits=4)

    assert result["model_name"] in {"logistic_regression", "random_forest"}
    assert hasattr(result["model"], "predict_proba")
    assert "cv_mean_score" in result
    assert "cv_std_score" in result


def test_select_best_candidate_picks_the_higher_cv_mean_score():
    X, y = _separable_dataset(n=150, seed=1)

    candidates = {
        "bad": DummyClassifier(strategy="constant", constant=0),
        "good": RandomForestClassifier(random_state=0),
    }
    param_grids = {"bad": {}, "good": {"n_estimators": [50]}}

    result = select_best_candidate(
        X, y, candidates=candidates, param_grids=param_grids, n_splits=4
    )

    assert result["model_name"] == "good"


def test_select_best_candidate_breaks_ties_in_favor_of_random_forest():
    X, y = _separable_dataset(n=150, seed=2)

    candidates = {
        "logistic_regression": DummyClassifier(strategy="constant", constant=0),
        "random_forest": DummyClassifier(strategy="constant", constant=0),
    }
    param_grids = {"logistic_regression": {}, "random_forest": {}}

    result = select_best_candidate(
        X, y, candidates=candidates, param_grids=param_grids, n_splits=4
    )

    assert result["model_name"] == "random_forest"
