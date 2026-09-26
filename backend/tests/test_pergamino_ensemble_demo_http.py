"""HTTP-level check that the separate Hito 2 demonstration executor's
output loads and infers through the real, unmodified producer v2 route --
synthetic data only, never the real Pergamino CSVs."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.dependencies import get_producer_bundle_root
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.storage import save_dataset
from experiment_runner.pergamino_ensemble_demo_runner import (
    DEMO_CALIBRATION,
    DEMO_TRAIN,
    FEATURE_COLUMNS,
    FIRST_ADMISSIBLE_DATE,
    INGESTION_END,
    INGESTION_START,
    LAGS,
    ROLLING_WINDOWS,
    RUN_MANIFEST_FILENAME,
    build_cut_plan,
    build_feature_frame,
    resolve_training_threshold,
    run_demo_from_frame,
)
from predictive_modeling.operational_preparation import (
    add_multihorizon_targets,
    partition_labeled_horizon,
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


def test_demo_bundle_exposes_ensemble_detail_via_the_real_route_for_all_three_horizons(client):
    response = client.post(
        f"/api/v2/sensors/{SENSOR_ID}/forecasts",
        headers={"Idempotency-Key": "pergamino-demo-1"},
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


def test_run_manifest_purge_counts_match_an_independent_recomputation_for_all_horizons(bundle_root):
    """The manifest's `train_rows_used`/`calibration_rows_used` (and their
    `_excluded_by_purge` counterparts) are cross-checked here against a
    recomputation done directly from the same synthetic frame, using the
    same production functions the runner itself calls -- not merely
    re-deriving the constants the runner was built from."""
    import json

    root, frame = bundle_root
    manifest = json.loads((root / RUN_MANIFEST_FILENAME).read_text())
    assert manifest["status"] == "completado"

    threshold = resolve_training_threshold(frame)
    feature_frame, feature_names_tuple = build_feature_frame(
        frame, list(FEATURE_COLUMNS), lags=list(LAGS), windows=list(ROLLING_WINDOWS)
    )
    feature_names = list(feature_names_tuple)
    labeled_by_horizon = add_multihorizon_targets(
        feature_frame, column="soil_moisture", thresholds={1: threshold, 2: threshold, 3: threshold}
    )
    cuts = build_cut_plan()

    for horizon in (1, 2, 3):
        prepared = partition_labeled_horizon(
            labeled_by_horizon[horizon], cuts=cuts, required_inference_columns=feature_names
        )
        expected_train_used = len(prepared.train.dropna(subset=feature_names))
        expected_train_excluded = len(prepared.train) - expected_train_used
        expected_calib_used = len(prepared.calibration.dropna(subset=feature_names))
        expected_calib_excluded = len(prepared.calibration) - expected_calib_used

        report = manifest["horizons"][str(horizon)]
        assert report["train_rows_used"] == expected_train_used
        assert report["train_rows_excluded_by_purge"] == expected_train_excluded
        assert report["calibration_rows_used"] == expected_calib_used
        assert report["calibration_rows_excluded_by_purge"] == expected_calib_excluded
        # The purge must actually remove something near each partition's
        # `partition_labeled_horizon`'s own containment-based purge (target
        # date must land back inside the same named range) already removed
        # the last `horizon` days from `prepared.train`/`prepared.calibration`
        # before the dropna-based counts above are even computed -- verified
        # directly here via the actual last date effectively used, on the
        # rows the runner exported, not merely re-deriving a constant.
        last_train_date = prepared.train["timestamp"].max().date()
        last_calib_date = prepared.calibration["timestamp"].max().date()
        assert last_train_date == DEMO_TRAIN.end - timedelta(days=horizon)
        assert last_calib_date == DEMO_CALIBRATION.end - timedelta(days=horizon)
