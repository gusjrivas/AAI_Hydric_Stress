import pandas as pd
import pytest

from data_ingestion.consolidate import consolidate_sources
from data_ingestion.schema import normalize_to_schema


def _climate_frame() -> pd.DataFrame:
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "temperature": [20.0, 21.0],
            }
        ),
        provenance="real",
    )


def _soil_moisture_frame() -> pd.DataFrame:
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "soil_moisture": [0.25, 0.31],
            }
        ),
        provenance="real",
    )


def test_consolidate_sources_combines_complementary_columns_by_timestamp():
    consolidated = consolidate_sources([_climate_frame(), _soil_moisture_frame()])

    row = consolidated[consolidated["timestamp"] == "2024-01-01"].iloc[0]
    assert row["temperature"] == 20.0
    assert row["soil_moisture"] == 0.25
    assert row["origen"] == "real"


def test_consolidate_sources_requires_at_least_one_frame():
    with pytest.raises(ValueError):
        consolidate_sources([])
