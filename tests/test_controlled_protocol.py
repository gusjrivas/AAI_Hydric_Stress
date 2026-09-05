from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from architecture_integration.pipeline import predict_available, run_end_to_end_pipeline
from data_quality.temporal import validate_daily_series
from experiment_runner.runner import run_configuration
from experiment_runner.scenarios import (
    fit_noise_scales,
    inject_gaussian_noise,
    select_training_dates,
)
from human_feedback.recalibration import recalibrate_predictor
from human_feedback.schema import init_prediction_feedback, update_feedback
from predictive_modeling.contract import ModelContractMismatch
from predictive_modeling.model_selection import select_best_candidate


def dataset(n=100):
    rng = np.random.default_rng(4)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n),
            "soil_moisture": rng.uniform(0.1, 0.5, n),
            "solar_radiation": rng.uniform(5, 30, n),
        }
    )


def run(df, **kwargs):
    params = dict(
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df.timestamp.iloc[75].date(),
        model=RandomForestClassifier(n_estimators=5, random_state=0),
        include_anomaly_detection=False,
    )
    return run_end_to_end_pipeline(df, **(params | kwargs))


@pytest.mark.parametrize("kind", ["gap", "duplicate", "intraday", "null"])
def test_daily_contract_rejects_invalid_calendars(kind):
    df = dataset()
    if kind == "gap":
        df = df.drop(index=20)
    if kind == "duplicate":
        df.loc[20, "timestamp"] = df.timestamp.iloc[19]
    if kind == "intraday":
        df.loc[20, "timestamp"] += pd.Timedelta(hours=1)
    if kind == "null":
        df.loc[20, "timestamp"] = pd.NaT
    with pytest.raises(ValueError):
        validate_daily_series(df)


def test_target_missing_is_not_imputed_or_removed_before_temporal_features():
    df = dataset()
    df.loc[80, "soil_moisture"] = np.nan
    result = run(df)
    assert df.timestamp.iloc[77] not in result["test"].timestamp.tolist()
    row = result["test"].set_index("timestamp").loc[df.timestamp.iloc[81]]
    assert row.soil_moisture_lag1 == df.soil_moisture.iloc[79]
    assert (result["train"].target_timestamp < df.timestamp.iloc[75]).all()
    assert result["test"].target_observed.all()


def test_explicit_features_exclude_unrequested_preexisting_columns():
    df = dataset()
    df["future_lag_injected"] = 999
    result = run(df)
    assert len(result["feature_columns"]) == 10
    assert "future_lag_injected" not in result["feature_columns"]
    assert "soil_moisture" not in result["feature_columns"]
    current = run(df, include_current=True)
    assert "soil_moisture" in current["feature_columns"]


def test_noise_requires_train_scales_and_preserves_missing_observations():
    df = dataset()
    scales = fit_noise_scales(df.iloc[:75], ["soil_moisture"])
    with pytest.raises(ValueError):
        inject_gaussian_noise(df, ["soil_moisture"], 0.3)
    modified = df.copy()
    modified.loc[80, "soil_moisture"] = 100
    a = inject_gaussian_noise(df, ["soil_moisture"], 0.3, scales=scales)
    b = inject_gaussian_noise(modified, ["soil_moisture"], 0.3, scales=scales)
    pd.testing.assert_frame_equal(a.iloc[:75], b.iloc[:75])


def test_scenarios_share_targets_and_training_budget():
    df = dataset()
    params = dict(
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df.timestamp.iloc[75].date(),
        model_name="random_forest",
        include_anomaly_detection=False,
        include_synthetic=False,
        seeds=[0],
    )
    base = run_configuration(df, **params)
    for changes in [
        {"noise_std_ratio": 0.3},
        {"train_fraction": 0.5, "scarcity_mode": "coverage"},
        {"train_fraction": 0.5, "scarcity_mode": "recent"},
    ]:
        result = run_configuration(df, **params, **changes)
        left = base.attrs["artifacts"][0]["predictions"]
        right = result.attrs["artifacts"][0]["predictions"]
        pd.testing.assert_frame_equal(left[["timestamp", "y_true"]], right[["timestamp", "y_true"]])
        assert base.threshold.iloc[0] == result.threshold.iloc[0]
    dates = df.timestamp.iloc[7:72]
    coverage = select_training_dates(dates, 0.5, "coverage", 0)
    recent = select_training_dates(dates, 0.5, "recent", 0)
    assert len(coverage) == len(recent)
    assert min(coverage) < min(recent)


def test_reuse_freezes_threshold_and_detector_and_predicts_unlabeled_tail(monkeypatch):
    df = dataset()
    result = run(df, include_anomaly_detection=True)
    predictor = result["predictor"]

    def fail(*args, **kwargs):
        raise AssertionError("No debe reajustar")

    monkeypatch.setattr(predictor.model, "fit", fail)
    monkeypatch.setattr(predictor.detector, "fit", fail)
    monkeypatch.setattr("architecture_integration.pipeline.fit_stress_threshold", fail)
    reused = run(df, model=predictor, skip_fit=True, include_anomaly_detection=True)
    assert reused["threshold"] == result["threshold"]
    forecasts = predict_available(df, predictor)
    assert forecasts.timestamp.max() == df.timestamp.max()
    assert forecasts.target_timestamp.max() == df.timestamp.max() + pd.Timedelta(days=3)
    with pytest.raises(ModelContractMismatch):
        run(df, model=predictor, skip_fit=True, include_anomaly_detection=True, lags=[2])


def test_recalibration_replays_corrections_and_excludes_used_dates_from_evaluation():
    df = dataset()
    original = run(df)["predictor"]
    forecasts = predict_available(df, original).tail(2).reset_index(drop=True)
    log = init_prediction_feedback(forecasts, original.model_id, 3, original.threshold)
    log = update_feedback(log, forecasts.timestamp.iloc[0], "rechazada", 1)
    updated, dates, _ = recalibrate_predictor(original, df, log)
    assert updated.trained_through > original.trained_through
    assert updated.applied_feedback[str(dates[0])] == 1
    with pytest.raises(ValueError, match="nuevas"):
        recalibrate_predictor(updated, df, log)
    reused = run(df, model=updated, skip_fit=True)
    assert reused["test"].empty
    log = update_feedback(log, forecasts.timestamp.iloc[1], "rechazada", 0)
    again, _, _ = recalibrate_predictor(updated, df, log)
    assert len(again.applied_feedback) == 2
    assert again.model_id != updated.model_id


def test_contract_rejects_metadata_only_feature_change():
    bundle = run(dataset())["predictor"]
    changed = replace(bundle, contract={**bundle.contract, "model_features": ["unrelated"]})
    with pytest.raises(ModelContractMismatch):
        changed.validate(changed.contract)


def test_fold_local_anomaly_transform_does_not_fit_on_validation():
    from sklearn.base import clone
    from sklearn.pipeline import Pipeline

    from predictive_modeling.anomaly_features import AnomalyFeatures

    df = dataset()
    X = df[["soil_moisture", "solar_radiation"]]
    y = (df.soil_moisture.shift(-3) < 0.2).astype(int)
    pipeline = Pipeline(
        [
            ("features", AnomalyFeatures(["soil_moisture", "solar_radiation"], ["soil_moisture"])),
            ("classifier", RandomForestClassifier(n_estimators=5, random_state=0)),
        ]
    )
    first = clone(pipeline).fit(X.iloc[:60], y.iloc[:60])
    original = first.named_steps["features"].transform(X.iloc[:60])
    changed_validation = X.iloc[63:80].copy() * 100
    first.predict(changed_validation)
    pd.testing.assert_frame_equal(original, first.named_steps["features"].transform(X.iloc[:60]))
    assert first.named_steps["features"].detector_.max_samples_ == 60


def test_automatic_selection_calibration_precedes_all_training_examples(monkeypatch):
    captured = []

    def select(X, y, **kwargs):
        fitted = RandomForestClassifier(n_estimators=5, random_state=0).fit(X, y)
        captured.append(X)
        return {
            "model": fitted,
            "model_name": "random_forest",
            "selection_warning": None,
            "fold_diagnostics": [],
        }

    monkeypatch.setattr("architecture_integration.pipeline.select_best_candidate", select)
    df = dataset()
    first = run(df, model=None)
    df.loc[60, "soil_moisture"] = 0.001
    second = run(df, model=None)
    assert first["threshold"] == second["threshold"]
    assert first["train"].timestamp.min() > pd.Timestamp(first["predictor"].calibration_end)
    assert len(captured) == 2


def test_empty_and_single_class_evaluation_are_explicit():
    from predictive_modeling.evaluation import evaluate_classifier

    empty = evaluate_classifier(pd.Series(dtype=int), pd.Series(dtype=int), pd.Series(dtype=float))
    assert all(np.isnan(v) for v in empty.values())
    single = evaluate_classifier(pd.Series([0, 0]), pd.Series([0, 0]), pd.Series([0.1, 0.2]))
    assert np.isnan(single["roc_auc"])
    assert np.isnan(single["average_precision"])


def test_automatic_selection_fails_when_any_common_fold_lacks_both_classes():
    X = pd.DataFrame({"x": range(20)})
    y = pd.Series([0] * 12 + [1] * 8)
    with pytest.raises(ValueError, match="folds sin ambas clases"):
        select_best_candidate(
            X,
            y,
            candidates={"random_forest": RandomForestClassifier(n_estimators=2)},
            param_grids={"random_forest": {"n_estimators": [2]}},
            n_splits=4,
            gap=3,
        )


def test_recalibration_rejects_history_missing_previous_correction():
    df = dataset()
    predictor = run(df)["predictor"]
    predictor.applied_feedback = {str(df.timestamp.iloc[20]): 1}
    forecasts = predict_available(df, predictor).tail(1).reset_index(drop=True)
    log = init_prediction_feedback(forecasts, predictor.model_id, 3, predictor.threshold)
    log = update_feedback(log, forecasts.timestamp.iloc[0], "rechazada", 0)
    with pytest.raises(ValueError, match="reaplicar"):
        recalibrate_predictor(predictor, df.iloc[30:], log)
