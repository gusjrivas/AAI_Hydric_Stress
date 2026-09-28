"""Historical *reproduction* of already-prepared Melchor Romero ensemble
forecasts -- the second real historical-demonstration site, generalizing
`test_pergamino_ensemble_historical_reproduction.py` to a genuinely
different dataset/site. Uses the REAL, already-committed Melchor Romero
dataset (unlike Pergamino's synthetic-data reproduction tests) through the
same unmodified `/sensors/{sensor_id}/historical/...` routes.

Reproduction (pure reads by an unambiguous emission date, clock simulated
per-request) is strictly separated from preparation (the one-time POST
emission, `_prepare_day`), exactly like the Pergamino test suite.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.dependencies import get_producer_bundle_root
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.storage import save_dataset
from experiment_runner.melchor_romero_historical_demo_runner import (
    build_daily_frame_from_repo_dataset,
    run_demo_from_frame,
)

SENSOR_ID = "melchor-romero-demo-reproduction"
REAL_ORIGEN = "real"
DAY_A = date(2024, 10, 20)
DAY_B = date(2024, 10, 21)
WINDOW_DAYS = [DAY_A + timedelta(days=i) for i in range(5)]  # 10-20..10-24


@pytest.fixture(scope="module")
def bundle_root(tmp_path_factory):
    frame, dataset_sha256 = build_daily_frame_from_repo_dataset()
    root = tmp_path_factory.mktemp("melchor_romero_reproduction_bundles")
    run_demo_from_frame(frame, dataset_sha256, root, sensor_id=SENSOR_ID, horizons=(1, 2, 3))
    return root, frame


@pytest.fixture
def client(tmp_path, bundle_root):
    root, _ = bundle_root
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: root
    try:
        with TestClient(app) as test_client:
            yield test_client, tmp_path
    finally:
        app.dependency_overrides.clear()


def _prepare_day(client, tmp_path, frame, day):
    """The one-time PREPARATION step: a real POST emission. Never called
    again for the same day in this file's reproduction tests."""
    emission_frame = frame.loc[pd.to_datetime(frame["timestamp"]).dt.date <= day].copy()
    emission_frame["origen"] = REAL_ORIGEN
    save_dataset(f"sensor__{SENSOR_ID}", emission_frame, data_dir=tmp_path)
    response = client.post(
        f"/api/v2/sensors/{SENSOR_ID}/forecasts",
        headers={"Idempotency-Key": f"prepare-{day.isoformat()}"},
        json={},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_reproduction_never_invokes_inference(client, bundle_root, monkeypatch):
    http, tmp_path = client
    _, frame = bundle_root

    for day in WINDOW_DAYS:
        _prepare_day(http, tmp_path, frame, day)

    def _forbidden(*args, **kwargs):
        raise AssertionError("inference must not be called during reproduction")

    monkeypatch.setattr("predictive_modeling.ensemble_bundle.predict_ensemble_bundle", _forbidden)
    monkeypatch.setattr(
        "predictive_modeling.operational_inference.predict_operational_bundle", _forbidden
    )

    for day in [WINDOW_DAYS[0], WINDOW_DAYS[1], WINDOW_DAYS[0], WINDOW_DAYS[-1]]:
        readings = http.get(
            f"/api/v2/sensors/{SENSOR_ID}/historical/{day.isoformat()}/readings",
            params={"days": 10},
        )
        assert readings.status_code == 200
        forecasts = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{day.isoformat()}/forecasts")
        assert forecasts.status_code == 200


def test_as_of_date_selection_is_unambiguous_across_a_to_b_to_a_navigation(client, bundle_root):
    http, tmp_path = client
    _, frame = bundle_root
    _prepare_day(http, tmp_path, frame, DAY_A)
    _prepare_day(http, tmp_path, frame, DAY_B)

    first_a = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts")
    b = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_B.isoformat()}/forecasts")
    second_a = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts")

    assert first_a.status_code == b.status_code == second_a.status_code == 200
    assert first_a.json() == second_a.json()
    assert first_a.json()["as_of_date"] == DAY_A.isoformat()
    assert b.json()["as_of_date"] == DAY_B.isoformat()

    a_targets = {slot["target_date"] for slot in first_a.json()["slots"]}
    b_targets = {slot["target_date"] for slot in b.json()["slots"]}
    assert a_targets != b_targets


def test_a_date_never_emitted_is_reported_as_not_prepared_not_as_empty_or_error(client):
    http, _ = client
    response = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{date(2024, 1, 1).isoformat()}/forecasts"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "batch_not_prepared"


def test_historical_review_is_gated_by_the_simulated_clock_not_real_now(client, bundle_root):
    http, tmp_path = client
    _, frame = bundle_root
    body = _prepare_day(http, tmp_path, frame, DAY_A)
    slot1 = next(s for s in body["slots"] if s["horizon_days"] == 1)
    assert slot1["target_date"] == (DAY_A + timedelta(days=1)).isoformat()
    forecast_id = slot1["forecast_id"]

    too_early = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts/{forecast_id}/reviews",
        json={"request_id": "hist-review-early", "expected_revision": 0, "action": "confirm"},
    )
    assert too_early.status_code == 409
    assert too_early.json()["error"]["code"] == "review_not_open"

    on_time = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_B.isoformat()}/forecasts/{forecast_id}/reviews",
        json={
            "request_id": "hist-review-on-time",
            "expected_revision": 0,
            "action": "confirm",
            "comment": "PRUEBA TECNICA -- no es feedback real de un productor ni de un experto.",
        },
    )
    assert on_time.status_code == 201
    assert on_time.json()["revision"] == 1


def test_reviewing_a_later_emissions_forecast_is_refused_from_an_earlier_historical_date(
    client, bundle_root
):
    http, tmp_path = client
    _, frame = bundle_root
    _prepare_day(http, tmp_path, frame, DAY_A)
    body_b = _prepare_day(http, tmp_path, frame, DAY_B)
    forecast_id_b = next(s for s in body_b["slots"] if s["horizon_days"] == 1)["forecast_id"]

    response = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts/{forecast_id_b}/reviews",
        json={"request_id": "hist-review-future", "expected_revision": 0, "action": "confirm"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_not_visible_at_this_historical_date"


def test_melchor_romero_and_pergamino_sensor_ids_never_cross_contaminate(client, bundle_root):
    """Two independent sites, same shared data_dir/bundle_root fixtures in
    this test process: preparing/reading Melchor Romero must never surface
    Pergamino's sensor_id (or vice versa) -- structural isolation by
    `sensor_id`-prefixed storage (ADR-0008), not by coincidence."""
    http, tmp_path = client
    _, frame = bundle_root
    _prepare_day(http, tmp_path, frame, DAY_A)

    other_site_response = http.get(
        f"/api/v2/sensors/pergamino-ensemble-demo/historical/{DAY_A.isoformat()}/forecasts"
    )
    assert other_site_response.status_code == 404
    assert other_site_response.json()["error"]["code"] == "batch_not_prepared"

    own_site_response = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts"
    )
    assert own_site_response.status_code == 200
