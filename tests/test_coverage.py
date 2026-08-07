import pandas as pd
import pytest

from data_ingestion.coverage import coverage_report
from data_ingestion.schema import normalize_to_schema


def test_coverage_report_reports_completeness_per_required_column():
    raw = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "temperature": [20.0, 21.0, None],
            "precipitation": [0.0, None, None],
        }
    )
    df = normalize_to_schema(raw, provenance="real")

    report = coverage_report(df)
    by_column = report.set_index("column")

    assert by_column.loc["temperature", "completeness_pct"] == pytest.approx(66.67, rel=1e-2)
    assert by_column.loc["precipitation", "completeness_pct"] == pytest.approx(33.33, rel=1e-2)
    assert by_column.loc["temperature", "start"] == pd.Timestamp("2026-01-01")
    assert by_column.loc["temperature", "end"] == pd.Timestamp("2026-01-02")


def test_coverage_report_zero_percent_when_column_absent_entirely():
    raw = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [20.0]})
    df = normalize_to_schema(raw, provenance="real")

    report = coverage_report(df)
    by_column = report.set_index("column")

    assert by_column.loc["soil_moisture", "completeness_pct"] == 0.0
    assert pd.isna(by_column.loc["soil_moisture", "start"])
