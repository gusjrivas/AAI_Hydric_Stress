import pandas as pd

from predictive_modeling.models import build_candidate_models, predict_persistence_baseline


def test_predict_persistence_baseline_flags_current_value_below_threshold():
    df = pd.DataFrame({"soil_moisture": [0.20, 0.40, 0.10, 0.35]})

    predictions = predict_persistence_baseline(df, column="soil_moisture", threshold=0.30)

    assert list(predictions) == [1, 0, 1, 0]


def test_build_candidate_models_returns_logistic_regression_and_random_forest():
    models = build_candidate_models(random_state=42)

    assert set(models.keys()) == {"logistic_regression", "random_forest"}
    assert hasattr(models["logistic_regression"], "fit")
    assert hasattr(models["random_forest"], "fit")
