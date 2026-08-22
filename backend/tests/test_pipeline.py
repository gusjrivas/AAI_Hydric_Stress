import numpy as np

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
