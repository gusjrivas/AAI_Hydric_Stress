from pathlib import Path

import mlflow
from fastapi.testclient import TestClient

from app.config import get_feedback_data_dir
from app.main import app


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def test_recalibrate_returns_400_without_pending_corrections(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-no-corrections")
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/forecast/run")
    response = client.post("/recalibrate")

    assert response.status_code == 400
    assert "correcciones" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_recalibrate_returns_404_when_no_forecast_ran_yet(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-no-feedback")
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/recalibrate")

    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_recalibrate_registers_a_new_model_version_after_a_rejection(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-recalibrate-registers-version")
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    forecast = client.post("/forecast/run").json()
    fecha = forecast["verdicts"][0]["fecha"]
    client.post(
        f"/feedback/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "test"},
    )

    response = client.post("/recalibrate")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1"
    assert body["n_correcciones"] == 1
    assert body["fechas_corregidas"] == [fecha]

    app.dependency_overrides.clear()
