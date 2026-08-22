import mlflow
import pandas as pd
import pytest
from mlflow.exceptions import MlflowException
from sklearn.linear_model import LogisticRegression

from human_feedback.model_registry import (
    load_latest_recalibrated_model,
    register_recalibrated_model,
)


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def test_register_and_load_latest_recalibrated_model(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-register-and-load")
    X = pd.DataFrame({"feature": [0, 1, 2, 3]})
    y = pd.Series([0, 0, 1, 1])
    model = LogisticRegression().fit(X, y)

    version = register_recalibrated_model(
        model, params={"n_correcciones": 1}, metrics={"n_filas_entrenamiento": 4}
    )

    assert version == "1"
    loaded = load_latest_recalibrated_model()
    assert hasattr(loaded, "predict")
    assert list(loaded.predict(X)) == list(model.predict(X))


def test_load_latest_recalibrated_model_returns_none_when_nothing_registered(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-nothing-registered")

    assert load_latest_recalibrated_model() is None


def test_register_recalibrated_model_twice_returns_incrementing_versions(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-incrementing-versions")
    X = pd.DataFrame({"feature": [0, 1, 2, 3]})
    y = pd.Series([0, 0, 1, 1])
    model = LogisticRegression().fit(X, y)

    v1 = register_recalibrated_model(model, params={}, metrics={})
    v2 = register_recalibrated_model(model, params={}, metrics={})

    assert v1 == "1"
    assert v2 == "2"
    loaded = load_latest_recalibrated_model()
    assert hasattr(loaded, "predict")


def test_load_latest_recalibrated_model_raises_when_mlflow_is_unreachable(monkeypatch):
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    mlflow.set_tracking_uri("http://localhost:59999")

    with pytest.raises(MlflowException):
        load_latest_recalibrated_model()
