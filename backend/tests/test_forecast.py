from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_feedback_data_dir
from app.main import app


def test_run_forecast_returns_verdicts(tmp_path: Path):
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/forecast/run")

    assert response.status_code == 200
    body = response.json()
    assert body["train_rows"] > 0
    assert body["test_rows"] > 0
    assert len(body["verdicts"]) == body["test_rows"]
    first = body["verdicts"][0]
    assert set(first.keys()) == {"fecha", "alerta", "probabilidad"}

    app.dependency_overrides.clear()


def test_run_forecast_returns_404_when_dataset_missing(tmp_path: Path, monkeypatch):
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    monkeypatch.setattr("app.routers.forecast.DATASET_NAME", "esto_no_existe")
    client = TestClient(app)

    response = client.post("/forecast/run")

    assert response.status_code == 404
    assert "esto_no_existe" in response.json()["detail"]

    app.dependency_overrides.clear()
