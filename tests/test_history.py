import hashlib
from datetime import date

import numpy as np
import pandas as pd
import pytest

from data_ingestion.history import HistoryError, query_readings
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
