from datetime import date

import pandas as pd

from historical_replay.history_view import filtered_history


def _dataset():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-10-01", periods=5, freq="D"),
            "soil_moisture": [0.30, 0.31, 0.32, 0.33, 0.34],
            "solar_radiation": [10, 11, 12, 13, 14],
        }
    )


def test_only_rows_up_to_the_simulated_clock_are_returned():
    view = filtered_history(
        _dataset(), columns=["soil_moisture"], simulated_clock=date(2024, 10, 3)
    )

    assert list(view["timestamp"].dt.date) == [
        date(2024, 10, 1),
        date(2024, 10, 2),
        date(2024, 10, 3),
    ]


def test_future_rows_are_absent_not_just_hidden():
    view = filtered_history(
        _dataset(), columns=["soil_moisture"], simulated_clock=date(2024, 10, 1)
    )

    assert len(view) == 1
    assert "2024-10-02" not in view["timestamp"].astype(str).values[0]


def test_only_requested_columns_plus_timestamp_are_exposed():
    view = filtered_history(
        _dataset(), columns=["soil_moisture"], simulated_clock=date(2024, 10, 5)
    )

    assert list(view.columns) == ["timestamp", "soil_moisture"]
    assert "solar_radiation" not in view.columns
