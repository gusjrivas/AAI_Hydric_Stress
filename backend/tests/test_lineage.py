from pathlib import Path

import mlflow
from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir, get_feedback_data_dir
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.sensor_naming import dataset_name_for, registered_model_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset, save_dataset
from human_feedback.lineage import LineageValidationError


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_lineage_is_empty_for_a_sensor_never_recalibrated(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-lineage-empty")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/lineage/sensor-a")

    assert response.status_code == 200
    assert response.json() == {"sensor_id": "sensor-a", "chain": []}

    app.dependency_overrides.clear()


def test_lineage_reconstructs_the_full_chain_in_order(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-lineage-endpoint-chain")
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

    response = client.get("/lineage/sensor-a")

    assert response.status_code == 200
    body = response.json()
    assert len(body["chain"]) == 1
    entry = body["chain"][0]
    assert entry["recalibration_id"] == recalibration.json()["recalibration_id"]
    assert entry["source_model_id"] != entry["successor_model_id"]
    assert len(entry["feedback_references"]) == 1
    assert entry["feedback_references"][0]["fecha"].startswith(fecha)
    assert entry["lineage_version"] == 2
    assert entry["dataset_sha256"] is not None

    app.dependency_overrides.clear()


def test_lineage_rejects_invalid_sensor_id(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/lineage/sensor con espacios")

    assert response.status_code == 422

    app.dependency_overrides.clear()


def test_lineage_never_hides_a_validation_error(monkeypatch):
    """Un linaje corrupto o incompleto debe propagarse como error HTTP
    explícito (409) — nunca ocultarse ni devolver una cadena vacía o
    parcial."""
    import app.routers.lineage as lineage_router

    def _raise(_sensor_id):
        raise LineageValidationError("linaje corrupto simulado en el test")

    monkeypatch.setattr(lineage_router, "list_recalibration_lineage", _raise)
    client = TestClient(app)

    response = client.get("/lineage/sensor-a")

    assert response.status_code == 409
    assert "linaje corrupto simulado" in response.json()["detail"]


def test_lineage_get_has_no_side_effects(tmp_path):
    """Consultar el linaje no crea runs ni registra ninguna versión de
    modelo — solo lee lo que ya existe en el Model Registry."""
    _use_sqlite_tracking(tmp_path, "test-lineage-no-side-effects")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)
    client.post("/forecast/sensor-a/run")

    name = registered_model_name_for("sensor-a")
    versions_before = mlflow.MlflowClient().search_model_versions(f"name='{name}'")

    response = client.get("/lineage/sensor-a")
    assert response.status_code == 200
    assert response.json()["chain"] == []

    versions_after = mlflow.MlflowClient().search_model_versions(f"name='{name}'")
    assert len(versions_after) == len(versions_before) == 0

    app.dependency_overrides.clear()
