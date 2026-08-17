import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.distributions import describe_variables


def test_describe_variables_reports_dtype_min_max_mean_std():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "temperature": [20.0, 22.0, 24.0],
            }
        ),
        provenance="real",
    )

    report = describe_variables(df)

    row = report[report["column"] == "temperature"].iloc[0]
    assert row["dtype"] == "float64"
    assert row["min"] == 20.0
    assert row["max"] == 24.0
    assert row["mean"] == 22.0
    assert round(row["std"], 4) == round(pd.Series([20.0, 22.0, 24.0]).std(), 4)


def test_describe_variables_skips_columns_absent_from_df():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01"]),
                "temperature": [20.0],
            }
        ),
        provenance="real",
    )
    # soil_moisture existe en el esquema pero queda todo NaN (normalize_to_schema
    # la agrega). No debe aparecer con estadísticas espurias.

    report = describe_variables(df)

    soil_moisture_row = report[report["column"] == "soil_moisture"]
    assert (
        soil_moisture_row.empty
        or soil_moisture_row.iloc[0][["min", "max", "mean", "std"]].isna().all()
    )
