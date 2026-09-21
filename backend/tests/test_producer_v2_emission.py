"""Real v2 HTTP emission from persisted, fitted synthetic models."""

import base64
import hashlib
import json
import shutil

import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.dependencies import get_producer_bundle_root
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.storage import save_dataset
from tests.test_operational_inference import exported as exported
from tests.test_operational_run import _synthetic_frame


@pytest.fixture
def client(tmp_path, exported):
    root = tmp_path / "bundles"
    shutil.copytree(exported, root / "synthetic-sensor")
    frame = _synthetic_frame()
    frame["origen"] = "sintetico"
    save_dataset("sensor__synthetic-sensor", frame, data_dir=tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: root
    try:
        with TestClient(app) as test_client:
            yield test_client, tmp_path, root
    finally:
        app.dependency_overrides.clear()


def emit(client, key="request-1", sensor="synthetic-sensor", body=None):
    return client.post(
        f"/api/v2/sensors/{sensor}/forecasts",
        headers={"Idempotency-Key": key},
        json={} if body is None else body,
    )


def test_emission_three_real_model_outputs_and_human_feedback(client):
    http, directory, _ = client
    response = emit(http)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["provenance"] == "synthetic"
    assert body["as_of_date"] == "2024-08-27"
    assert [slot["target_date"] for slot in body["slots"]] == [
        "2024-08-28",
        "2024-08-29",
        "2024-08-30",
    ]
    assert all(slot["status"] == "available" for slot in body["slots"])
    assert all(slot["display_probability"] is None for slot in body["slots"])
    forecast = body["slots"][0]
    review = http.post(
        f'/api/v2/sensors/synthetic-sensor/forecasts/{forecast["forecast_id"]}/reviews',
        json={"request_id": "review-1", "expected_revision": 0, "action": "confirm"},
    )
    assert review.status_code == 201
    assert (
        http.get(f'/api/v2/sensors/synthetic-sensor/forecasts/{forecast["forecast_id"]}').json()[
            "review"
        ]["status"]
        == "confirmed"
    )
    # HTTP replay is byte-equivalent JSON even after a human review.
    replay = emit(http)
    assert replay.status_code == 201
    assert replay.json() == body
    new_request = emit(http, key="request-2")
    assert new_request.status_code == 200
    assert new_request.json()["revision"] == body["revision"]
    assert new_request.json()["slots"][0]["review"]["status"] == "confirmed"
    files = list((directory / "ui_metadata").glob("*synthetic-sensor*.json"))
    assert files
    document = json.loads(files[0].read_text())
    stored = document["batches"][body["batch_id"]]["input_snapshot"]
    assert (
        hashlib.sha256(base64.b64decode(stored["parquet_base64"])).hexdigest()
        == body["snapshot_id"]
    )


def test_retry_precedes_snapshot_capture_and_changed_snapshot_conflicts(client):
    http, directory, _ = client
    response = emit(http)
    frame = _synthetic_frame()
    frame.loc[frame.index[-1], "temperature"] = 99
    save_dataset("sensor__synthetic-sensor", frame, data_dir=directory)
    assert emit(http).json() == response.json()
    conflict = emit(http, key="different")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "issued_snapshot_conflict"


def test_partial_failure_can_complete_without_replacing_success(client, tmp_path):
    http, _, root = client
    missing = root / "synthetic-sensor" / "horizon_2"
    saved = tmp_path / "held"
    shutil.move(str(missing), str(saved))
    first = emit(http).json()
    assert [slot["status"] for slot in first["slots"]] == ["available", "unavailable", "available"]
    shutil.move(str(saved), str(missing))
    second = emit(http, key="complete")
    assert second.status_code == 200
    assert second.json()["revision"] == 2
    assert all(slot["status"] == "available" for slot in second.json()["slots"])
    assert second.json()["slots"][0] == first["slots"][0]


def test_unknown_empty_demo_and_invalid_body(client):
    http, _, _ = client
    assert emit(http, sensor="unknown").status_code == 404
    assert emit(http, body={"score": 0.9}).status_code == 422
    assert http.post("/api/v2/sensors/synthetic-sensor/forecasts", json={}).status_code == 422
    for sensor in ["empty-sensor", "demo-test"]:
        assert (
            http.post(
                "/api/v2/sensors",
                json={"sensor_id": sensor, "display_name": sensor, "source_kind": "synthetic"},
            ).status_code
            == 201
        )
    empty = emit(http, sensor="empty-sensor")
    assert empty.status_code == 200
    assert empty.json()["batch_id"] is None
    assert all(slot["reason_code"] == "no_readings" for slot in empty.json()["slots"])
    assert emit(http, sensor="demo-test").json()["error"]["code"] == "demo_write_locked"


def test_persistence_failure_leaves_no_half_committed_emission(client, monkeypatch):
    from human_feedback.operational_repository import (
        OperationalRepository,
        OperationalRepositoryError,
    )

    http, _, _ = client
    with monkeypatch.context() as patch:

        def fail(*args):
            raise OperationalRepositoryError("operational_storage_unavailable", "forced", 503)

        patch.setattr(OperationalRepository, "_write", fail)
        assert emit(http).status_code == 503
    assert http.get("/api/v2/sensors/synthetic-sensor/forecasts").json()["items"] == []
    assert emit(http).status_code == 201


def test_busy_sensor_returns_retryable_conflict(client):
    from data_ingestion.storage import interprocess_lock
    from human_feedback.operational_repository import OperationalRepository

    http, directory, _ = client
    repo = OperationalRepository(directory, "synthetic-sensor")
    with interprocess_lock(repo.lock_path):
        response = emit(http)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "operation_in_progress"
    assert emit(http).status_code == 201


def test_missing_operational_dependencies_do_not_break_legacy_or_invent_scores(client, monkeypatch):
    import sys

    http, _, _ = client
    monkeypatch.setitem(sys.modules, "predictive_modeling.operational_inference", None)
    response = emit(http)
    assert response.status_code == 201
    assert all(
        slot["reason_code"] == "incompatible_environment" for slot in response.json()["slots"]
    )
    assert all(slot["alert"] is None for slot in response.json()["slots"])
