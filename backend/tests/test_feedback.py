from pathlib import Path

import pandas as pd
from app.config import get_feedback_data_dir
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.registry import save_feedback_log
from human_feedback.schema import init_feedback_log


def _seed_feedback_log(sensor_id: str, data_dir: Path) -> str:
    dates = pd.to_datetime(["2024-10-19", "2024-10-20"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)
    log["target_timestamp"] = dates + pd.Timedelta(days=3)
    log["model_version"] = "test-model"
    log["validated_at"] = pd.NaT
    save_feedback_log(feedback_log_name_for(sensor_id), log, data_dir=data_dir)
    return "2024-10-19"


def test_list_feedback_returns_404_when_no_forecast_ran_yet(tmp_path: Path):
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/feedback/sensor-a")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_list_feedback_returns_persisted_rows(tmp_path: Path):
    _seed_feedback_log("sensor-a", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/feedback/sensor-a")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 2
    assert rows[0]["estado_validacion"] == "pendiente"
    app.dependency_overrides.clear()


def test_confirm_feedback_updates_state(tmp_path: Path):
    fecha = _seed_feedback_log("sensor-a", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(f"/feedback/sensor-a/{fecha}/confirm")

    assert response.status_code == 200
    assert response.json()["estado_validacion"] == "confirmada"

    persisted = client.get("/feedback/sensor-a").json()["rows"]
    updated_row = next(r for r in persisted if r["fecha"] == fecha)
    assert updated_row["estado_validacion"] == "confirmada"
    app.dependency_overrides.clear()


def test_reject_feedback_stores_correction_and_observation(tmp_path: Path):
    fecha = _seed_feedback_log("sensor-a", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        f"/feedback/sensor-a/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "no habia estres real"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["estado_validacion"] == "rechazada"
    assert body["etiqueta_corregida"] == 0
    assert body["observacion"] == "no habia estres real"
    app.dependency_overrides.clear()


def test_confirm_unknown_date_returns_404(tmp_path: Path):
    _seed_feedback_log("sensor-a", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/feedback/sensor-a/2099-01-01/confirm")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_feedback_logs_are_isolated_per_sensor(tmp_path: Path):
    fecha = _seed_feedback_log("sensor-a", tmp_path)
    _seed_feedback_log("sensor-b", tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post(f"/feedback/sensor-a/{fecha}/confirm")

    rows_a = client.get("/feedback/sensor-a").json()["rows"]
    rows_b = client.get("/feedback/sensor-b").json()["rows"]
    confirmed_a = next(r for r in rows_a if r["fecha"] == fecha)
    still_pending_b = next(r for r in rows_b if r["fecha"] == fecha)
    assert confirmed_a["estado_validacion"] == "confirmada"
    assert still_pending_b["estado_validacion"] == "pendiente"
    app.dependency_overrides.clear()
