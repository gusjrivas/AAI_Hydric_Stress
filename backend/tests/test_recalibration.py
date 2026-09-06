from pathlib import Path

import mlflow
import pandas as pd
from app.config import HISTORICAL_DATASET_NAME, get_dataset_data_dir, get_feedback_data_dir
from app.main import app
from app.pipeline import load_dataset_or_raise
from fastapi.testclient import TestClient

from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset, save_dataset
from human_feedback.model_registry import list_recalibration_lineage, load_recalibration_lineage


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_recalibrate_returns_400_without_pending_corrections(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-no-corrections")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/forecast/sensor-a/run")
    response = client.post("/recalibrate/sensor-a")

    assert response.status_code == 400
    assert "correcciones" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_recalibrate_returns_404_when_no_forecast_ran_yet(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-no-feedback")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/recalibrate/sensor-a")

    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_recalibrate_registers_a_new_model_version_after_a_rejection(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-registers-version")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    forecast = client.post("/forecast/sensor-a/run").json()
    fecha = forecast["verdicts"][0]["fecha"]
    client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "test"},
    )

    response = client.post("/recalibrate/sensor-a")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1"
    assert body["n_correcciones"] == 1
    assert body["fechas_corregidas"] == [fecha]

    app.dependency_overrides.clear()


def test_recalibrating_one_sensor_does_not_affect_another(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-isolated-per-sensor")
    _seed_sensor_dataset("sensor-a", tmp_path)
    _seed_sensor_dataset("sensor-b", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    forecast_a = client.post("/forecast/sensor-a/run").json()
    client.post("/forecast/sensor-b/run")
    fecha = forecast_a["verdicts"][0]["fecha"]
    client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "test"},
    )
    client.post("/recalibrate/sensor-a")

    response_b = client.post("/recalibrate/sensor-b")

    assert response_b.status_code == 400  # sensor-b nunca tuvo rechazos propios

    app.dependency_overrides.clear()


def test_recalibration_is_not_reapplied_and_old_test_is_not_reused(tmp_path):
    from app.pipeline import execute_configured_pipeline, load_dataset_or_raise

    _use_sqlite_tracking(tmp_path, "test-recalibration-boundary")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)
    forecast = client.post("/forecast/sensor-a/run")
    assert forecast.status_code == 200, forecast.text
    fecha = forecast.json()["verdicts"][0]["fecha"]
    rejected = client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 1, "observacion": "corrección verificada"},
    )
    assert rejected.status_code == 200, rejected.text
    response = client.post("/recalibrate/sensor-a")
    assert response.status_code == 200, response.text
    repeat = client.post("/recalibrate/sensor-a")
    assert repeat.status_code == 400
    df, fingerprint = load_dataset_or_raise("sensor-a", tmp_path)
    result = execute_configured_pipeline(df, "sensor-a", fingerprint, tmp_path)
    assert result["test"].empty
    assert result["forecast"].timestamp.iloc[0] == df.timestamp.max()
    # A rerun returns the originally issued forecast, not a fitted response to its correction.
    assert client.post("/forecast/sensor-a/run").json()["verdicts"] == forecast.json()["verdicts"]
    app.dependency_overrides.clear()


def test_recalibration_lineage_reconstructs_full_a_to_b_to_c_chain(tmp_path):
    """Regresión de trazabilidad (complementa H-01/PR #182): dos ciclos
    HITL sucesivos, con un forecast real y nuevo emitido por B (no una
    reutilización artificial del forecast de A), deben quedar
    reconstruibles desde el linaje persistido en MLflow.
    """
    _use_sqlite_tracking(tmp_path, "test-recalibrate-lineage")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    # Ciclo 1: forecast con A, feedback rechazado + corregido, recalibración -> B.
    forecast_a = client.post("/forecast/sensor-a/run")
    assert forecast_a.status_code == 200, forecast_a.text
    fecha_a = forecast_a.json()["verdicts"][0]["fecha"]
    rejected_a = client.post(
        f"/feedback/sensor-a/{fecha_a}/reject",
        json={"etiqueta_corregida": 0, "observacion": "corrección ciclo 1"},
    )
    assert rejected_a.status_code == 200, rejected_a.text
    response_1 = client.post("/recalibrate/sensor-a")
    assert response_1.status_code == 200, response_1.text
    body_1 = response_1.json()
    assert body_1["recalibration_id"]

    # Avanza el dataset una fecha real (ADR-0007) para que el ciclo 2 emita
    # un pronóstico genuinamente nuevo con B; no se reutiliza el forecast de A.
    df, _ = load_dataset_or_raise("sensor-a", tmp_path)
    next_day = df.timestamp.max() + pd.Timedelta(days=1)
    reading = client.post(
        "/sensors/sensor-a/readings",
        json={
            "timestamp": next_day.isoformat(),
            "soil_moisture": 0.3,
            "solar_radiation": 18.0,
            "relative_humidity": 55.0,
        },
    )
    assert reading.status_code == 200, reading.text

    # Ciclo 2: nuevo forecast real con B, feedback rechazado + corregido, recalibración -> C.
    forecast_b = client.post("/forecast/sensor-a/run")
    assert forecast_b.status_code == 200, forecast_b.text
    fecha_b = forecast_b.json()["verdicts"][0]["fecha"]
    assert fecha_b != fecha_a
    rejected_b = client.post(
        f"/feedback/sensor-a/{fecha_b}/reject",
        json={"etiqueta_corregida": 1, "observacion": "corrección ciclo 2"},
    )
    assert rejected_b.status_code == 200, rejected_b.text
    response_2 = client.post("/recalibrate/sensor-a")
    assert response_2.status_code == 200, response_2.text
    body_2 = response_2.json()
    assert body_2["recalibration_id"]
    assert body_2["recalibration_id"] != body_1["recalibration_id"]

    chain = list_recalibration_lineage("sensor-a")

    assert len(chain) == 2
    first, second = chain
    assert first.recalibration_id == body_1["recalibration_id"]
    assert second.recalibration_id == body_2["recalibration_id"]
    assert first.source_model_id != first.successor_model_id
    assert second.source_model_id == first.successor_model_id
    assert second.successor_model_id not in {first.source_model_id, first.successor_model_id}

    # feedback A -> A -> B
    assert len(first.feedback_references) == 1
    assert first.feedback_references[0].fecha.startswith(fecha_a)
    assert first.feedback_references[0].model_version == first.source_model_id

    # feedback B -> B -> C
    assert len(second.feedback_references) == 1
    assert second.feedback_references[0].fecha.startswith(fecha_b)
    assert second.feedback_references[0].model_version == second.source_model_id

    resolved_second = load_recalibration_lineage("sensor-a", second.successor_model_id)
    assert resolved_second == second

    app.dependency_overrides.clear()


def test_no_lineage_event_recorded_on_failed_or_noop_recalibration(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-lineage-failure")
    _seed_sensor_dataset("sensor-a", tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/forecast/sensor-a/run")
    failed = client.post("/recalibrate/sensor-a")
    assert failed.status_code == 400
    assert list_recalibration_lineage("sensor-a") == []

    forecast = client.post("/forecast/sensor-a/run").json()
    fecha = forecast["verdicts"][0]["fecha"]
    client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "test"},
    )
    ok = client.post("/recalibrate/sensor-a")
    assert ok.status_code == 200
    assert len(list_recalibration_lineage("sensor-a")) == 1

    # Repetir sin correcciones nuevas falla y no agrega un segundo evento.
    repeat = client.post("/recalibrate/sensor-a")
    assert repeat.status_code == 400
    assert len(list_recalibration_lineage("sensor-a")) == 1

    app.dependency_overrides.clear()
