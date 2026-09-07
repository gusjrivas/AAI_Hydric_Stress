from pathlib import Path

import mlflow
from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir, get_feedback_data_dir
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset, save_dataset


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_active_predictor_is_explicit_when_nothing_ran_yet(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-active-predictor-empty")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/models/sensor-a/active")

    assert response.status_code == 200
    body = response.json()
    assert body["origin"] is None
    assert body["model_id"] is None
    assert body["version"] is None
    assert body["trained_through"] is None
    assert body["calibration_end"] is None
    assert body["applied_feedback_count"] == 0
    assert body["applied_feedback_dates"] == []
    # Config del contrato siempre disponible, no depende de que exista un predictor.
    assert body["horizon_days"] == 3
    assert body["feature_columns"] == ["soil_moisture", "solar_radiation", "relative_humidity"]

    app.dependency_overrides.clear()


def test_active_predictor_reflects_the_issued_predictor_after_a_forecast(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-active-predictor-base")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    forecast = client.post("/forecast/sensor-a/run")
    assert forecast.status_code == 200, forecast.text

    response = client.get("/models/sensor-a/active")

    assert response.status_code == 200
    body = response.json()
    assert body["origin"] == "base_configurado"
    assert body["model_id"]
    assert body["version"]
    assert body["trained_through"]
    assert body["applied_feedback_count"] == 0

    app.dependency_overrides.clear()


def test_active_predictor_reflects_the_recalibrated_predictor(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-active-predictor-recalibrated")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    forecast = client.post("/forecast/sensor-a/run")
    fecha = forecast.json()["verdicts"][0]["fecha"]
    client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "test"},
    )
    recalibration = client.post("/recalibrate/sensor-a")
    assert recalibration.status_code == 200, recalibration.text

    response = client.get("/models/sensor-a/active")

    assert response.status_code == 200
    body = response.json()
    assert body["origin"] == "recalibrado"
    assert body["version"] == recalibration.json()["version"]
    assert body["applied_feedback_count"] == 1
    assert len(body["applied_feedback_dates"]) == 1

    app.dependency_overrides.clear()


def test_active_predictor_rejects_invalid_sensor_id(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/models/sensor con espacios/active")

    assert response.status_code == 422

    app.dependency_overrides.clear()


def test_active_predictor_get_has_no_side_effects(tmp_path):
    """Consultar el predictor activo no dispara ninguna recalibración ni
    entrenamiento nuevo: repetir el GET no cambia el resultado."""
    _use_sqlite_tracking(tmp_path, "test-active-predictor-no-side-effects")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)
    client.post("/forecast/sensor-a/run")

    first = client.get("/models/sensor-a/active").json()
    second = client.get("/models/sensor-a/active").json()

    assert first == second

    app.dependency_overrides.clear()
