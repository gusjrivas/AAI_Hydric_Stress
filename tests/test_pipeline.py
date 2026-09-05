from datetime import date

import numpy as np
import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.imputation import interpolate_missing_causal
from data_quality.pipeline import run_quality_pipeline
from data_quality.splitting import temporal_train_test_split


def _real_df(n=40, seed=0):
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="D")
    temperature = 20.0 + rng.normal(0, 2.0, size=n)
    soil_moisture = 0.3 + rng.normal(0, 0.02, size=n)
    df = normalize_to_schema(
        pd.DataFrame(
            {"timestamp": timestamps, "temperature": temperature, "soil_moisture": soil_moisture}
        ),
        provenance="real",
    )
    df.loc[5, "soil_moisture"] = None  # gap a interpolar
    return df


def test_pipeline_base_configuration_runs_without_anomaly_or_synthetic():
    df = _real_df()

    result = run_quality_pipeline(
        df,
        numeric_columns=["temperature", "soil_moisture"],
        split_date=date(2024, 1, 25),
        include_anomaly_detection=False,
        include_synthetic=False,
    )

    assert result["train"]["soil_moisture"].isna().sum() == 0  # se imputó el gap
    assert "is_anomaly" not in result["train"].columns
    assert (result["train"]["origen"] == "real").all()
    assert result["quality_report"]["missing_pct"]["soil_moisture"] > 0


def test_pipeline_complete_configuration_includes_anomaly_flag_and_synthetic_rows():
    df = _real_df()

    result = run_quality_pipeline(
        df,
        numeric_columns=["temperature", "soil_moisture"],
        split_date=date(2024, 1, 25),
        include_anomaly_detection=True,
        include_synthetic=True,
        n_synthetic_samples=10,
        random_state=0,
    )

    assert "is_anomaly" in result["train"].columns
    assert (result["train"]["origen"] == "sintetico").sum() == 10
    assert (result["train"]["origen"] == "real").sum() > 0


def test_pipeline_anomaly_detector_for_test_is_fit_on_train_not_on_itself():
    from data_quality.anomaly_detection import apply_anomaly_detector, fit_anomaly_detector

    df = _real_df(n=60, seed=3)
    numeric_columns = ["temperature", "soil_moisture"]

    result = run_quality_pipeline(
        df,
        numeric_columns=numeric_columns,
        split_date=date(2024, 1, 25),
        include_anomaly_detection=True,
        include_synthetic=False,
    )

    # reconstruye manualmente el camino metodológicamente correcto: un único
    # detector ajustado sobre train, aplicado (sin reajustar) sobre test.
    # Si `run_quality_pipeline` ajusta un detector nuevo sobre test (el bug
    # reportado), el resultado de `test["is_anomaly"]` no va a coincidir con
    # este, salvo por casualidad.
    train_raw, test_raw = temporal_train_test_split(df, split_date=date(2024, 1, 25))
    train_imputed = interpolate_missing_causal(train_raw, columns=numeric_columns)
    train_imputed = train_imputed.dropna(subset=numeric_columns).reset_index(drop=True)
    warm_start = train_imputed.iloc[-1]
    test_imputed = interpolate_missing_causal(
        test_raw, columns=numeric_columns, warm_start=warm_start
    )
    detector = fit_anomaly_detector(train_imputed, columns=numeric_columns, random_state=42)
    expected_test_is_anomaly = apply_anomaly_detector(
        test_imputed, columns=numeric_columns, detector=detector
    )["is_anomaly"].reset_index(drop=True)

    pd.testing.assert_series_equal(
        result["test"]["is_anomaly"].reset_index(drop=True),
        expected_test_is_anomaly,
        check_names=False,
    )


def test_pipeline_does_not_leak_test_statistics_into_scaling():
    df = _real_df()

    result = run_quality_pipeline(
        df,
        numeric_columns=["temperature"],
        split_date=date(2024, 1, 25),
        include_anomaly_detection=False,
        include_synthetic=False,
    )

    mean, std = result["scaling_params"]["temperature"]
    real_train_temperature = df[df["timestamp"] < "2024-01-25"]["temperature"]
    assert round(mean, 6) == round(real_train_temperature.mean(), 6)
    assert round(std, 6) == round(real_train_temperature.std(), 6)
