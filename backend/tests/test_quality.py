from pathlib import Path

import mlflow
from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, get_dataset_path, load_dataset, save_dataset


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_quality_report_returns_real_diagnostics(tmp_path):
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/quality/sensor-a")

    assert response.status_code == 200
    body = response.json()
    assert body["sensor_id"] == "sensor-a"
    assert body["total_rows"] > 0
    assert body["period_start"] is not None
    assert body["period_end"] is not None
    assert "soil_moisture" in body["missing_pct"]
    assert isinstance(body["duplicate_timestamps"], list)
    assert isinstance(body["out_of_range"], dict)
    assert isinstance(body["anomalies_detected"], int)
    assert body["anomaly_method"] == "isolation_forest"
    assert body["is_diagnostic_only"] is True
    assert "include_anomaly_detection=False" in body["note"]

    app.dependency_overrides.clear()


def test_quality_report_returns_404_for_missing_sensor(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/quality/sensor-inexistente")

    assert response.status_code == 404
    assert "sensor__sensor-inexistente" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_quality_report_rejects_invalid_sensor_id(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/quality/sensor con espacios")

    assert response.status_code == 422

    app.dependency_overrides.clear()


def test_quality_report_has_no_side_effects(tmp_path):
    """El diagnóstico de calidad es exploratorio y de solo lectura: no debe
    modificar el dataset ni crear ningún run de MLflow."""
    _use_sqlite_tracking(tmp_path, "test-quality-no-side-effects")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    dataset_path = get_dataset_path(dataset_name_for("sensor-a"), tmp_path)
    before_bytes = dataset_path.read_bytes()
    experiment = mlflow.get_experiment_by_name("test-quality-no-side-effects")

    response = client.get("/quality/sensor-a")

    assert response.status_code == 200
    assert dataset_path.read_bytes() == before_bytes
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    assert runs.empty

    app.dependency_overrides.clear()
