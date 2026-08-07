import pandas as pd

from data_ingestion.aggregation import to_daily
from data_ingestion.schema import normalize_to_schema


def test_to_daily_averages_temperature_and_sums_precipitation_preserving_native_series():
    raw = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2026-01-01 00:00", "2026-01-01 12:00", "2026-01-02 00:00"]
            ),
            "temperature": [20.0, 24.0, 22.0],
            "precipitation": [1.0, 2.0, 0.5],
        }
    )
    native = normalize_to_schema(raw, provenance="real")

    daily = to_daily(native)

    day1 = daily[daily["timestamp"] == pd.Timestamp("2026-01-01")].iloc[0]
    assert day1["temperature"] == 22.0
    assert day1["precipitation"] == 3.0

    # La serie nativa no se modifica: sigue teniendo sus 3 filas originales.
    assert len(native) == 3
    assert native["timestamp"].tolist() == raw["timestamp"].tolist()
