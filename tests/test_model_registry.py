from dataclasses import replace

import mlflow
import pandas as pd
import pytest
from mlflow.exceptions import MlflowException
from sklearn.linear_model import LogisticRegression

from human_feedback.model_registry import (
    ModelContractMismatch,
    load_latest_recalibrated_model,
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


def test_loading_requires_expected_contract():
    with pytest.raises(TypeError):
        load_latest_recalibrated_model("a")


def test_load_propagates_unavailable_mlflow(monkeypatch):
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    mlflow.set_tracking_uri("http://localhost:59999")
    bundle, _ = _bundle()
    with pytest.raises(MlflowException):
        load_latest_recalibrated_model("a", bundle.contract)
