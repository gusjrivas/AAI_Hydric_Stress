import pandas as pd
from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir
from app.main import app
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import load_dataset, save_dataset
from fastapi.testclient import TestClient


def test_ingest_reading_creates_dataset_when_missing(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        "/sensors/sensor-a/readings",
        json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0, "procedencia": "sintetico"},
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 1

    app.dependency_overrides.clear()


def test_ingest_reading_appends_to_existing_dataset(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )
    response = client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-02T00:00:00", "temperature": 26.0}
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 2

    app.dependency_overrides.clear()


def test_ingest_reading_defaults_procedencia_to_real(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )

    df = load_dataset(dataset_name_for("sensor-a"), data_dir=tmp_path)
    assert df.loc[0, "origen"] == "real"

    app.dependency_overrides.clear()


def test_ingest_reading_same_day_different_time_replaces_row(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )
    response = client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T14:30:00", "temperature": 30.0}
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 1

    app.dependency_overrides.clear()


def test_ingest_reading_rejects_invalid_sensor_id(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        "/sensors/sensor.uno/readings",
        json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0},
    )

    assert response.status_code == 422

    app.dependency_overrides.clear()


def test_ingest_reading_isolates_datasets_between_sensors(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )
    client.post(
        "/sensors/sensor-b/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 40.0}
    )

    df_a = load_dataset(dataset_name_for("sensor-a"), data_dir=tmp_path)
    df_b = load_dataset(dataset_name_for("sensor-b"), data_dir=tmp_path)
    assert len(df_a) == 1
    assert len(df_b) == 1
    assert df_a.loc[0, "temperature"] == 25.0
    assert df_b.loc[0, "temperature"] == 40.0

    app.dependency_overrides.clear()


def test_ingest_reading_never_touches_the_historical_dataset(tmp_path):
    historical = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01"]), "temperature": [20.0]})
    save_dataset(HISTORICAL_DATASET_NAME, historical, data_dir=tmp_path)

    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0}
    )

    reloaded_historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=tmp_path)
    pd.testing.assert_frame_equal(reloaded_historical, historical)

    app.dependency_overrides.clear()
