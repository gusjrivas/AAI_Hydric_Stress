import json
import multiprocessing
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


def _append_many(storage_dir, package_id, run_id, count, barrier):
    from datetime import datetime, timezone

    from historical_replay.feedback import ReplayFeedbackRecord

    store = ReplayFeedbackStore(storage_dir, package_id=package_id)
    barrier.wait()
    for i in range(count):
        store.append(
            ReplayFeedbackRecord(
                timestamp_origen="2024-01-01",
                experiment_id="exp",
                run_id=run_id,
                estado_validacion="confirmada",
                etiqueta_corregida=1,
                observacion=f"{run_id}-{i}",
                registered_at=datetime.now(timezone.utc).isoformat(),
                simulated_at="2024-01-05",
            )
        )


def test_append_survives_concurrent_writers_without_loss_or_corruption(tmp_path):
    n_writers = 6
    n_per_writer = 100
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(n_writers)
    procs = [
        ctx.Process(
            target=_append_many,
            args=(str(tmp_path), "pkg-concurrent", f"writer{i}", n_per_writer, barrier),
        )
        for i in range(n_writers)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
        assert p.exitcode == 0

    path = tmp_path / "pkg-concurrent.jsonl"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == n_writers * n_per_writer

    seen = set()
    for line in lines:
        payload = json.loads(line)  # raises if any line is corrupted/interleaved
        key = (payload["run_id"], payload["observacion"])
        assert key not in seen
        seen.add(key)
    assert len(seen) == n_writers * n_per_writer


def test_append_lock_file_is_separate_from_the_data_file_and_packages_stay_isolated(tmp_path):
    from datetime import datetime, timezone

    from historical_replay.feedback import ReplayFeedbackRecord

    store_a = ReplayFeedbackStore(tmp_path, package_id="package-a")
    store_b = ReplayFeedbackStore(tmp_path, package_id="package-b")

    record = ReplayFeedbackRecord(
        timestamp_origen="2024-01-01",
        experiment_id="exp",
        run_id="writer",
        estado_validacion="confirmada",
        etiqueta_corregida=1,
        observacion="solo-a",
        registered_at=datetime.now(timezone.utc).isoformat(),
        simulated_at="2024-01-05",
    )
    store_a.append(record)

    assert (tmp_path / "package-a.jsonl").exists()
    assert (tmp_path / "package-a.jsonl.lock").exists()
    assert not (tmp_path / "package-b.jsonl").exists()
    assert store_b.list_for("2024-01-01") == []


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
