"""Real wiring test: producer_emission.py's per-horizon branch on
is_ensemble_configured, exercised end to end through the real
predict_operational_bundle (via predict_ensemble_bundle), not mocked."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from architecture_integration.producer_emission import emit_forecasts
from human_feedback.operational_repository import OperationalRepository
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
        }
    )


def _write_ensemble_component(root, *, sensor_id, horizon, family, probability):
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


def _write_single_model_bundle(root, *, sensor_id, horizon, probability):
    model = StubEstimator(
        positive_probability=probability, feature_names_in_=np.array(EXPANDED_NAMES, dtype=object)
    )
    calibrator = StubEstimator(
        positive_probability=probability, feature_names_in_=np.array(EXPANDED_NAMES, dtype=object)
    )
    write_single_bundle(
        root / sensor_id / f"horizon_{horizon}",
        sensor_id=sensor_id,
        horizon=horizon,
        model=model,
        calibrator=calibrator,
        model_identity_label="legacy_model",
        calibrator_identity_label="legacy_calibrator",
        feature_columns=FEATURE_COLUMNS,
        feature_names=EXPANDED_NAMES,
        lags=LAGS,
        rolling_windows=ROLLING_WINDOWS,
    )


def _emit_via_real_entrypoint(tmp_path, bundle_root, *, sensor_id="s1", key="k1"):
    repo = OperationalRepository(tmp_path, sensor_id)
    now = datetime(2024, 5, 5, 12, tzinfo=timezone.utc)
    frame = _frame()

    import architecture_integration.producer_emission as producer_emission_module

    original_load_snapshot = producer_emission_module.load_dataset_snapshot

    class _FakeSnapshot:
        dataframe = frame
        dataset_sha256 = "snap-" + sensor_id
        content = b""

    def _fake_load_dataset_snapshot(name, *, data_dir):
        return _FakeSnapshot()

    producer_emission_module.load_dataset_snapshot = _fake_load_dataset_snapshot
    try:
        status_code, body = emit_forecasts(
            repo, data_dir=tmp_path, bundle_root=bundle_root, idempotency_key=key, now=now
        )
    finally:
        producer_emission_module.load_dataset_snapshot = original_load_snapshot
    return status_code, body


def test_sensor_without_ensemble_signals_behaves_exactly_as_before(tmp_path):
    bundle_root = tmp_path / "bundles"
    for horizon in (1, 2, 3):
        _write_single_model_bundle(bundle_root, sensor_id="s1", horizon=horizon, probability=0.7)

    status_code, body = _emit_via_real_entrypoint(tmp_path, bundle_root)

    slot_1 = next(s for s in body["slots"] if s["horizon_days"] == 1)
    assert slot_1["status"] == "available"
    assert slot_1.get("ensemble") is None
    assert slot_1["score_kind"] == "calibrated_probability"


def test_ensemble_configured_and_complete_is_available_with_combined_view(tmp_path):
    bundle_root = tmp_path / "bundles"
    for horizon in (1, 2, 3):
        for family, probability in [
            ("logistic_regression", 0.51),
            ("random_forest", 0.51),
            ("hist_gradient_boosting_classifier", 0.01),
        ]:
            _write_ensemble_component(
                bundle_root, sensor_id="s1", horizon=horizon, family=family, probability=probability
            )
        write_ensemble_manifest(
            bundle_root / "s1" / f"horizon_{horizon}", sensor_id="s1", horizon=horizon
        )

    status_code, body = _emit_via_real_entrypoint(tmp_path, bundle_root)

    slot_1 = next(s for s in body["slots"] if s["horizon_days"] == 1)
    assert slot_1["status"] == "available"
    assert slot_1["ensemble"]["policy_version"] == "ensemble_agreement_v1"
    assert slot_1["ensemble"]["positive_votes"] == 2
    assert slot_1["ensemble"]["agreement_category"] == "posible_alerta_acuerdo_parcial"
    assert slot_1["alert"] == slot_1["ensemble"]["combined_alert"]
    assert slot_1["score_kind"] == "ensemble_mean_of_calibrated_components"


def test_one_horizon_ensemble_incomplete_does_not_block_the_others(tmp_path):
    bundle_root = tmp_path / "bundles"
    # Horizon 1: ensemble configured but missing random_forest.
    for family, probability in [
        ("logistic_regression", 0.6),
        ("hist_gradient_boosting_classifier", 0.4),
    ]:
        _write_ensemble_component(
            bundle_root, sensor_id="s1", horizon=1, family=family, probability=probability
        )
    write_ensemble_manifest(bundle_root / "s1" / "horizon_1", sensor_id="s1", horizon=1)
    # Horizon 2: normal single-model, no ensemble/ at all.
    _write_single_model_bundle(bundle_root, sensor_id="s1", horizon=2, probability=0.7)
    # Horizon 3: nothing at all -> model_not_available.

    status_code, body = _emit_via_real_entrypoint(tmp_path, bundle_root)

    slot_1 = next(s for s in body["slots"] if s["horizon_days"] == 1)
    slot_2 = next(s for s in body["slots"] if s["horizon_days"] == 2)
    assert slot_1["status"] == "unavailable"
    assert "random_forest" in slot_1["reason_code"]
    assert slot_2["status"] == "available"
    assert slot_2.get("ensemble") is None


def test_reemission_does_not_recompute_an_already_available_slot(tmp_path):
    bundle_root = tmp_path / "bundles"
    _write_single_model_bundle(bundle_root, sensor_id="s1", horizon=1, probability=0.7)
    _write_single_model_bundle(bundle_root, sensor_id="s1", horizon=2, probability=0.7)
    _write_single_model_bundle(bundle_root, sensor_id="s1", horizon=3, probability=0.7)

    _, first = _emit_via_real_entrypoint(tmp_path, bundle_root, key="first")
    first_slot_1 = next(s for s in first["slots"] if s["horizon_days"] == 1)
    assert first_slot_1["status"] == "available"

    # Now configure an ensemble for horizon 1 -- a *new* emission (different
    # idempotency key, but the SAME as_of_date) must not recompute the
    # already-available slot.
    for family, probability in [
        ("logistic_regression", 0.9),
        ("random_forest", 0.9),
        ("hist_gradient_boosting_classifier", 0.9),
    ]:
        _write_ensemble_component(
            bundle_root, sensor_id="s1", horizon=1, family=family, probability=probability
        )
    write_ensemble_manifest(bundle_root / "s1" / "horizon_1", sensor_id="s1", horizon=1)

    _, second = _emit_via_real_entrypoint(tmp_path, bundle_root, key="second")
    second_slot_1 = next(s for s in second["slots"] if s["horizon_days"] == 1)
    assert second_slot_1["forecast_id"] == first_slot_1["forecast_id"]
    assert second_slot_1.get("ensemble") is None  # untouched: still the original single-model slot
