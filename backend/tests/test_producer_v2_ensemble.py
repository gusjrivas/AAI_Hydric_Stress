"""Real HTTP integration for the ensemble path, through the real route
(`POST /api/v2/sensors/{sensor_id}/forecasts`), with the real emit()/json={}
pattern already used by backend/tests/test_producer_v2_emission.py."""

from __future__ import annotations

import json as json_module

import numpy as np
import pandas as pd
import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.dependencies import get_producer_bundle_root
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.storage import save_dataset
from predictive_modeling.contract import feature_names as expand_feature_names
from tests.helpers.synthetic_bundles import (
    StubEstimator,
    write_ensemble_manifest,
    write_single_bundle,
)

FEATURE_COLUMNS = ["temperature", "relative_humidity"]
LAGS = [1]
ROLLING_WINDOWS = [3]
EXPANDED_NAMES = expand_feature_names(FEATURE_COLUMNS, LAGS, ROLLING_WINDOWS, include_current=True)


def _frame(days=10):
    dates = pd.date_range(end="2024-05-05", periods=days, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": dates,
            "temperature": np.linspace(15.0, 25.0, days),
            "relative_humidity": np.linspace(40.0, 60.0, days),
            "origen": "sintetico",
        }
    )


def _write_component(root, *, sensor_id, horizon, family, probability):
    model = StubEstimator(
        positive_probability=probability, feature_names_in_=np.array(EXPANDED_NAMES, dtype=object)
    )
    calibrator = StubEstimator(
        positive_probability=probability, feature_names_in_=np.array(EXPANDED_NAMES, dtype=object)
    )
    write_single_bundle(
        root / sensor_id / f"horizon_{horizon}" / "ensemble" / family,
        sensor_id=sensor_id,
        horizon=horizon,
        model=model,
        calibrator=calibrator,
        model_identity_label=f"{family}_model",
        calibrator_identity_label=f"{family}_calibrator",
        feature_columns=FEATURE_COLUMNS,
        feature_names=EXPANDED_NAMES,
        lags=LAGS,
        rolling_windows=ROLLING_WINDOWS,
    )


@pytest.fixture
def client(tmp_path):
    root = tmp_path / "bundles"
    sensor_id = "synthetic-sensor"
    for horizon in (1, 2, 3):
        for family, probability in [
            ("logistic_regression", 0.99),
            ("random_forest", 0.49),
            ("hist_gradient_boosting_classifier", 0.40),
        ]:
            _write_component(
                root, sensor_id=sensor_id, horizon=horizon, family=family, probability=probability
            )
        write_ensemble_manifest(
            root / sensor_id / f"horizon_{horizon}", sensor_id=sensor_id, horizon=horizon
        )
    save_dataset(f"sensor__{sensor_id}", _frame(), data_dir=tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: root
    try:
        with TestClient(app) as test_client:
            yield test_client, tmp_path, root
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client_with_malformed_manifest_at_horizon_2(tmp_path):
    """horizon_1 and horizon_3 are fully valid 3-family ensembles; horizon_2's
    `ensemble_manifest.json` has `policy_version=[]` (unhashable) and
    `families` containing an object instead of a string -- both would raise
    a bare `TypeError` from a `set()`/`in`-on-a-set operation on unvalidated
    input if `_validate_manifest` didn't type-check first."""
    root = tmp_path / "bundles"
    sensor_id = "synthetic-sensor"
    for horizon in (1, 3):
        for family, probability in [
            ("logistic_regression", 0.99),
            ("random_forest", 0.49),
            ("hist_gradient_boosting_classifier", 0.40),
        ]:
            _write_component(
                root, sensor_id=sensor_id, horizon=horizon, family=family, probability=probability
            )
        write_ensemble_manifest(
            root / sensor_id / f"horizon_{horizon}", sensor_id=sensor_id, horizon=horizon
        )
    horizon_2_dir = root / sensor_id / "horizon_2"
    horizon_2_dir.mkdir(parents=True, exist_ok=True)
    malformed_manifest = {
        "format_version": 1,
        "mode": "ensemble",
        "policy_version": [],  # unhashable: must not raise a bare TypeError
        "sensor_id": sensor_id,
        "horizon_days": 2,
        "contract_version": "producer_daily_h123_v1",
        "families": [
            "logistic_regression",
            {"not": "a string"},  # unhashable: must not raise a bare TypeError
            "hist_gradient_boosting_classifier",
        ],
        "weights": {
            "logistic_regression": 1 / 3,
            "random_forest": 1 / 3,
            "hist_gradient_boosting_classifier": 1 / 3,
        },
    }
    (horizon_2_dir / "ensemble_manifest.json").write_text(
        json_module.dumps(malformed_manifest), encoding="utf-8"
    )
    save_dataset(f"sensor__{sensor_id}", _frame(), data_dir=tmp_path)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: root
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_a_malformed_manifest_at_one_horizon_leaves_it_unavailable_without_blocking_the_others(
    client_with_malformed_manifest_at_horizon_2,
):
    http = client_with_malformed_manifest_at_horizon_2
    response = emit(http)
    assert response.status_code == 201, response.text
    body = response.json()
    slots = {slot["horizon_days"]: slot for slot in body["slots"]}

    assert slots[2]["status"] == "unavailable"
    assert "EnsembleManifestInvalidError" in slots[2]["reason_code"]
    assert "TypeError" not in slots[2]["reason_code"]

    for horizon in (1, 3):
        assert slots[horizon]["status"] == "available"
        assert slots[horizon]["ensemble"]["policy_version"] == "ensemble_agreement_v1"


def emit(client, key="request-1", sensor="synthetic-sensor", body=None):
    return client.post(
        f"/api/v2/sensors/{sensor}/forecasts",
        headers={"Idempotency-Key": key},
        json={} if body is None else body,
    )


def test_forecast_emission_exposes_ensemble_detail_via_the_real_route(client):
    http, _, _ = client
    response = emit(http)
    assert response.status_code == 201, response.text
    body = response.json()
    horizon_1 = next(slot for slot in body["slots"] if slot["horizon_days"] == 1)
    assert horizon_1["ensemble"]["policy_version"] == "ensemble_agreement_v1"
    assert horizon_1["score_kind"] == "ensemble_mean_of_calibrated_components"
    assert horizon_1["ensemble"]["positive_votes"] == 1
    assert horizon_1["ensemble"]["agreement_category"] == "sin_alerta_por_mayoria_con_discrepancia"
    # Minority vote (1/3) but the combined probability still crosses 0.5.
    assert horizon_1["alert"] == horizon_1["ensemble"]["combined_alert"] is True


def test_http_replay_returns_the_original_response_without_reevaluating(client):
    http, _, root = client
    first = emit(http)
    # Corrupt a component after the first emission: a replay must never
    # re-touch artifacts, so this must not surface any new failure.
    (
        root / "synthetic-sensor" / "horizon_1" / "ensemble" / "random_forest" / "model.joblib"
    ).write_bytes(b"corrupted after the fact")
    replay = emit(http)
    assert replay.status_code == 201
    assert replay.json() == first.json()


def test_confirming_an_ensemble_forecast_validates_combined_alert_not_the_vote(client):
    http, data_dir, _ = client
    response = emit(http)
    body = response.json()
    horizon_1 = next(slot for slot in body["slots"] if slot["horizon_days"] == 1)
    assert horizon_1["ensemble"]["agreement_category"] == "sin_alerta_por_mayoria_con_discrepancia"
    assert horizon_1["ensemble"]["positive_votes"] == 1  # minority
    assert horizon_1["alert"] is True  # but the combined decision is an alert

    review = http.post(
        f'/api/v2/sensors/synthetic-sensor/forecasts/{horizon_1["forecast_id"]}/reviews',
        json={"request_id": "review-1", "expected_revision": 0, "action": "confirm"},
    )
    assert review.status_code == 201

    # observed_label = forecast["alert"] when confirming -- must reflect the
    # combined decision (True), never the minority-vote category.
    import json

    document_paths = list((data_dir / "ui_metadata").glob("*synthetic-sensor*.json"))
    assert document_paths
    document = json.loads(document_paths[0].read_text())
    review_event = document["reviews"][horizon_1["forecast_id"]][0]
    assert review_event["observed_label"] is True
