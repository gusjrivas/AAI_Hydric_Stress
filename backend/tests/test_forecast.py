from pathlib import Path

from fastapi.testclient import TestClient

from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir, get_feedback_data_dir
from app.main import app
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset, save_dataset


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_run_forecast_returns_verdicts(tmp_path: Path):
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/forecast/sensor-a/run")

    assert response.status_code == 200
    body = response.json()
    assert body["train_rows"] > 0
    assert body["test_rows"] > 0
    assert len(body["verdicts"]) == body["test_rows"]
    first = body["verdicts"][0]
    assert set(first.keys()) == {"fecha", "alerta", "probabilidad"}

    app.dependency_overrides.clear()


def test_run_forecast_returns_404_when_dataset_missing(tmp_path: Path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/forecast/sensor-inexistente/run")

    assert response.status_code == 404
    assert "sensor__sensor-inexistente" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_run_forecast_isolates_feedback_between_sensors(tmp_path: Path):
    _seed_sensor_dataset("sensor-a", tmp_path)
    _seed_sensor_dataset("sensor-b", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/forecast/sensor-a/run")
    response_b = client.post("/forecast/sensor-b/run")

    assert response_b.status_code == 200
    feedback_a = client.get("/feedback/sensor-a").json()["rows"]
    feedback_b = client.get("/feedback/sensor-b").json()["rows"]
    assert len(feedback_a) > 0
    assert len(feedback_b) > 0

    app.dependency_overrides.clear()
