import pandas as pd
from app.config import get_dataset_data_dir
from app.main import app
from data_ingestion.storage import load_dataset, save_dataset
from fastapi.testclient import TestClient


def test_ingest_reading_creates_dataset_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.sensors.DATASET_NAME", "test_dataset_en_vivo")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        "/sensors/readings",
        json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0, "procedencia": "sintetico"},
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 1

    app.dependency_overrides.clear()


def test_ingest_reading_appends_to_existing_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.sensors.DATASET_NAME", "test_dataset_en_vivo")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/sensors/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0})
    response = client.post(
        "/sensors/readings", json={"timestamp": "2026-01-02T00:00:00", "temperature": 26.0}
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 2

    app.dependency_overrides.clear()


def test_ingest_reading_defaults_procedencia_to_real(tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.sensors.DATASET_NAME", "test_dataset_en_vivo")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/sensors/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0})

    df = load_dataset("test_dataset_en_vivo", data_dir=tmp_path)
    assert df.loc[0, "origen"] == "real"

    app.dependency_overrides.clear()


def test_ingest_reading_same_day_different_time_replaces_row(tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.sensors.DATASET_NAME", "test_dataset_en_vivo")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/sensors/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0})
    response = client.post(
        "/sensors/readings", json={"timestamp": "2026-01-01T14:30:00", "temperature": 30.0}
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 1

    app.dependency_overrides.clear()


def test_ingest_reading_rejects_default_historical_dataset_without_explicit_env(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        "/sensors/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )

    assert response.status_code == 409

    app.dependency_overrides.clear()


def test_ingest_reading_does_not_touch_other_datasets(tmp_path, monkeypatch):
    historical = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01"]), "temperature": [20.0]})
    save_dataset("melchor_romero_2024_consolidado", historical, data_dir=tmp_path)

    monkeypatch.setattr("app.routers.sensors.DATASET_NAME", "otro_dataset_en_vivo")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/sensors/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0})

    reloaded_historical = load_dataset("melchor_romero_2024_consolidado", data_dir=tmp_path)
    pd.testing.assert_frame_equal(reloaded_historical, historical)

    app.dependency_overrides.clear()
