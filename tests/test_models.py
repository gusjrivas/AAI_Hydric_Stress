import pandas as pd

from predictive_modeling.models import (
    build_candidate_models,
    predict_always_stress_baseline,
    predict_majority_class_baseline,
    predict_persistence_baseline,
)


def test_predict_persistence_baseline_flags_current_value_below_threshold():
    df = pd.DataFrame({"soil_moisture": [0.20, 0.40, 0.10, 0.35]})

    predictions = predict_persistence_baseline(df, column="soil_moisture", threshold=0.30)

    assert list(predictions) == [1, 0, 1, 0]


def test_predict_majority_class_baseline_predicts_the_majority_class_of_y_train():
    y_train = pd.Series([0, 0, 0, 1])  # mayoría: 0

    predictions = predict_majority_class_baseline(y_train, n_predictions=5)

    assert list(predictions) == [0, 0, 0, 0, 0]


def test_predict_majority_class_baseline_with_majority_positive():
    y_train = pd.Series([1, 1, 1, 0])  # mayoría: 1

    predictions = predict_majority_class_baseline(y_train, n_predictions=3)

    assert list(predictions) == [1, 1, 1]


def test_predict_always_stress_baseline_predicts_one_for_every_row():
    predictions = predict_always_stress_baseline(n_predictions=4)

    assert list(predictions) == [1, 1, 1, 1]


def test_build_candidate_models_returns_logistic_regression_and_random_forest():
    models = build_candidate_models(random_state=42)

    assert set(models.keys()) == {"logistic_regression", "random_forest"}
    assert hasattr(models["logistic_regression"], "fit")
    assert hasattr(models["random_forest"], "fit")
