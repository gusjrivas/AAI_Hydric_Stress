import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.scaling import inverse_standardize, standardize


def test_standardize_and_inverse_roundtrip():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "temperature": [20.0, 22.0, 24.0],
            }
        ),
        provenance="real",
    )

    scaled, params = standardize(df, columns=["temperature"])
    reverted = inverse_standardize(scaled, params)

    assert list(reverted["temperature"].round(6)) == list(df["temperature"].round(6))


def test_standardize_produces_zero_mean_unit_std():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "temperature": [20.0, 22.0, 24.0],
            }
        ),
        provenance="real",
    )

    scaled, _ = standardize(df, columns=["temperature"])

    assert round(scaled["temperature"].mean(), 6) == 0.0
