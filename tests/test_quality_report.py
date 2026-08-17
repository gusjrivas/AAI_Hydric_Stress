import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.quality_report import quality_report


def test_quality_report_flags_out_of_range_value():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "temperature": [20.0, 80.0],  # 80.0 excede el rango plausible
            }
        ),
        provenance="real",
    )

    report = quality_report(df)

    out_of_range_timestamps = report["out_of_range"]["temperature"]
    assert pd.Timestamp("2024-01-02") in out_of_range_timestamps
    assert pd.Timestamp("2024-01-01") not in out_of_range_timestamps


def test_quality_report_flags_duplicate_timestamps():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"]),
                "temperature": [20.0, 21.0, 22.0],
            }
        ),
        provenance="real",
    )

    report = quality_report(df)

    assert pd.Timestamp("2024-01-01") in report["duplicate_timestamps"]
    assert pd.Timestamp("2024-01-02") not in report["duplicate_timestamps"]


def test_quality_report_computes_missing_percentage():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
                ),
                "temperature": [20.0, None, 22.0, None],
            }
        ),
        provenance="real",
    )

    report = quality_report(df)

    assert report["missing_pct"]["temperature"] == 50.0
