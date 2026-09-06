import dataclasses

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from architecture_integration.pipeline import predict_available, run_end_to_end_pipeline
from human_feedback.lineage import (
    FeedbackReference,
    LineageValidationError,
    RecalibrationLineage,
    build_feedback_references,
)
from human_feedback.recalibration import recalibrate_predictor
from human_feedback.schema import init_prediction_feedback, update_feedback


def _base_kwargs(**overrides):
    kwargs = dict(
        recalibration_id="r1",
        sensor_id="sensor-a",
        source_model_id="model-a",
        successor_model_id="model-b",
        feedback_references=[
            FeedbackReference(
                sensor_id="sensor-a",
                fecha="2024-01-01 00:00:00",
                model_version="model-a",
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
    kwargs.update(overrides)
    return kwargs


def _dataset(n=100):
    rng = np.random.default_rng(4)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n),
            "soil_moisture": rng.uniform(0.1, 0.5, n),
            "solar_radiation": rng.uniform(5, 30, n),
        }
    )


def _run(df, **kwargs):
    params = dict(
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df.timestamp.iloc[75].date(),
        model=RandomForestClassifier(n_estimators=5, random_state=0),
        include_anomaly_detection=False,
    )
    return run_end_to_end_pipeline(df, **(params | kwargs))


def test_recalibration_lineage_roundtrip_through_dict():
    ref = FeedbackReference(
        sensor_id="sensor-a",
        fecha="2024-01-01 00:00:00",
        model_version="model-a",
        target_timestamp="2024-01-04 00:00:00",
    )
    lineage = RecalibrationLineage(
        recalibration_id="r1",
        sensor_id="sensor-a",
        source_model_id="model-a",
        successor_model_id="model-b",
        feedback_references=[ref],
        recalibrated_at="2026-09-06 00:00:00",
        source_trained_through="2024-01-04",
        successor_trained_through="2024-01-05",
        dataset_fingerprint="abc123",
        contract_version=1,
        pipeline_version="controlled_daily_v3",
    )

    restored = RecalibrationLineage.from_dict(lineage.to_dict())

    assert restored == lineage


def test_build_feedback_references_only_covers_pending_correction_dates():
    """El evento de linaje de un segundo ciclo (B->C) debe referenciar
    únicamente el feedback nuevo originado por B, no el histórico de A
    ya reaplicado (requirement "Linaje explícito de recalibraciones
    HITL").
    """
    df = _dataset()
    predictor_a = _run(df)["predictor"]

    forecast_a = predict_available(df, predictor_a)
    cycle1 = forecast_a.tail(4).head(2).reset_index(drop=True)
    log = init_prediction_feedback(cycle1, predictor_a.model_id, 3, predictor_a.threshold)
    log = update_feedback(log, cycle1.timestamp.iloc[0], "rechazada", 1)
    predictor_b, dates_1, _ = recalibrate_predictor(predictor_a, df, log)

    refs_1 = build_feedback_references("sensor-a", log, dates_1)
    assert len(refs_1) == 1
    assert refs_1[0].sensor_id == "sensor-a"
    assert refs_1[0].fecha == str(cycle1.timestamp.iloc[0])
    assert refs_1[0].model_version == predictor_a.model_id

    forecast_b = predict_available(df, predictor_b)
    cycle2 = forecast_b.tail(2).reset_index(drop=True)
    fresh_b = init_prediction_feedback(cycle2, predictor_b.model_id, 3, predictor_b.threshold)
    log = pd.concat([log, fresh_b[~fresh_b.fecha.isin(log.fecha)]], ignore_index=True)
    log = update_feedback(log, cycle2.timestamp.iloc[0], "rechazada", 0)

    predictor_c, dates_2, _ = recalibrate_predictor(predictor_b, df, log)
    refs_2 = build_feedback_references("sensor-a", log, dates_2)

    assert len(refs_2) == 1
    assert refs_2[0].fecha == str(cycle2.timestamp.iloc[0])
    assert refs_2[0].model_version == predictor_b.model_id
    assert predictor_c.model_id not in {ref.model_version for ref in refs_1 + refs_2}


def test_lineage_rejects_source_equal_to_successor():
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(**_base_kwargs(successor_model_id="model-a"))


def test_lineage_rejects_empty_feedback_references():
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(**_base_kwargs(feedback_references=[]))


def test_lineage_rejects_duplicate_feedback_references():
    ref = FeedbackReference(
        sensor_id="sensor-a",
        fecha="2024-01-01 00:00:00",
        model_version="model-a",
        target_timestamp="2024-01-04 00:00:00",
    )
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(**_base_kwargs(feedback_references=[ref, ref]))


def test_lineage_rejects_reference_from_a_different_sensor():
    ref = FeedbackReference(
        sensor_id="sensor-b",
        fecha="2024-01-01 00:00:00",
        model_version="model-a",
        target_timestamp="2024-01-04 00:00:00",
    )
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(**_base_kwargs(feedback_references=[ref]))


def test_lineage_rejects_reference_belonging_to_a_different_predictor():
    ref = FeedbackReference(
        sensor_id="sensor-a",
        fecha="2024-01-01 00:00:00",
        model_version="model-z",
        target_timestamp="2024-01-04 00:00:00",
    )
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(**_base_kwargs(feedback_references=[ref]))


def test_lineage_rejects_successor_trained_through_before_source():
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(
            **_base_kwargs(
                source_trained_through="2024-01-10", successor_trained_through="2024-01-05"
            )
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "recalibration_id",
        "sensor_id",
        "source_model_id",
        "successor_model_id",
        "dataset_fingerprint",
        "pipeline_version",
    ],
)
def test_lineage_rejects_empty_identifiers(field_name):
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(**_base_kwargs(**{field_name: ""}))


def test_lineage_rejects_invalid_contract_version():
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(**_base_kwargs(contract_version=0))


def test_lineage_rejects_invalid_timestamp():
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(**_base_kwargs(recalibrated_at="no-es-una-fecha"))


def test_lineage_feedback_references_cannot_be_modified_after_creation():
    lineage = RecalibrationLineage(**_base_kwargs())

    assert isinstance(lineage.feedback_references, tuple)
    with pytest.raises(TypeError):
        lineage.feedback_references[0] = lineage.feedback_references[0]
    with pytest.raises(AttributeError):
        lineage.feedback_references.append(lineage.feedback_references[0])
    with pytest.raises(dataclasses.FrozenInstanceError):
        lineage.feedback_references = ()


def test_from_dict_revalidates_a_corrupted_artifact():
    """Recuperar un artefacto persistido (`from_dict`) debe volver a
    ejecutar la misma validación semántica que crear el evento — no solo
    reconstruir la forma de los datos.
    """
    lineage = RecalibrationLineage(**_base_kwargs())
    payload = lineage.to_dict()
    payload["source_model_id"] = payload["successor_model_id"]  # corrompe la invariante

    with pytest.raises(LineageValidationError):
        RecalibrationLineage.from_dict(payload)
