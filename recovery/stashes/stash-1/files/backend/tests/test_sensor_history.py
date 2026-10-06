import pandas as pd
import pytest
from app.config import get_dataset_data_dir
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import get_dataset_path, save_dataset


@pytest.fixture
def history_client(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_history_preserves_values_gaps_and_file(history_client, tmp_path):
    name = dataset_name_for("demo-history")
    save_dataset(
        name,
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-29", "2024-01-31"]),
                "soil_moisture": [0.3, None, 0.2],
                "temperature": [20.0, 21.0, float("inf")],
                "precipitation": [0.0, 1.0, 0.0],
                "origen": ["sintetico"] * 3,
            }
        ),
        data_dir=tmp_path,
    )
    file = get_dataset_path(name, data_dir=tmp_path)
    before = file.read_bytes()
    response = history_client.get("/sensors/demo-history/history?days=7")
    assert response.status_code == 200
    body = response.json()
    assert body["period_start"] == "2024-01-25"
    assert [row["fecha"] for row in body["rows"]] == ["2024-01-29", "2024-01-31"]
    assert body["rows"][0]["soil_moisture"] is None
    assert body["rows"][1]["temperature"] is None
    assert body["rows"][1]["soil_moisture"] == 0.2
    assert body["rows"][1]["origen"] == "sintetico"
    assert file.read_bytes() == before
    assert history_client.get("/sensors/other-sensor/history").status_code == 404


@pytest.mark.parametrize("days", [0, -1, 367, "invalid"])
def test_history_rejects_invalid_windows(history_client, days):
    assert history_client.get(f"/sensors/demo-history/history?days={days}").status_code == 422


def test_history_rejects_invalid_sensor(history_client):
    assert history_client.get("/sensors/invalid.sensor/history").status_code == 422
