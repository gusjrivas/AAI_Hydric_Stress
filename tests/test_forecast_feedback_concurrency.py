"""F-09 completion: forecast.py's emission cycle now goes through the same
atomic lock as confirm/reject (`human_feedback.registry.register_forecast_feedback`).
These tests call the REAL functions the routers use directly — no
reimplementation, no isolated-helper-only coverage — under real OS
process concurrency (repo convention: `multiprocessing.get_context("spawn")`,
see `tests/test_controlled_daily_v4_holdout_ledger.py`). MLflow/model
training is not involved: `register_forecast_feedback` never touches
MLflow, and `confirm_feedback`/`reject_feedback` never did either — the
risk this file tests is purely the storage-locking contract, so no
doubles are needed for those two real functions.
"""

from __future__ import annotations

import multiprocessing
from datetime import date as date_type
from pathlib import Path

import pandas as pd

from app.routers.feedback import confirm_feedback, reject_feedback
from app.schemas import RejectRequest
from data_ingestion.sensor_naming import feedback_log_name_for
from data_ingestion.storage import load_dataset
from human_feedback.registry import register_forecast_feedback, save_feedback_log
from human_feedback.schema import init_feedback_log, init_prediction_feedback

NAME = "feedback_concurrency_forecast"
# confirm_feedback/reject_feedback derive their own file name from
# sensor_id via feedback_log_name_for — the emission side must write to
# that exact name for the two to race over the same file.
SENSOR_NAME = feedback_log_name_for("sensor-x")


def _fresh(dates, y_proba, model_version="model-x"):
    return init_prediction_feedback(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(dates),
                "alert": [1] * len(dates),
                "y_proba": y_proba,
            }
        ),
        model_version,
        horizon_days=3,
        threshold=0.5,
    )


def _seed_confirmable_log(data_dir: Path, fecha: str) -> None:
    dates = pd.to_datetime([fecha])
    log = init_feedback_log(dates, pd.Series([1]))
    log["target_timestamp"] = dates + pd.Timedelta(days=3)
    log["model_version"] = "seed-model"
    log["y_proba"] = [0.8]
    log["target_threshold"] = 0.5
    log["issued_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)
    log["validated_at"] = pd.NaT
    save_feedback_log(SENSOR_NAME, log, data_dir=data_dir)


def _worker_emit(data_dir, barrier, dates, y_proba, model_version, name=NAME):
    barrier.wait()
    register_forecast_feedback(name, _fresh(dates, y_proba, model_version), data_dir=data_dir)


def _worker_confirm(data_dir, barrier, fecha):
    barrier.wait()
    confirm_feedback(fecha=date_type.fromisoformat(fecha), sensor_id="sensor-x", data_dir=data_dir)


def _worker_reject(data_dir, barrier, fecha, etiqueta, observacion):
    barrier.wait()
    reject_feedback(
        fecha=date_type.fromisoformat(fecha),
        body=RejectRequest(etiqueta_corregida=etiqueta, observacion=observacion),
        sensor_id="sensor-x",
        data_dir=data_dir,
    )


def test_concurrent_emission_and_confirmation_preserve_both(tmp_path):
    _seed_confirmable_log(tmp_path, "2024-04-01")
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p_emit = ctx.Process(
        target=_worker_emit,
        args=(tmp_path, barrier, ["2024-04-10"], [0.6], "model-new", SENSOR_NAME),
    )
    p_confirm = ctx.Process(target=_worker_confirm, args=(tmp_path, barrier, "2024-04-01"))
    p_emit.start()
    p_confirm.start()
    p_emit.join(timeout=60)
    p_confirm.join(timeout=60)
    assert p_emit.exitcode == 0
    assert p_confirm.exitcode == 0

    final = load_dataset(SENSOR_NAME, data_dir=tmp_path)
    assert len(final) == 2
    confirmed = final.loc[final["fecha"] == pd.Timestamp("2024-04-01")].iloc[0]
    assert confirmed["estado_validacion"] == "confirmada"
    emitted = final.loc[final["fecha"] == pd.Timestamp("2024-04-10")].iloc[0]
    assert emitted["model_version"] == "model-new"


def test_concurrent_emission_and_rejection_preserve_correction_and_observation(tmp_path):
    _seed_confirmable_log(tmp_path, "2024-04-01")
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p_emit = ctx.Process(
        target=_worker_emit,
        args=(tmp_path, barrier, ["2024-04-11"], [0.4], "model-new", SENSOR_NAME),
    )
    p_reject = ctx.Process(
        target=_worker_reject, args=(tmp_path, barrier, "2024-04-01", 0, "no habia estres real")
    )
    p_emit.start()
    p_reject.start()
    p_emit.join(timeout=60)
    p_reject.join(timeout=60)
    assert p_emit.exitcode == 0
    assert p_reject.exitcode == 0

    final = load_dataset(SENSOR_NAME, data_dir=tmp_path)
    assert len(final) == 2
    rejected = final.loc[final["fecha"] == pd.Timestamp("2024-04-01")].iloc[0]
    assert rejected["estado_validacion"] == "rechazada"
    assert int(rejected["etiqueta_corregida"]) == 0
    assert rejected["observacion"] == "no habia estres real"
    emitted = final.loc[final["fecha"] == pd.Timestamp("2024-04-11")].iloc[0]
    assert emitted["model_version"] == "model-new"


def test_two_concurrent_emissions_with_disjoint_dates_do_not_lose_rows(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p0 = ctx.Process(
        target=_worker_emit,
        args=(tmp_path, barrier, ["2024-05-01", "2024-05-02"], [0.5, 0.5], "model-a"),
    )
    p1 = ctx.Process(
        target=_worker_emit,
        args=(tmp_path, barrier, ["2024-05-03", "2024-05-04"], [0.5, 0.5], "model-b"),
    )
    p0.start()
    p1.start()
    p0.join(timeout=60)
    p1.join(timeout=60)
    assert p0.exitcode == 0
    assert p1.exitcode == 0

    final = load_dataset(NAME, data_dir=tmp_path)
    assert len(final) == 4
    assert set(final["fecha"]) == {
        pd.Timestamp(d) for d in ["2024-05-01", "2024-05-02", "2024-05-03", "2024-05-04"]
    }


def test_two_concurrent_emissions_with_an_overlapping_date_do_not_duplicate_identity(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p0 = ctx.Process(target=_worker_emit, args=(tmp_path, barrier, ["2024-06-01"], [0.9], "model-a"))
    p1 = ctx.Process(target=_worker_emit, args=(tmp_path, barrier, ["2024-06-01"], [0.1], "model-b"))
    p0.start()
    p1.start()
    p0.join(timeout=60)
    p1.join(timeout=60)
    assert p0.exitcode == 0
    assert p1.exitcode == 0

    final = load_dataset(NAME, data_dir=tmp_path)
    matching = final.loc[final["fecha"] == pd.Timestamp("2024-06-01")]
    assert len(matching) == 1
    assert matching.iloc[0]["model_version"] in ("model-a", "model-b")


def test_concurrent_initial_creation_for_a_brand_new_sensor_preserves_a_valid_log(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p0 = ctx.Process(target=_worker_emit, args=(tmp_path, barrier, ["2024-07-01"], [0.5], "model-a"))
    p1 = ctx.Process(target=_worker_emit, args=(tmp_path, barrier, ["2024-07-02"], [0.5], "model-b"))
    p0.start()
    p1.start()
    p0.join(timeout=60)
    p1.join(timeout=60)
    assert p0.exitcode == 0
    assert p1.exitcode == 0

    final = load_dataset(NAME, data_dir=tmp_path)
    assert len(final) == 2
    assert set(final["fecha"]) == {pd.Timestamp("2024-07-01"), pd.Timestamp("2024-07-02")}
