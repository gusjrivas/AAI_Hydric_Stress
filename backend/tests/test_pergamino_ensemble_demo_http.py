"""HTTP-level check that the separate Hito 2 demonstration executor's
output loads and infers through the real, unmodified producer v2 route --
synthetic data only, never the real Pergamino CSVs."""

from __future__ import annotations

import hashlib
from datetime import date

import numpy as np
import pandas as pd
import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.dependencies import get_producer_bundle_root
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.storage import save_dataset
from experiment_runner.pergamino_ensemble_demo_runner import (
    FIRST_ADMISSIBLE_DATE,
    INGESTION_END,
    INGESTION_START,
    run_demo_from_frame,
)

SENSOR_ID = "pergamino-ensemble-demo-http"


def _synthetic_daily_frame() -> pd.DataFrame:
    start = date.fromisoformat(INGESTION_START)
    end = date.fromisoformat(INGESTION_END)
    n_days = (end - start).days + 1
    dates = pd.date_range(start=start, periods=n_days, freq="D")
    day = np.arange(n_days)
    rng = np.random.default_rng(20260926)
    soil_moisture = 0.5 + 0.25 * np.sin(2 * np.pi * day / 365.25) + rng.normal(0, 0.03, n_days)
    rh2m = 60 + 15 * np.cos(2 * np.pi * day / 30) + rng.normal(0, 2.0, n_days)
    allsky = 20 + 8 * np.sin(2 * np.pi * day / 90 + 1.0) + rng.normal(0, 1.0, n_days)
    return pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": np.clip(soil_moisture, 0.05, 0.95),
            "relative_humidity": rh2m,
            "solar_radiation": allsky,
        }
    )


@pytest.fixture(scope="module")
def bundle_root(tmp_path_factory):
    frame = _synthetic_daily_frame()
    dataset_sha256 = hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()
    root = tmp_path_factory.mktemp("pergamino_demo_bundles")
    run_demo_from_frame(frame, dataset_sha256, root, sensor_id=SENSOR_ID, horizons=(1, 2, 3))
    return root, frame


@pytest.fixture
def client(tmp_path, bundle_root):
    root, frame = bundle_root
    # The producer route reads the sensor's own dataset snapshot to decide
    # `as_of_date` -- feed it the same synthetic frame, restricted through
    # the first admissible date so the emission lands exactly there.
    as_of = date.fromisoformat(FIRST_ADMISSIBLE_DATE)
    emission_frame = frame.loc[pd.to_datetime(frame["timestamp"]).dt.date <= as_of].copy()
    emission_frame["origen"] = "sintetico"
    save_dataset(f"sensor__{SENSOR_ID}", emission_frame, data_dir=tmp_path)

    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: root
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_demo_bundle_exposes_ensemble_detail_via_the_real_route(client):
    response = client.post(
        f"/api/v2/sensors/{SENSOR_ID}/forecasts",
        headers={"Idempotency-Key": "pergamino-demo-1"},
        json={},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    horizon_1 = next(slot for slot in body["slots"] if slot["horizon_days"] == 1)
    assert horizon_1["status"] == "available", horizon_1.get("reason_code")
    assert horizon_1["ensemble"]["policy_version"] == "ensemble_agreement_v1"
    assert horizon_1["score_kind"] == "ensemble_mean_of_calibrated_components"
    assert set(horizon_1["ensemble"]["weights"]) == {
        "logistic_regression",
        "random_forest",
        "hist_gradient_boosting_classifier",
    }
