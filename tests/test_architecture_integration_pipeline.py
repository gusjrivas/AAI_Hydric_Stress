import numpy as np
import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from predictive_modeling.models import build_candidate_models


def _synthetic_dataset(n=60, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime(pd.date_range("2024-01-01", periods=n, freq="D"))
    soil_moisture = rng.normal(0.35, 0.03, size=n)
    solar_radiation = rng.normal(20, 3, size=n)
    return pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": soil_moisture,
            "solar_radiation": solar_radiation,
        }
    )


def test_run_end_to_end_pipeline_produces_all_expected_artifacts():
    df = _synthetic_dataset()
    model = build_candidate_models(random_state=0)["logistic_regression"]

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[45].date(),
        model=model,
        include_anomaly_detection=True,
    )

    assert "quality_report" in result
    assert "train" in result and "test" in result
    assert "model" in result and hasattr(result["model"], "predict")
    assert "alerts" in result and len(result["alerts"]) == len(result["test"])
    assert "feedback_log" in result
    assert set(result["feedback_log"]["estado_validacion"]) == {"pendiente"}
    assert "is_anomaly" in result["train"].columns


def test_run_end_to_end_pipeline_computes_features_for_first_test_rows_without_nan():
    df = _synthetic_dataset()
    model = build_candidate_models(random_state=0)["logistic_regression"]

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[45].date(),
        model=model,
        include_anomaly_detection=False,
    )

    feature_cols = result["feature_columns"]
    assert not result["test"][feature_cols].isna().any().any()


def test_run_end_to_end_pipeline_with_skip_fit_true_does_not_refit_the_model():
    df = _synthetic_dataset()

    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("fit no debería llamarse cuando skip_fit=True")

        def predict_proba(self, X):
            return np.tile([0.3, 0.7], (len(X), 1))

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[45].date(),
        model=_FitRaisesModel(),
        include_anomaly_detection=False,
        skip_fit=True,
    )

    assert len(result["y_proba"]) == len(result["test"])
    assert all(p == 0.7 for p in result["y_proba"])
