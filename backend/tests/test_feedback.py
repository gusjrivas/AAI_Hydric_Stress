from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app.config import FEEDBACK_LOG_NAME, get_feedback_data_dir
from app.main import app
from human_feedback.registry import save_feedback_log
from human_feedback.schema import init_feedback_log


def _seed_feedback_log(data_dir: Path) -> str:
    dates = pd.to_datetime(["2024-10-19", "2024-10-20"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)
    save_feedback_log(FEEDBACK_LOG_NAME, log, data_dir=data_dir)
    return "2024-10-19"


def test_list_feedback_returns_404_when_no_forecast_ran_yet(tmp_path: Path):
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/feedback")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_list_feedback_returns_persisted_rows(tmp_path: Path):
    _seed_feedback_log(tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/feedback")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 2
    assert rows[0]["estado_validacion"] == "pendiente"
    app.dependency_overrides.clear()


def test_confirm_feedback_updates_state(tmp_path: Path):
    fecha = _seed_feedback_log(tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(f"/feedback/{fecha}/confirm")

    assert response.status_code == 200
    assert response.json()["estado_validacion"] == "confirmada"

    persisted = client.get("/feedback").json()["rows"]
    updated_row = next(r for r in persisted if r["fecha"] == fecha)
    assert updated_row["estado_validacion"] == "confirmada"
    app.dependency_overrides.clear()


def test_reject_feedback_stores_correction_and_observation(tmp_path: Path):
    fecha = _seed_feedback_log(tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        f"/feedback/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "no habia estres real"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["estado_validacion"] == "rechazada"
    assert body["etiqueta_corregida"] == 0
    assert body["observacion"] == "no habia estres real"
    app.dependency_overrides.clear()


def test_confirm_unknown_date_returns_404(tmp_path: Path):
    _seed_feedback_log(tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/feedback/2099-01-01/confirm")

    assert response.status_code == 404
    app.dependency_overrides.clear()
