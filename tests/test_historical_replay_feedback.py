from datetime import date

import pytest

from historical_replay.feedback import (
    FeedbackNotYetRevealedError,
    InvalidFeedbackContentError,
    ReplayFeedbackStore,
    UnknownPredictionError,
    register_feedback,
)
from historical_replay.records import build_records


def _package_records():
    row = {
        "experiment_id": "4",
        "run_id": "1157696b7bb941e394c5af530c762b07",
        "config_name": "base",
        "seed": 4,
        "timestamp": "2024-10-19T00:00:00.000",
        "target_timestamp": "2024-10-22T00:00:00.000",
        "target_observed": True,
        "y_true": 1.0,
        "y_proba": 0.44,
        "y_pred": 0,
    }
    return build_records([row], horizon_days=3)


def test_register_feedback_after_reveal_succeeds(tmp_path):
    records = _package_records()
    store = ReplayFeedbackStore(tmp_path, package_id="base-seed4-test")

    record = register_feedback(
        records,
        store,
        timestamp_origen=date(2024, 10, 19),
        simulated_date=date(2024, 10, 22),
        estado_validacion="confirmada",
        observacion="Coincide con lo que vimos en el suelo.",
    )

    assert record.timestamp_origen == "2024-10-19"
    assert record.simulated_at == "2024-10-22"
    assert record.registered_at is not None
    assert record.estado_validacion == "confirmada"

    stored = store.list_for("2024-10-19")
    assert len(stored) == 1
    assert stored[0] == record


def test_register_feedback_before_reveal_is_rejected(tmp_path):
    records = _package_records()
    store = ReplayFeedbackStore(tmp_path, package_id="base-seed4-test")

    with pytest.raises(FeedbackNotYetRevealedError):
        register_feedback(
            records,
            store,
            timestamp_origen=date(2024, 10, 19),
            simulated_date=date(2024, 10, 20),  # antes del objetivo (10-22)
            estado_validacion="confirmada",
        )

    assert store.list_for("2024-10-19") == []


def test_register_feedback_for_unknown_identity_is_rejected(tmp_path):
    records = _package_records()
    store = ReplayFeedbackStore(tmp_path, package_id="base-seed4-test")

    with pytest.raises(UnknownPredictionError):
        register_feedback(
            records,
            store,
            timestamp_origen=date(2019, 1, 1),
            simulated_date=date(2024, 10, 22),
            estado_validacion="confirmada",
        )


def test_register_feedback_with_invalid_estado_is_rejected(tmp_path):
    records = _package_records()
    store = ReplayFeedbackStore(tmp_path, package_id="base-seed4-test")

    with pytest.raises(InvalidFeedbackContentError):
        register_feedback(
            records,
            store,
            timestamp_origen=date(2024, 10, 19),
            simulated_date=date(2024, 10, 22),
            estado_validacion="pendiente",  # no admitido para feedback ya decidido
        )


def test_register_feedback_with_invalid_etiqueta_is_rejected(tmp_path):
    records = _package_records()
    store = ReplayFeedbackStore(tmp_path, package_id="base-seed4-test")

    with pytest.raises(InvalidFeedbackContentError):
        register_feedback(
            records,
            store,
            timestamp_origen=date(2024, 10, 19),
            simulated_date=date(2024, 10, 22),
            estado_validacion="rechazada",
            etiqueta_corregida=2,
        )


def test_feedback_is_not_visible_before_the_reveal_clock_even_after_registration(tmp_path):
    # El registro persiste, pero una consulta con reloj anterior al objetivo
    # no debe exponerlo (oculto por retroceso, sin borrarlo).
    records = _package_records()
    store = ReplayFeedbackStore(tmp_path, package_id="base-seed4-test")
    register_feedback(
        records,
        store,
        timestamp_origen=date(2024, 10, 19),
        simulated_date=date(2024, 10, 22),
        estado_validacion="confirmada",
    )

    from historical_replay.feedback import visible_feedback_for

    visible = visible_feedback_for(
        records, store, timestamp_origen=date(2024, 10, 19), simulated_date=date(2024, 10, 20)
    )
    assert visible == []

    visible_after = visible_feedback_for(
        records, store, timestamp_origen=date(2024, 10, 19), simulated_date=date(2024, 10, 22)
    )
    assert len(visible_after) == 1


def test_two_packages_use_independent_stores(tmp_path):
    records = _package_records()
    store_a = ReplayFeedbackStore(tmp_path, package_id="package-a")
    store_b = ReplayFeedbackStore(tmp_path, package_id="package-b")

    register_feedback(
        records,
        store_a,
        timestamp_origen=date(2024, 10, 19),
        simulated_date=date(2024, 10, 22),
        estado_validacion="confirmada",
    )

    assert store_a.list_for("2024-10-19") != []
    assert store_b.list_for("2024-10-19") == []
