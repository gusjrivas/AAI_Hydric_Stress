from datetime import date, timedelta

import pandas as pd
import pytest

from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import load_dataset, save_dataset
from scripts.demo_simulation.config import DemoSessionConfig
from scripts.demo_simulation.manifest import load_manifest
from scripts.demo_simulation.prepare import prepare_session
from scripts.demo_simulation.worker import DemoStepError, run_session
from tests.demo_simulation.conftest import utc_today


def _prepare(live_backend, reference_session_kwargs, session_id="demo-worker"):
    config = DemoSessionConfig(**reference_session_kwargs)
    return prepare_session(
        config,
        today=utc_today(),
        sessions_root=live_backend.sessions_dir,
        data_dir=live_backend.data_dir,
        session_id=session_id,
    )


def test_five_consecutive_steps_complete_session(live_backend, reference_session_kwargs):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-five-steps")

    manifest = run_session(
        "demo-five-steps", live_backend.sessions_dir, steps=5, sleep_fn=lambda _seconds: None
    )

    assert manifest.status == "completed"
    assert manifest.cursor == 5
    assert manifest.last_error is None
    assert len(manifest.steps) == 5
    assert all(step.phase == "completed" for step in manifest.steps.values())

    start = date.fromisoformat(prepared.manifest.start_date)
    expected_dates = {(start + timedelta(days=i)).isoformat() for i in range(5)}
    assert set(manifest.steps) == expected_dates

    dataset = load_dataset(dataset_name_for("demo-five-steps"), data_dir=live_backend.data_dir)
    dataset_dates = set(pd.to_datetime(dataset["timestamp"]).dt.date.astype(str))
    # Ninguna lectura futura respecto de las 5 reproducidas: exactamente
    # historia + 5 días nuevos, ninguno posterior al último reproducido.
    assert expected_dates <= dataset_dates
    assert pd.to_datetime(dataset["timestamp"]).max().date().isoformat() == max(expected_dates)
    assert len(dataset) == reference_session_kwargs["history_days"] + 5

    for day_key in expected_dates:
        step = manifest.steps[day_key]
        assert step.forecast_verdict["fecha"] == day_key
        assert step.feedback_confirmation["fecha"] == day_key
        assert step.feedback_confirmation["y_proba"] == step.forecast_verdict["probabilidad"]


def test_steps_are_causal_and_sequential(live_backend, reference_session_kwargs):
    _prepare(live_backend, reference_session_kwargs, "demo-causal")

    manifest = run_session(
        "demo-causal", live_backend.sessions_dir, steps=3, sleep_fn=lambda _seconds: None
    )

    ordered_dates = sorted(manifest.steps)
    assert ordered_dates == [date.fromisoformat(d).isoformat() for d in ordered_dates]
    for earlier, later in zip(ordered_dates, ordered_dates[1:]):
        assert date.fromisoformat(later) == date.fromisoformat(earlier) + timedelta(days=1)
    # El pronóstico de cada día usa el objetivo real informado por el
    # backend (fecha + horizonte), nunca un valor inventado localmente.
    for day_key in ordered_dates:
        verdict = manifest.steps[day_key].forecast_verdict
        assert (
            verdict["fecha_objetivo"]
            == (
                date.fromisoformat(day_key) + timedelta(days=manifest.contract["horizon_days"])
            ).isoformat()
        )


def test_run_stops_and_blocks_when_ingest_endpoint_fails(
    live_backend, reference_session_kwargs, monkeypatch
):
    _prepare(live_backend, reference_session_kwargs, "demo-blocked")

    import scripts.demo_simulation.worker as worker_module

    def _fail_post(*args, **kwargs):
        raise worker_module.DemoBackendError("simulado", status_code=500)

    monkeypatch.setattr(worker_module, "post_reading", _fail_post)

    with pytest.raises(DemoStepError):
        run_session("demo-blocked", live_backend.sessions_dir, steps=1, sleep_fn=lambda _s: None)

    manifest = load_manifest(live_backend.sessions_dir, "demo-blocked")
    assert manifest.status == "blocked"
    assert manifest.last_error is not None
    assert manifest.cursor == 0

    dataset = load_dataset(dataset_name_for("demo-blocked"), data_dir=live_backend.data_dir)
    assert len(dataset) == reference_session_kwargs["history_days"]


def test_blocked_session_does_not_auto_retry_on_next_run(
    live_backend, reference_session_kwargs, monkeypatch
):
    _prepare(live_backend, reference_session_kwargs, "demo-blocked2")
    import scripts.demo_simulation.worker as worker_module

    monkeypatch.setattr(
        worker_module,
        "post_reading",
        lambda *a, **k: (_ for _ in ()).throw(worker_module.DemoBackendError("x", 500)),
    )
    with pytest.raises(DemoStepError):
        run_session("demo-blocked2", live_backend.sessions_dir, steps=1, sleep_fn=lambda _s: None)

    with pytest.raises(DemoStepError, match="bloqueada"):
        run_session("demo-blocked2", live_backend.sessions_dir, steps=1, sleep_fn=lambda _s: None)


def test_forecast_failure_preserves_already_ingested_day(
    live_backend, reference_session_kwargs, monkeypatch
):
    _prepare(live_backend, reference_session_kwargs, "demo-forecast-fail")
    import scripts.demo_simulation.worker as worker_module

    def _fail_forecast(*args, **kwargs):
        raise worker_module.DemoBackendError("sin historial entrenable", status_code=422)

    monkeypatch.setattr(worker_module, "run_forecast", _fail_forecast)

    with pytest.raises(DemoStepError):
        run_session(
            "demo-forecast-fail", live_backend.sessions_dir, steps=1, sleep_fn=lambda _s: None
        )

    manifest = load_manifest(live_backend.sessions_dir, "demo-forecast-fail")
    assert manifest.status == "blocked"
    assert manifest.cursor == 0

    dataset = load_dataset(dataset_name_for("demo-forecast-fail"), data_dir=live_backend.data_dir)
    # La ingesta ya aceptada se conserva aunque el pronóstico no se confirmó.
    assert len(dataset) == reference_session_kwargs["history_days"] + 1


def test_run_preserves_sentinel_files_of_other_sensors(live_backend, reference_session_kwargs):
    sentinel_path = live_backend.data_dir / f"{dataset_name_for('sensor-untouched')}.parquet"
    save_dataset(
        dataset_name_for("sensor-untouched"),
        pd.DataFrame({"timestamp": [pd.Timestamp("2020-01-01")], "soil_moisture": [0.3]}),
        data_dir=live_backend.data_dir,
    )
    before = sentinel_path.stat()

    _prepare(live_backend, reference_session_kwargs, "demo-sentinel")
    run_session("demo-sentinel", live_backend.sessions_dir, steps=2, sleep_fn=lambda _s: None)

    after = sentinel_path.stat()
    assert (before.st_mtime, before.st_size) == (after.st_mtime, after.st_size)
