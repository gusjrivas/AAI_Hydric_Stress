import numpy as np

import app.pipeline as pipeline_module
from app.config import DATASET_NAME
from app.pipeline import execute_configured_pipeline, load_dataset_or_raise
from data_ingestion.storage import load_dataset


def test_execute_configured_pipeline_trains_a_new_model_when_none_recalibrated(monkeypatch):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: None)
    df = load_dataset(DATASET_NAME)

    result = execute_configured_pipeline(df)

    assert hasattr(result["model"], "predict_proba")
    assert len(result["test"]) > 0


def test_execute_configured_pipeline_reuses_recalibrated_model_without_refitting(monkeypatch):
    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("no debería reentrenar cuando hay un modelo recalibrado")

        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    fake_model = _FitRaisesModel()
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: fake_model)
    df = load_dataset(DATASET_NAME)

    result = execute_configured_pipeline(df)

    assert result["model"] is fake_model


def test_load_dataset_or_raise_raises_file_not_found_with_explicit_message(monkeypatch):
    monkeypatch.setattr("app.pipeline.DATASET_NAME", "esto_no_existe")

    try:
        load_dataset_or_raise()
        assert False, "debería haber levantado FileNotFoundError"
    except FileNotFoundError as error:
        assert "esto_no_existe" in str(error)


def test_execute_configured_pipeline_selects_a_model_automatically_when_none_recalibrated(
    monkeypatch,
):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: None)
    df = load_dataset(DATASET_NAME)

    result = execute_configured_pipeline(df)

    assert result["model_name"] in {"logistic_regression", "random_forest"}


def test_execute_configured_pipeline_reuses_cached_selection_when_dataset_unchanged(monkeypatch):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: None)
    monkeypatch.setattr("app.pipeline._selection_cache", None)
    df = load_dataset(DATASET_NAME)

    received_models = []
    original = pipeline_module.run_end_to_end_pipeline

    def _spy(*args, **kwargs):
        received_models.append(kwargs.get("model"))
        return original(*args, **kwargs)

    monkeypatch.setattr("app.pipeline.run_end_to_end_pipeline", _spy)

    first = execute_configured_pipeline(df)
    second = execute_configured_pipeline(df)

    assert received_models == [None, first["model"]]
    assert second["model"] is first["model"]
    assert second["model_name"] == first["model_name"]


def test_execute_configured_pipeline_reselects_when_dataset_fingerprint_changes(monkeypatch):
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: None)
    monkeypatch.setattr("app.pipeline._selection_cache", None)
    df = load_dataset(DATASET_NAME)

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

    execute_configured_pipeline(df)
    execute_configured_pipeline(df)

    assert received_models == [None, None]


def test_execute_configured_pipeline_recalibrated_model_ignores_selection_cache(monkeypatch):
    class _FitRaisesModel:
        def fit(self, X, y):
            raise AssertionError("no debería reentrenar cuando hay un modelo recalibrado")

        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    cached_model = _FitRaisesModel()
    monkeypatch.setattr(
        "app.pipeline._selection_cache",
        {"model": cached_model, "model_name": "random_forest", "fingerprint": (0.0, 0)},
    )
    fake_recalibrated = _FitRaisesModel()
    monkeypatch.setattr("app.pipeline.load_latest_recalibrated_model", lambda: fake_recalibrated)
    df = load_dataset(DATASET_NAME)

    result = execute_configured_pipeline(df)

    assert result["model"] is fake_recalibrated


def test_load_dataset_or_raise_returns_dataframe_and_matching_fingerprint():
    from data_ingestion.storage import get_dataset_fingerprint

    df, fingerprint = load_dataset_or_raise()

    assert len(df) > 0
    assert fingerprint == get_dataset_fingerprint(DATASET_NAME)
