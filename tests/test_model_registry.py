from dataclasses import replace

import mlflow
import pandas as pd
import pytest
from mlflow.exceptions import MlflowException
from sklearn.linear_model import LogisticRegression

from human_feedback.lineage import FeedbackReference, RecalibrationLineage
from human_feedback.model_registry import (
    ModelContractMismatch,
    list_recalibration_lineage,
    load_latest_recalibrated_model,
    load_recalibration_lineage,
    register_recalibrated_model,
)
from predictive_modeling.contract import FittedPredictor, make_contract


def _tracking(tmp_path):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment("contracts")


def _bundle():
    contract = make_contract(["soil_moisture"], lags=[1], rolling_windows=[])
    X = pd.DataFrame({"soil_moisture_lag1": [0.1, 0.2, 0.3, 0.4]})
    model = LogisticRegression().fit(X, [1, 1, 0, 0])
    return FittedPredictor(model, contract, 0.25, "2024-01-10"), X


def test_register_load_roundtrip_and_sensor_isolation(tmp_path):
    _tracking(tmp_path)
    bundle, X = _bundle()
    assert load_latest_recalibrated_model("a", bundle.contract) is None
    assert register_recalibrated_model("a", bundle, {}, {}) == "1"
    loaded = load_latest_recalibrated_model("a", bundle.contract)
    assert loaded.contract == bundle.contract
    assert loaded.threshold == bundle.threshold
    assert loaded.model_id == bundle.model_id
    assert list(loaded.model.predict(X)) == list(bundle.model.predict(X))
    assert load_latest_recalibrated_model("b", bundle.contract) is None
    assert register_recalibrated_model("a", bundle, {}, {}) == "2"


@pytest.mark.parametrize(
    "change",
    [
        {"lags": [2]},
        {"rolling_windows": [3]},
        {"horizon_days": 7},
        {"include_current": True},
        {"include_anomaly_detection": True},
    ],
)
def test_incompatible_contract_rejected_before_download(tmp_path, monkeypatch, change):
    _tracking(tmp_path)
    bundle, _ = _bundle()
    register_recalibrated_model("a", bundle, {}, {})
    expected = make_contract(["soil_moisture"], **({"lags": [1], "rolling_windows": []} | change))

    def fail(*args, **kwargs):
        raise AssertionError("No debe descargar el modelo incompatible")

    monkeypatch.setattr(mlflow.sklearn, "load_model", fail)
    with pytest.raises(ModelContractMismatch):
        load_latest_recalibrated_model("a", expected)


def test_registration_rejects_metadata_that_disagrees_with_estimator(tmp_path):
    _tracking(tmp_path)
    bundle, _ = _bundle()
    bad = replace(bundle, contract={**bundle.contract, "model_features": ["wrong"]})
    with pytest.raises(ModelContractMismatch):
        register_recalibrated_model("a", bad, {}, {})


def _lineage(sensor_id, source_model_id, successor_model_id, recalibration_id="r1"):
    return RecalibrationLineage(
        recalibration_id=recalibration_id,
        sensor_id=sensor_id,
        source_model_id=source_model_id,
        successor_model_id=successor_model_id,
        feedback_references=[
            FeedbackReference(
                sensor_id=sensor_id,
                fecha="2024-01-01 00:00:00",
                model_version=source_model_id,
                target_timestamp="2024-01-04 00:00:00",
            )
        ],
        recalibrated_at="2026-09-06 00:00:00",
        source_trained_through="2024-01-04",
        successor_trained_through="2024-01-05",
        dataset_fingerprint="abc123",
        contract_version=1,
        pipeline_version="controlled_daily_v3",
    )


def test_register_persists_lineage_as_artifact_of_the_same_run(tmp_path):
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage = _lineage("a", "model-a", bundle.model_id)

    version = register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    resolved = load_recalibration_lineage("a", bundle.model_id)
    assert resolved is not None
    assert resolved.recalibration_id == lineage.recalibration_id
    assert resolved.source_model_id == "model-a"
    assert resolved.successor_model_id == bundle.model_id
    assert resolved.mlflow_model_version == version
    assert resolved.feedback_references == lineage.feedback_references


def test_list_recalibration_lineage_reconstructs_chronological_chain(tmp_path):
    _tracking(tmp_path)
    bundle, _ = _bundle()
    successor = replace(bundle, model_id="model-c")

    lineage_a_b = _lineage("a", "model-a", bundle.model_id)
    lineage_b_c = _lineage("a", bundle.model_id, "model-c", recalibration_id="r2")
    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage_a_b)
    register_recalibrated_model("a", successor, {}, {}, lineage=lineage_b_c)

    chain = list_recalibration_lineage("a")

    assert [event.recalibration_id for event in chain] == ["r1", "r2"]
    assert chain[0].source_model_id == "model-a"
    assert chain[0].successor_model_id == bundle.model_id
    assert chain[1].source_model_id == bundle.model_id
    assert chain[1].successor_model_id == "model-c"


def test_register_without_lineage_does_not_create_a_lineage_event(tmp_path):
    _tracking(tmp_path)
    bundle, _ = _bundle()

    register_recalibrated_model("a", bundle, {}, {})

    assert load_recalibration_lineage("a", bundle.model_id) is None
    assert list_recalibration_lineage("a") == []


def test_loading_requires_expected_contract():
    with pytest.raises(TypeError):
        load_latest_recalibrated_model("a")


def test_load_propagates_unavailable_mlflow(monkeypatch):
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    mlflow.set_tracking_uri("http://localhost:59999")
    bundle, _ = _bundle()
    with pytest.raises(MlflowException):
        load_latest_recalibrated_model("a", bundle.contract)
