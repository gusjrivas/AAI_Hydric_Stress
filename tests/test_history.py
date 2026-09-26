import hashlib
from datetime import date

import numpy as np
import pandas as pd
import pytest

from data_ingestion.history import (
    EXTERNAL_REANALYSIS_RAW_VALUE,
    HistoryError,
    query_readings,
)
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import save_dataset


def _save_history(data_dir, sensor_id="sensor-a"):
    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-03", "2026-01-04"]),
            "soil_moisture": [0.21, np.nan, 0.18],
            "relative_humidity": [70.0, 68.0, np.inf],
            "solar_radiation": [15.0, 16.0, 17.0],
            "temperature": [25.0, 26.0, 27.0],
            "precipitation": [0.0, np.nan, 2.0],
            "wind_speed": [2.0, 2.5, 3.0],
            "et0": [3.0, 3.1, 3.2],
            "origen": ["real", "sintetico", None],
        }
    )
    save_dataset(dataset_name_for(sensor_id), dataframe, data_dir=data_dir)
    return data_dir / f"{dataset_name_for(sensor_id)}.parquet"


def test_history_windows_share_snapshot_and_common_rows(tmp_path):
    path = _save_history(tmp_path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    seven = query_readings(
        "sensor-a",
        tmp_path,
        registered=False,
        days=7,
        end=date(2026, 1, 4),
        server_today=date(2026, 1, 5),
    )
    thirty = query_readings(
        "sensor-a",
        tmp_path,
        registered=False,
        days=30,
        end=date(2026, 1, 4),
        server_today=date(2026, 1, 5),
    )

    assert seven["snapshot_id"] == thirty["snapshot_id"] == before
    assert seven["rows"] == thirty["rows"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_history_exposes_missing_dates_nulls_units_quality_and_provenance(tmp_path):
    _save_history(tmp_path)

    result = query_readings(
        "sensor-a",
        tmp_path,
        registered=False,
        days=4,
        end=date(2026, 1, 4),
        server_today=date(2026, 1, 5),
    )

    assert result["missing_dates"] == [date(2026, 1, 2)]
    assert result["rows"][1]["soil_moisture"] is None
    assert result["rows"][1]["origin"] == "synthetic"
    assert result["rows"][2]["relative_humidity"] is None
    assert "non_finite:relative_humidity" in result["rows"][2]["quality_flags"]
    assert "unknown_origin" in result["rows"][2]["quality_flags"]
    assert result["provenance"] == "unknown"
    assert result["units"]["soil_moisture"] == "m3/m3"
    assert result["input_roles"][0]["basis"] == "configured"
    soil_coverage = next(
        item for item in result["variable_coverage"] if item["variable"] == "soil_moisture"
    )
    assert soil_coverage == {
        "variable": "soil_moisture",
        "observed_days": 2,
        "missing_days": 2,
    }


def test_last_reading_date_and_age_reflect_the_clock_not_the_whole_file(tmp_path):
    """Regression: browsing a historical clock earlier than the file's
    latest row must never report that later row as `last_reading_date`,
    nor a negative `data_age_days` -- and the admissible last reading can
    be *before* the displayed window's start, so it must be found by
    scanning the whole file up to the clock, not just the window slice."""
    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2023-06-13", "2023-06-20"]),
            "soil_moisture": [0.30, 0.25],
            "relative_humidity": [65.0, 64.0],
            "solar_radiation": [18.0, 17.0],
            "temperature": [22.0, 21.0],
            "precipitation": [0.0, 0.0],
            "wind_speed": [3.0, 3.2],
            "et0": [4.0, 4.1],
            "origen": [EXTERNAL_REANALYSIS_RAW_VALUE, EXTERNAL_REANALYSIS_RAW_VALUE],
        }
    )
    save_dataset(dataset_name_for("sensor-a"), dataframe, data_dir=tmp_path)

    # A 2-day window ending 2023-06-13 would only contain 06-12/06-13 --
    # the admissible last reading (06-13 itself) is inside it here, but
    # the search must not depend on that coincidence (see the second
    # assertion below, where the window is narrower than the gap).
    at_earlier_clock = query_readings(
        "sensor-a", tmp_path, registered=False, days=2,
        end=date(2023, 6, 13), server_today=date(2023, 6, 13),
    )
    assert at_earlier_clock["last_reading_date"] == date(2023, 6, 13)
    assert at_earlier_clock["data_age_days"] == 0
    assert all(row["date"] <= date(2023, 6, 13) for row in at_earlier_clock["rows"])

    # A 1-day window ending 2023-06-16 excludes both actual rows from the
    # window slice entirely -- the admissible last reading (06-13) is
    # *before* window_start (06-16), so it can only be found by scanning
    # the whole file up to the clock, never just the window.
    with_gap_before_window = query_readings(
        "sensor-a", tmp_path, registered=False, days=1,
        end=date(2023, 6, 16), server_today=date(2023, 6, 16),
    )
    assert with_gap_before_window["last_reading_date"] == date(2023, 6, 13)
    assert with_gap_before_window["data_age_days"] == 3
    assert with_gap_before_window["rows"] == []

    # Browsing forward to 06-20 legitimately reveals the later row.
    at_later_clock = query_readings(
        "sensor-a", tmp_path, registered=False, days=2,
        end=date(2023, 6, 20), server_today=date(2023, 6, 20),
    )
    assert at_later_clock["last_reading_date"] == date(2023, 6, 20)
    assert at_later_clock["data_age_days"] == 0


def test_status_is_no_readings_when_nothing_is_admissible_yet_despite_a_nonempty_file(tmp_path):
    """A file with data, none of it admissible under the effective clock
    (all rows are in its future), must read the same as no readings at
    all -- never "ready" with an empty row list and no last reading."""
    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2023-06-20"]),
            "soil_moisture": [0.25], "relative_humidity": [64.0], "solar_radiation": [17.0],
            "temperature": [21.0], "precipitation": [0.0], "wind_speed": [3.2], "et0": [4.1],
            "origen": [EXTERNAL_REANALYSIS_RAW_VALUE],
        }
    )
    save_dataset(dataset_name_for("sensor-a"), dataframe, data_dir=tmp_path)

    result = query_readings(
        "sensor-a", tmp_path, registered=False, days=5,
        end=date(2023, 6, 13), server_today=date(2023, 6, 13),
    )
    assert result["status"] == "no_readings"
    assert result["rows"] == []
    assert result["last_reading_date"] is None
    assert result["data_age_days"] is None


def test_external_reanalysis_origin_is_recognized_and_never_reclassified(tmp_path):
    """`origen=EXTERNAL_REANALYSIS_RAW_VALUE` (ERA5-Land + NASA POWER, Hito 2)
    is a distinct, recognized category -- never "real" (would claim a
    physical sensor of ours), never "synthetic" (it is genuine external
    data), and never silently "unknown"."""
    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2023-06-13", "2023-06-14", "2023-06-15"]),
            "soil_moisture": [0.30, 0.31, 0.29],
            "relative_humidity": [55.0, 56.0, 54.0],
            "solar_radiation": [20.0, 21.0, 19.0],
            "temperature": [22.0, 23.0, 21.0],
            "precipitation": [0.0, 0.0, 0.0],
            "wind_speed": [2.0, 2.0, 2.0],
            "et0": [3.0, 3.0, 3.0],
            "origen": [EXTERNAL_REANALYSIS_RAW_VALUE] * 3,
        }
    )
    save_dataset(dataset_name_for("pergamino-ensemble-demo"), dataframe, data_dir=tmp_path)

    result = query_readings(
        "pergamino-ensemble-demo",
        tmp_path,
        registered=False,
        days=3,
        end=date(2023, 6, 15),
        server_today=date(2023, 6, 16),
    )

    assert all(row["origin"] == "external_reanalysis" for row in result["rows"])
    assert result["provenance"] == "external_reanalysis"
    assert not any("unknown_origin" in row["quality_flags"] for row in result["rows"])


def test_mixed_external_reanalysis_and_real_origins_reduce_to_mixed(tmp_path):
    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2023-06-13", "2023-06-14"]),
            "soil_moisture": [0.30, 0.31],
            "relative_humidity": [55.0, 56.0],
            "solar_radiation": [20.0, 21.0],
            "temperature": [22.0, 23.0],
            "precipitation": [0.0, 0.0],
            "wind_speed": [2.0, 2.0],
            "et0": [3.0, 3.0],
            "origen": [EXTERNAL_REANALYSIS_RAW_VALUE, "real"],
        }
    )
    save_dataset(dataset_name_for("sensor-mixed"), dataframe, data_dir=tmp_path)

    result = query_readings(
        "sensor-mixed",
        tmp_path,
        registered=False,
        days=2,
        end=date(2023, 6, 14),
        server_today=date(2023, 6, 15),
    )

    assert result["rows"][0]["origin"] == "external_reanalysis"
    assert result["rows"][1]["origin"] == "real"
    assert result["provenance"] == "mixed"


def test_registered_sensor_without_dataset_returns_no_readings(tmp_path):
    result = query_readings(
        "sensor-a",
        tmp_path,
        registered=True,
        days=7,
        end=date(2026, 1, 7),
        server_today=date(2026, 1, 7),
    )

    assert result["status"] == "no_readings"
    assert result["rows"] == []
    assert result["snapshot_id"] is None
    assert len(result["missing_dates"]) == 7


def test_unknown_sensor_without_dataset_is_not_found(tmp_path):
    with pytest.raises(HistoryError) as raised:
        query_readings(
            "sensor-a",
            tmp_path,
            registered=False,
            server_today=date(2026, 1, 7),
        )

    assert raised.value.code == "sensor_not_found"
    assert raised.value.status_code == 404


def test_storage_failure_is_not_reported_as_empty_history(tmp_path):
    path = tmp_path / f"{dataset_name_for('sensor-a')}.parquet"
    path.write_bytes(b"not parquet")

    with pytest.raises(HistoryError) as raised:
        query_readings(
            "sensor-a",
            tmp_path,
            registered=True,
            server_today=date(2026, 1, 7),
        )

    assert raised.value.code == "readings_storage_unavailable"
    assert raised.value.status_code == 503


@pytest.mark.parametrize(
    "timestamps",
    [
        ["2026-01-01", "2026-01-01"],
        ["2026-01-01T12:00:00"],
    ],
)
def test_invalid_daily_calendar_returns_conflict(tmp_path, timestamps):
    save_dataset(
        dataset_name_for("sensor-a"),
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(timestamps),
                "origen": ["real"] * len(timestamps),
            }
        ),
        data_dir=tmp_path,
    )

    with pytest.raises(HistoryError) as raised:
        query_readings(
            "sensor-a",
            tmp_path,
            registered=False,
            server_today=date(2026, 1, 7),
        )

    assert raised.value.code == "invalid_calendar"
    assert raised.value.status_code == 409


def test_history_rejects_out_of_range_window(tmp_path):
    with pytest.raises(HistoryError) as raised:
        query_readings("sensor-a", tmp_path, registered=True, days=366)

    assert raised.value.code == "invalid_window"
    assert raised.value.status_code == 422
