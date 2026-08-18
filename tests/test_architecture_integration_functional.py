import numpy as np
import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from predictive_modeling.models import build_candidate_models


def _dataset_with_missing_values(n=70, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime(pd.date_range("2024-01-01", periods=n, freq="D"))
    soil_moisture = rng.normal(0.35, 0.03, size=n)
    solar_radiation = rng.normal(20, 3, size=n)

    soil_moisture[[3, 4, 15, 30, 31, 32]] = np.nan

    return pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": soil_moisture,
            "solar_radiation": solar_radiation,
        }
    )


def test_missing_values_are_interpolated_before_labeling_and_feature_engineering():
    df = _dataset_with_missing_values()
    model = build_candidate_models(random_state=0)["logistic_regression"]

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[55].date(),
        model=model,
        include_anomaly_detection=False,
    )

    feature_cols = result["feature_columns"]
    assert not result["test"][feature_cols].isna().any().any()
    assert not result["train"][feature_cols].isna().any().any()


def test_disabling_anomaly_detection_omits_is_anomaly_column():
    df = _dataset_with_missing_values()
    model = build_candidate_models(random_state=0)["logistic_regression"]

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[55].date(),
        model=model,
        include_anomaly_detection=False,
    )

    assert "is_anomaly" not in result["train"].columns
    assert "is_anomaly" not in result["test"].columns


def test_end_to_end_result_is_consistent_across_train_test_and_feedback():
    df = _dataset_with_missing_values()
    model = build_candidate_models(random_state=0)["random_forest"]

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[55].date(),
        model=model,
        include_anomaly_detection=True,
    )

    assert len(result["alerts"]) == len(result["test"])
    assert len(result["feedback_log"]) == len(result["test"])
    assert set(result["feedback_log"]["alerta_generada"]) <= {0, 1}
    assert "is_anomaly" in result["train"].columns
    assert "is_anomaly" in result["test"].columns
