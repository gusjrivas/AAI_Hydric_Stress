import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.imputation import interpolate_missing


def test_interpolate_missing_fills_gap_linearly_and_flags_imputed_rows():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "temperature": [20.0, None, 24.0],
            }
        ),
        provenance="real",
    )

    imputed = interpolate_missing(df, columns=["temperature"])

    middle_row = imputed[imputed["timestamp"] == "2024-01-02"].iloc[0]
    assert middle_row["temperature"] == 22.0
    assert bool(middle_row["temperature_imputado"]) is True

    first_row = imputed[imputed["timestamp"] == "2024-01-01"].iloc[0]
    assert bool(first_row["temperature_imputado"]) is False


def test_interpolate_missing_leaves_columns_without_gaps_unflagged():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "temperature": [20.0, 21.0],
            }
        ),
        provenance="real",
    )

    imputed = interpolate_missing(df, columns=["temperature"])

    assert not imputed["temperature_imputado"].any()
