import numpy as np
import pandas as pd

from experiment_runner.runner import run_configuration


def _synthetic_dataset(n=80, seed=0):
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


def test_run_configuration_produces_one_row_per_seed():
    df = _synthetic_dataset()
    split_date = df["timestamp"].iloc[60].date()

    results = run_configuration(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=split_date,
        model_name="logistic_regression",
        include_anomaly_detection=False,
        include_synthetic=False,
        seeds=[1, 2, 3],
    )

    assert len(results) == 3
    assert list(results["seed"]) == [1, 2, 3]
    for column in ("precision", "recall", "f1", "roc_auc"):
        assert column in results.columns


def test_run_configuration_with_synthetic_augmentation_runs_without_error():
    df = _synthetic_dataset()
    split_date = df["timestamp"].iloc[60].date()

    results = run_configuration(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=split_date,
        model_name="random_forest",
        include_anomaly_detection=True,
        include_synthetic=True,
        seeds=[1, 2],
        n_synthetic_samples=20,
    )

    assert len(results) == 2
    assert not results[["precision", "recall", "f1", "roc_auc"]].isna().any().any()


def test_run_configuration_with_scarcity_scenario_runs_without_error():
    df = _synthetic_dataset()
    split_date = df["timestamp"].iloc[60].date()

    results = run_configuration(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=split_date,
        model_name="logistic_regression",
        include_anomaly_detection=False,
        include_synthetic=False,
        seeds=[1, 2],
        train_fraction=0.5,
    )

    assert len(results) == 2
    assert not results[["precision", "recall", "f1", "roc_auc"]].isna().any().any()


def test_run_configuration_with_noise_scenario_runs_without_error():
    df = _synthetic_dataset()
    split_date = df["timestamp"].iloc[60].date()

    results = run_configuration(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=split_date,
        model_name="logistic_regression",
        include_anomaly_detection=False,
        include_synthetic=False,
        seeds=[1, 2],
        noise_std_ratio=0.5,
    )

    assert len(results) == 2
    assert not results[["precision", "recall", "f1", "roc_auc"]].isna().any().any()
