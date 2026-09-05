import numpy as np
import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from predictive_modeling.contract import FittedPredictor, make_contract
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
        classes_ = np.array([0, 1])
        feature_names_in_ = np.array(
            make_contract(["soil_moisture", "solar_radiation"])["model_features"]
        )

        def fit(self, X, y):
            raise AssertionError("fit no debería llamarse cuando skip_fit=True")

        def predict_proba(self, X):
            return np.tile([0.3, 0.7], (len(X), 1))

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[45].date(),
        model=FittedPredictor(
            _FitRaisesModel(),
            make_contract(["soil_moisture", "solar_radiation"]),
            0.32,
            "2024-02-14",
        ),
        include_anomaly_detection=False,
        skip_fit=True,
    )

    assert len(result["y_proba"]) == len(result["test"])
    assert all(p == 0.7 for p in result["y_proba"])


def test_run_end_to_end_pipeline_includes_is_anomaly_as_a_feature_when_enabled():
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

    assert "is_anomaly" in result["feature_columns"]
    assert "is_anomaly" in result["train"].columns


def test_run_end_to_end_pipeline_excludes_is_anomaly_when_disabled():
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

    assert "is_anomaly" not in result["feature_columns"]


def test_run_end_to_end_pipeline_selects_a_model_automatically_when_none_given():
    df = _synthetic_dataset(n=150, seed=2)

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[110].date(),
        model=None,
        include_anomaly_detection=False,
    )

    assert result["model_name"] in {"logistic_regression", "random_forest"}
    assert hasattr(result["model"], "predict_proba")
    assert len(result["y_proba"]) == len(result["test"])


def test_run_end_to_end_pipeline_purges_train_rows_whose_target_crosses_into_test():
    df = _synthetic_dataset(n=60)
    model = build_candidate_models(random_state=0)["logistic_regression"]
    split_date = df["timestamp"].iloc[45].date()
    horizon_days = 3

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=split_date,
        model=model,
        horizon_days=horizon_days,
        include_anomaly_detection=False,
    )

    # las últimas `horizon_days` fechas antes de split_date tendrían un
    # target (soil_moisture horizon_days filas adelante) que cae dentro de
    # test -- no deben aparecer en train.
    cutoff = pd.Timestamp(split_date)
    purged_dates = pd.date_range(end=cutoff, periods=horizon_days + 1, freq="D")[:-1]
    assert not result["train"]["timestamp"].isin(purged_dates).any()
    assert result["train"]["timestamp"].max() < purged_dates.min()


def test_changing_a_test_period_value_does_not_change_the_selected_model_or_its_training_data():
    baseline_df = _synthetic_dataset(n=150, seed=2)
    modified_df = baseline_df.copy()
    # cambia radicalmente un valor bien adentro de lo que será test
    modified_df.loc[140, "soil_moisture"] = 999.0
    split_date = baseline_df["timestamp"].iloc[110].date()

    baseline_result = run_end_to_end_pipeline(
        baseline_df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=split_date,
        model=None,
        include_anomaly_detection=False,
    )
    modified_result = run_end_to_end_pipeline(
        modified_df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=split_date,
        model=None,
        include_anomaly_detection=False,
    )

    pd.testing.assert_frame_equal(
        baseline_result["train"].drop(columns=["soil_moisture_imputado"], errors="ignore"),
        modified_result["train"].drop(columns=["soil_moisture_imputado"], errors="ignore"),
    )


def test_run_end_to_end_pipeline_leaves_model_name_none_when_model_is_given():
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

    assert result["model_name"] is None
