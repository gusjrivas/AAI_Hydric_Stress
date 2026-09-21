"""Persisted, genuinely fitted synthetic models; no real data or holdouts."""

import json
import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from data_ingestion.history import VARIABLE_UNITS
from predictive_modeling.operational_inference import (
    BundleUnavailable,
    load_operational_bundle,
    predict_operational_bundle,
)
from predictive_modeling.operational_run import run_operational_manifest
from predictive_modeling.operational_run_artifacts import persist_operational_run
from tests.test_operational_run import (
    _dataset_sha256,
    _synthetic_frame,
    _synthetic_ready_manifest,
)


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    root = tmp_path_factory.mktemp("persisted-inference")
    frame = _synthetic_frame()
    fingerprint = _dataset_sha256(frame)
    manifest = _synthetic_ready_manifest(fingerprint)
    result = run_operational_manifest(manifest, frame, dataset_sha256=fingerprint)
    persist_operational_run(
        result,
        output_dir=root / "run",
        run_id="synthetic-inference-test",
        manifest_path=root / "fixture.json",
        manifest_identity_sha256="a" * 64,
        dataset_id="synthetic-fixture",
        repo_root=Path(__file__).resolve().parents[1],
    )
    return root / "run"


def predict(bundle, frame=None, **overrides):
    options = dict(sensor_id="synthetic-sensor", units=VARIABLE_UNITS, as_of_date=date(2024, 8, 20))
    options.update(overrides)
    return predict_operational_bundle(
        bundle, _synthetic_frame() if frame is None else frame, **options
    )


@pytest.mark.parametrize("horizon", [1, 2, 3])
def test_loaded_models_predict_exact_days_without_refitting(exported, horizon, monkeypatch):
    bundle = load_operational_bundle(
        exported / f"horizon_{horizon}", sensor_id="synthetic-sensor", horizon=horizon
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Inference must never fit")

    monkeypatch.setattr(bundle.model, "fit", forbidden)
    monkeypatch.setattr(bundle.calibrator, "fit", forbidden)
    output = predict(bundle)
    assert output["target_date"] == f"2024-08-{20 + horizon}"
    assert output["alert"] == (output["score"] >= 0.5)
    assert output["display_probability"] is None
    assert output["probability_status"] == "not_qualified"
    assert output["model_reference"]["horizon_days"] == horizon


def test_future_values_cannot_change_prior_frozen_inference(exported):
    bundle = load_operational_bundle(
        exported / "horizon_1", sensor_id="synthetic-sensor", horizon=1
    )
    frame = _synthetic_frame()
    original = predict(bundle, frame)
    frame.loc[frame.timestamp > "2024-08-20", "temperature"] = 999999
    frame.loc[frame.timestamp > "2024-08-20", "soil_moisture"] = np.nan
    assert predict(bundle, frame) == original


@pytest.mark.parametrize("change", ["gap", "missing", "no_as_of"])
def test_insufficient_latest_data_never_falls_back_to_an_earlier_day(exported, change):
    bundle = load_operational_bundle(
        exported / "horizon_1", sensor_id="synthetic-sensor", horizon=1
    )
    frame = _synthetic_frame()
    if change == "gap":
        frame = frame.loc[frame.timestamp != "2024-08-18"]
    elif change == "missing":
        frame.loc[frame.timestamp == "2024-08-20", "temperature"] = np.nan
    else:
        frame = frame.loc[frame.timestamp != "2024-08-20"]
    with pytest.raises(BundleUnavailable, match="insufficient_data"):
        predict(bundle, frame)


def test_temporal_sensor_and_unit_guards(exported):
    bundle = load_operational_bundle(
        exported / "horizon_1", sensor_id="synthetic-sensor", horizon=1
    )
    for override, reason in [
        ({"sensor_id": "another-sensor"}, "incompatible_model"),
        ({"units": {**VARIABLE_UNITS, "temperature": "kelvin"}}, "incompatible_units"),
        ({"as_of_date": date(2024, 5, 1)}, "model_not_available_at_date"),
    ]:
        with pytest.raises(BundleUnavailable, match=reason):
            predict(bundle, **override)


@pytest.mark.parametrize("file", ["model.joblib", "calibrator.joblib", "contract.json"])
def test_corrupt_artifact_rejected_before_deserialization(exported, tmp_path, file, monkeypatch):
    directory = tmp_path / "bundle"
    shutil.copytree(exported / "horizon_1", directory)
    with (directory / file).open("ab") as stream:
        stream.write(b"corruption")

    def forbidden(*args, **kwargs):
        pytest.fail("Corrupt bytes must not be deserialized")

    monkeypatch.setattr("predictive_modeling.operational_inference.joblib.load", forbidden)
    with pytest.raises(BundleUnavailable, match="artifact_identity_mismatch"):
        load_operational_bundle(directory, sensor_id="synthetic-sensor", horizon=1)


def test_loader_rejects_other_sensor_horizon_and_runtime(exported, tmp_path):
    directory = tmp_path / "bundle"
    shutil.copytree(exported / "horizon_1", directory)
    for sensor, horizon in [("other", 1), ("synthetic-sensor", 2)]:
        with pytest.raises(BundleUnavailable, match="incompatible_model"):
            load_operational_bundle(directory, sensor_id=sensor, horizon=horizon)
    path = directory / "bundle.json"
    metadata = json.loads(path.read_text())
    metadata["environment"]["python"] = "0.0.0"
    path.write_text(json.dumps(metadata))
    with pytest.raises(BundleUnavailable, match="incompatible_environment"):
        load_operational_bundle(directory, sensor_id="synthetic-sensor", horizon=1)
