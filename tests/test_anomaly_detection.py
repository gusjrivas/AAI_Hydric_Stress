import numpy as np
import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.anomaly_detection import detect_anomalies, evaluate_with_injected_anomalies


def _stable_series_df(n=60, seed=0):
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="D")
    temperature = 20.0 + rng.normal(0, 1.0, size=n)
    relative_humidity = 60.0 + rng.normal(0, 3.0, size=n)
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": timestamps,
                "temperature": temperature,
                "relative_humidity": relative_humidity,
            }
        ),
        provenance="real",
    )


def test_detect_anomalies_adds_boolean_column_without_labels():
    df = _stable_series_df()

    result = detect_anomalies(df, columns=["temperature", "relative_humidity"])

    assert "is_anomaly" in result.columns
    assert result["is_anomaly"].dtype == bool
    assert len(result) == len(df)


def test_detect_anomalies_flags_an_extreme_injected_value():
    df = _stable_series_df().copy()
    df.loc[10, "temperature"] = 200.0  # anomalía evidente respecto de la serie estable

    result = detect_anomalies(df, columns=["temperature", "relative_humidity"], contamination=0.05)

    assert bool(result.loc[10, "is_anomaly"]) is True


def test_evaluate_with_injected_anomalies_reports_detection_rate():
    df = _stable_series_df(n=100)

    detection_rate = evaluate_with_injected_anomalies(
        df,
        columns=["temperature", "relative_humidity"],
        n_injected=5,
        random_state=0,
    )

    assert 0.0 <= detection_rate <= 1.0
    assert detection_rate > 0.5  # anomalías extremas inyectadas deberían detectarse en su mayoría
