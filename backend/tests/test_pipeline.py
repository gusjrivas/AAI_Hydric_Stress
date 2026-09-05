from pathlib import Path

import numpy as np

import app.pipeline as pipeline_module
from app.config import HISTORICAL_DATASET_NAME
from app.pipeline import execute_configured_pipeline, load_dataset_or_raise
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import (
    DEFAULT_DATA_DIR,
    get_dataset_fingerprint,
    load_dataset,
    save_dataset,
)


def _seed_sensor_dataset(sensor_id: str, data_dir: Path) -> None:
    historical = load_dataset(HISTORICAL_DATASET_NAME, data_dir=DEFAULT_DATA_DIR)
    save_dataset(dataset_name_for(sensor_id), historical, data_dir=data_dir)


def test_execute_configured_pipeline_trains_a_new_model_when_none_recalibrated(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        "app.pipeline.load_latest_recalibrated_model", lambda sensor_id, **kwargs: None
    )
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    result = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert hasattr(result["model"], "predict_proba")
    assert len(result["test"]) > 0


def test_execute_configured_pipeline_reuses_recalibrated_model_without_refitting(
    monkeypatch, tmp_path
):
    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("no debería reentrenar cuando hay un modelo recalibrado")

        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    fake_model = _FitRaisesModel()
    monkeypatch.setattr(
        "app.pipeline.load_latest_recalibrated_model", lambda sensor_id, **kwargs: fake_model
    )
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    result = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert result["model"] is fake_model


def test_load_dataset_or_raise_raises_file_not_found_with_explicit_message(tmp_path):
    try:
        load_dataset_or_raise("sensor-inexistente", data_dir=tmp_path)
        assert False, "debería haber levantado FileNotFoundError"
    except FileNotFoundError as error:
        assert "sensor__sensor-inexistente" in str(error)


def test_execute_configured_pipeline_selects_a_model_automatically_when_none_recalibrated(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        "app.pipeline.load_latest_recalibrated_model", lambda sensor_id, **kwargs: None
    )
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    result = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert result["model_name"] in {"logistic_regression", "random_forest"}


def test_execute_configured_pipeline_reuses_cached_selection_when_dataset_unchanged(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        "app.pipeline.load_latest_recalibrated_model", lambda sensor_id, **kwargs: None
    )
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    received_models = []
    original = pipeline_module.run_end_to_end_pipeline

    def _spy(*args, **kwargs):
        received_models.append(kwargs.get("model"))
        return original(*args, **kwargs)

    monkeypatch.setattr("app.pipeline.run_end_to_end_pipeline", _spy)

    first = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)
    second = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert received_models == [None, first["model"]]
    assert second["model"] is first["model"]
    assert second["model_name"] == first["model_name"]


def test_execute_configured_pipeline_reselects_when_dataset_fingerprint_changes(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        "app.pipeline.load_latest_recalibrated_model", lambda sensor_id, **kwargs: None
    )
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    fingerprints = iter([(1.0, 100), (2.0, 200)])
    monkeypatch.setattr(
        "app.pipeline.get_dataset_fingerprint", lambda *args, **kwargs: next(fingerprints)
    )

    received_models = []
    original = pipeline_module.run_end_to_end_pipeline

    def _spy(*args, **kwargs):
        received_models.append(kwargs.get("model"))
        return original(*args, **kwargs)

    monkeypatch.setattr("app.pipeline.run_end_to_end_pipeline", _spy)

    execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)
    execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert received_models == [None, None]


def test_execute_configured_pipeline_recalibrated_model_ignores_selection_cache(
    monkeypatch, tmp_path
):
    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("no debería reentrenar cuando hay un modelo recalibrado")

        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    cached_model = _FitRaisesModel()
    monkeypatch.setattr(
        "app.pipeline._selection_cache",
        {
            "sensor-a": {
                "model": cached_model,
                "model_name": "random_forest",
                "fingerprint": (0.0, 0),
            }
        },
    )
    fake_recalibrated = _FitRaisesModel()
    monkeypatch.setattr(
        "app.pipeline.load_latest_recalibrated_model", lambda sensor_id, **kwargs: fake_recalibrated
    )
    _seed_sensor_dataset("sensor-a", tmp_path)
    df, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    result = execute_configured_pipeline(df, "sensor-a", data_dir=tmp_path)

    assert result["model"] is fake_recalibrated


def test_load_dataset_or_raise_returns_dataframe_and_matching_fingerprint(tmp_path):
    _seed_sensor_dataset("sensor-a", tmp_path)

    df, fingerprint = load_dataset_or_raise("sensor-a", data_dir=tmp_path)

    assert len(df) > 0
    assert fingerprint == get_dataset_fingerprint(dataset_name_for("sensor-a"), data_dir=tmp_path)


def test_selection_cache_is_isolated_per_sensor(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.pipeline.load_latest_recalibrated_model", lambda sensor_id, **kwargs: None
    )
    _seed_sensor_dataset("sensor-a", tmp_path)
    _seed_sensor_dataset("sensor-b", tmp_path)
    df_a, _ = load_dataset_or_raise("sensor-a", data_dir=tmp_path)
    df_b, _ = load_dataset_or_raise("sensor-b", data_dir=tmp_path)

    received_models = []
    original = pipeline_module.run_end_to_end_pipeline

    def _spy(*args, **kwargs):
        received_models.append(kwargs.get("model"))
        return original(*args, **kwargs)

    monkeypatch.setattr("app.pipeline.run_end_to_end_pipeline", _spy)

    execute_configured_pipeline(df_a, "sensor-a", data_dir=tmp_path)
    execute_configured_pipeline(df_b, "sensor-b", data_dir=tmp_path)

    # ambos entrenan desde cero (model=None): el caché de "sensor-a" no se
    # reutilizó para "sensor-b"
    assert received_models == [None, None]
    assert set(pipeline_module._selection_cache.keys()) == {"sensor-a", "sensor-b"}
