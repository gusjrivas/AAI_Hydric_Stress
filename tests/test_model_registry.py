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


def _use_sqlite_tracking(tmp_path, experiment_name):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment(experiment_name)


def _register(sensor_id="sensor-a", feature_columns=None, horizon_days=3, threshold=0.32):
    X = pd.DataFrame({"feature": [0, 1, 2, 3]})
    y = pd.Series([0, 0, 1, 1])
    model = LogisticRegression().fit(X, y)
    version = register_recalibrated_model(
        sensor_id,
        model,
        params={"n_correcciones": 1},
        metrics={"n_filas_entrenamiento": 4},
        feature_columns=feature_columns or ["soil_moisture", "solar_radiation"],
        horizon_days=horizon_days,
        threshold=threshold,
        pipeline_version="purged_cv_v2",
    )
    return model, X, version


def test_register_and_load_latest_recalibrated_model(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-register-and-load")
    model, X, version = _register()

    assert version == "1"
    loaded = load_latest_recalibrated_model("sensor-a")
    assert hasattr(loaded, "predict")
    assert list(loaded.predict(X)) == list(model.predict(X))


def test_load_latest_recalibrated_model_returns_none_when_nothing_registered(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-nothing-registered")

    assert load_latest_recalibrated_model("sensor-a") is None


def test_register_recalibrated_model_twice_returns_incrementing_versions(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-incrementing-versions")

    _, _, v1 = _register()
    _, _, v2 = _register()

    assert v1 == "1"
    assert v2 == "2"
    loaded = load_latest_recalibrated_model("sensor-a")
    assert hasattr(loaded, "predict")


def test_recalibrated_models_are_isolated_per_sensor(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-isolated-per-sensor")

    _register(sensor_id="sensor-a")

    assert load_latest_recalibrated_model("sensor-a") is not None
    assert load_latest_recalibrated_model("sensor-b") is None


def test_load_latest_recalibrated_model_raises_when_mlflow_is_unreachable(monkeypatch):
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    mlflow.set_tracking_uri("http://localhost:59999")

    with pytest.raises(MlflowException):
        load_latest_recalibrated_model("sensor-a")


def test_load_latest_recalibrated_model_without_expected_columns_skips_validation(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-no-validation-requested")
    _register(feature_columns=["soil_moisture", "solar_radiation"])

    # sin expected_feature_columns, se carga tal cual (comportamiento
    # preexistente, para no romper llamadores que todavía no lo declaran).
    loaded = load_latest_recalibrated_model("sensor-a")
    assert hasattr(loaded, "predict")


def test_load_latest_recalibrated_model_accepts_matching_expected_columns(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-matching-columns")
    _register(feature_columns=["soil_moisture", "solar_radiation"], horizon_days=3)

    loaded = load_latest_recalibrated_model(
        "sensor-a", expected_feature_columns=["soil_moisture", "solar_radiation"]
    )
    assert hasattr(loaded, "predict")


def test_load_latest_recalibrated_model_raises_on_feature_columns_mismatch(tmp_path):
    _use_sqlite_tracking(tmp_path, "test-columns-mismatch")
    _register(feature_columns=["soil_moisture", "solar_radiation"])

    with pytest.raises(ModelContractMismatch):
        load_latest_recalibrated_model(
            "sensor-a", expected_feature_columns=["soil_moisture", "temperature"]
        )


def test_load_latest_recalibrated_model_does_not_load_the_model_when_mismatch_detected(tmp_path):
    # "no cargar silenciosamente": el mismatch debe detectarse antes de
    # descargar/deserializar el modelo real desde el artifact store.
    _use_sqlite_tracking(tmp_path, "test-mismatch-fails-fast")
    _register(feature_columns=["soil_moisture"])

    with pytest.raises(ModelContractMismatch) as exc_info:
        load_latest_recalibrated_model("sensor-a", expected_feature_columns=["otra_columna"])

    assert "sensor-a" in str(exc_info.value)
    assert "otra_columna" in str(exc_info.value) or "soil_moisture" in str(exc_info.value)
