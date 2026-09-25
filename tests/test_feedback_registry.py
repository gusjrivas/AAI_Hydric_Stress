import multiprocessing

import pandas as pd
import pytest

from data_ingestion.storage import load_dataset
from human_feedback.registry import (
    integrate_feedback_with_predictions,
    save_feedback_log,
    update_feedback_log_atomically,
    upsert_feedback_log,
)
from human_feedback.schema import init_feedback_log, update_feedback


def test_save_feedback_log_roundtrips_through_storage_contract(tmp_path):
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)
    log = update_feedback(log, fecha=pd.Timestamp("2024-01-01"), estado_validacion="confirmada")

    save_feedback_log("feedback_test", log, data_dir=tmp_path)
    loaded = load_dataset("feedback_test", data_dir=tmp_path)

    pd.testing.assert_frame_equal(loaded, log)


def test_upsert_feedback_log_preserves_existing_validation_and_adds_new_dates():
    existing = init_feedback_log(pd.to_datetime(["2024-01-01", "2024-01-02"]), pd.Series([1, 0]))
    existing = update_feedback(
        existing, fecha=pd.Timestamp("2024-01-01"), estado_validacion="confirmada"
    )

    new_dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    new_alerts = pd.Series([0, 0, 1])

    merged = upsert_feedback_log(existing, new_dates, new_alerts)

    row_jan1 = merged.loc[merged["fecha"] == pd.Timestamp("2024-01-01")].iloc[0]
    row_jan3 = merged.loc[merged["fecha"] == pd.Timestamp("2024-01-03")].iloc[0]

    assert row_jan1["estado_validacion"] == "confirmada"
    assert row_jan3["estado_validacion"] == "pendiente"
    assert len(merged) == 3


def _worker_update_atomically(data_dir, name, barrier, fecha, estado):
    from human_feedback.registry import update_feedback_log_atomically
    from human_feedback.schema import update_feedback

    def _apply(log):
        return update_feedback(log, fecha=fecha, estado_validacion=estado)

    barrier.wait()
    update_feedback_log_atomically(name, _apply, data_dir=data_dir)


def test_update_feedback_log_atomically_survives_concurrent_updates_to_different_rows(tmp_path):
    dates = pd.date_range("2024-01-01", periods=4, freq="D")
    alerts = pd.Series([1, 1, 0, 0])
    initial = init_feedback_log(pd.Series(dates), alerts)
    save_feedback_log("feedback_concurrent", initial, data_dir=tmp_path)

    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p0 = ctx.Process(
        target=_worker_update_atomically,
        args=(tmp_path, "feedback_concurrent", barrier, dates[0], "confirmada"),
    )
    p1 = ctx.Process(
        target=_worker_update_atomically,
        args=(tmp_path, "feedback_concurrent", barrier, dates[1], "rechazada"),
    )
    p0.start()
    p1.start()
    p0.join(timeout=60)
    p1.join(timeout=60)
    assert p0.exitcode == 0
    assert p1.exitcode == 0

    final = load_dataset("feedback_concurrent", data_dir=tmp_path)
    row0 = final.loc[final["fecha"] == dates[0]].iloc[0]
    row1 = final.loc[final["fecha"] == dates[1]].iloc[0]
    assert row0["estado_validacion"] == "confirmada"
    assert row1["estado_validacion"] == "rechazada"


def test_update_feedback_log_atomically_creates_the_file_when_missing_and_requested(tmp_path):
    def _apply(existing):
        assert existing is None
        return init_feedback_log(pd.to_datetime(["2024-02-01"]), pd.Series([1]))

    result = update_feedback_log_atomically(
        "feedback_new", _apply, data_dir=tmp_path, create_if_missing=True
    )

    assert len(result) == 1
    loaded = load_dataset("feedback_new", data_dir=tmp_path)
    pd.testing.assert_frame_equal(loaded, result)


def test_update_feedback_log_atomically_still_raises_when_missing_and_not_requested(tmp_path):
    def _apply(existing):
        raise AssertionError(
            "update_fn must not run when the file is missing and create_if_missing=False"
        )

    with pytest.raises(FileNotFoundError):
        update_feedback_log_atomically("feedback_missing", _apply, data_dir=tmp_path)


def test_integrate_feedback_with_predictions_joins_by_date():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)

    predictions = pd.DataFrame(
        {
            "fecha": dates,
            "y_proba": [0.8, 0.3],
            "stress_label": [1, 0],
        }
    )

    integrated = integrate_feedback_with_predictions(log, predictions)

    row = integrated.loc[integrated["fecha"] == pd.Timestamp("2024-01-01")].iloc[0]
    assert row["y_proba"] == 0.8
    assert row["stress_label"] == 1
    assert row["estado_validacion"] == "pendiente"
