import numpy as np
import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.synthetic_data import (
    evaluate_predictive_utility,
    generate_synthetic,
    statistical_similarity,
)


def _correlated_real_df(n=200, seed=0):
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="D")
    temperature = 20.0 + rng.normal(0, 3.0, size=n)
    # humedad de suelo correlacionada negativamente con temperatura, con ruido
    soil_moisture = 0.4 - 0.01 * temperature + rng.normal(0, 0.01, size=n)
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": timestamps,
                "temperature": temperature,
                "soil_moisture": soil_moisture,
            }
        ),
        provenance="real",
    )


def test_generate_synthetic_marks_provenance_and_row_count():
    real_df = _correlated_real_df()

    synthetic_df = generate_synthetic(
        real_df, columns=["temperature", "soil_moisture"], n_samples=150, random_state=0
    )

    assert len(synthetic_df) == 150
    assert (synthetic_df["origen"] == "sintetico").all()
    assert set(synthetic_df.columns) == set(real_df.columns)


def test_statistical_similarity_reports_close_mean_std_and_correlation():
    real_df = _correlated_real_df()
    synthetic_df = generate_synthetic(
        real_df, columns=["temperature", "soil_moisture"], n_samples=2000, random_state=0
    )

    similarity = statistical_similarity(
        real_df, synthetic_df, columns=["temperature", "soil_moisture"]
    )

    assert abs(similarity["mean_diff"]["temperature"]) < 0.5
    assert abs(similarity["std_diff"]["temperature"]) < 0.5
    assert similarity["correlation_diff"] < 0.15


def test_evaluate_predictive_utility_returns_error_for_both_real_and_synthetic():
    real_df = _correlated_real_df(n=200, seed=1)
    train_df = real_df.iloc[:150].reset_index(drop=True)
    test_df = real_df.iloc[150:].reset_index(drop=True)
    synthetic_train_df = generate_synthetic(
        train_df, columns=["temperature", "soil_moisture"], n_samples=150, random_state=1
    )

    result = evaluate_predictive_utility(
        train_real=train_df,
        train_synthetic=synthetic_train_df,
        test_real=test_df,
        feature_columns=["temperature"],
        target_column="soil_moisture",
    )

    assert "mae_real" in result
    assert "mae_synthetic" in result
    assert result["mae_real"] >= 0
    assert result["mae_synthetic"] >= 0
