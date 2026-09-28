"""HTTP-level check that the Melchor Romero demonstration executor's output
loads and infers through the real, unmodified producer v2 route -- the same
pattern already verified for Pergamino
(`test_pergamino_ensemble_demo_http.py`), now exercised with the real,
already-committed Melchor Romero dataset instead of a synthetic frame."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.dependencies import get_producer_bundle_root
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.storage import save_dataset
from experiment_runner.melchor_romero_historical_demo_runner import (
    DEMO_CALIBRATION,
    FIRST_ADMISSIBLE_DATE,
    RUN_MANIFEST_FILENAME,
    build_daily_frame_from_repo_dataset,
    run_demo_from_frame,
)

SENSOR_ID = "melchor-romero-demo-http"


@pytest.fixture(scope="module")
def bundle_root(tmp_path_factory):
    frame, dataset_sha256 = build_daily_frame_from_repo_dataset()
    root = tmp_path_factory.mktemp("melchor_romero_demo_bundles")
    run_demo_from_frame(frame, dataset_sha256, root, sensor_id=SENSOR_ID, horizons=(1, 2, 3))
    return root, frame


@pytest.fixture
def client(tmp_path, bundle_root):
    root, frame = bundle_root
    as_of = date.fromisoformat(FIRST_ADMISSIBLE_DATE)
    emission_frame = frame.loc[frame["timestamp"].dt.date <= as_of].copy()
    emission_frame["origen"] = "real"
    save_dataset(f"sensor__{SENSOR_ID}", emission_frame, data_dir=tmp_path)

    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: root
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_demo_bundle_exposes_ensemble_detail_via_the_real_route_for_all_three_horizons(client):
    response = client.post(
        f"/api/v2/sensors/{SENSOR_ID}/forecasts",
        headers={"Idempotency-Key": "melchor-romero-demo-1"},
        json={},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    as_of = date.fromisoformat(FIRST_ADMISSIBLE_DATE)
    for horizon in (1, 2, 3):
        slot = next(s for s in body["slots"] if s["horizon_days"] == horizon)
        assert slot["status"] == "available", slot.get("reason_code")
        assert slot["target_date"] == (as_of + timedelta(days=horizon)).isoformat()
        assert slot["ensemble"]["policy_version"] == "ensemble_agreement_v1"
        assert slot["score_kind"] == "ensemble_mean_of_calibrated_components"
        assert set(slot["ensemble"]["weights"]) == {
            "logistic_regression",
            "random_forest",
            "hist_gradient_boosting_classifier",
        }


def test_run_manifest_identifies_this_site_distinctly_from_pergamino(bundle_root):
    import json

    root, _ = bundle_root
    manifest = json.loads((root / RUN_MANIFEST_FILENAME).read_text())
    assert manifest["status"] == "completado"
    assert manifest["dataset_name"] == "melchor_romero_2024_consolidado"
    assert manifest["sensor_id"] == SENSOR_ID
    assert manifest["partitions"]["calibration"]["end"] == DEMO_CALIBRATION.end.isoformat()
