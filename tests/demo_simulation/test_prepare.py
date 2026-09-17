import pandas as pd
import pytest

from data_ingestion.sensor_naming import dataset_name_for, feedback_log_name_for
from data_ingestion.storage import load_dataset, save_dataset
from scripts.demo_simulation.config import DemoConfigError, DemoSessionConfig
from scripts.demo_simulation.manifest import load_manifest
from scripts.demo_simulation.prepare import DemoCollisionError, prepare_session
from tests.demo_simulation.conftest import utc_today


def test_prepare_creates_manifest_and_exclusive_history(live_backend, reference_session_kwargs):
    config = DemoSessionConfig(**reference_session_kwargs)

    result = prepare_session(
        config,
        today=utc_today(),
        sessions_root=live_backend.sessions_dir,
        data_dir=live_backend.data_dir,
        session_id="demo-fixture1",
    )

    assert result.manifest.session_id == "demo-fixture1"
    assert result.manifest.sensor_id == "demo-fixture1"
    assert result.manifest.status == "prepared"
    assert result.history_rows == reference_session_kwargs["history_days"]

    dataset = load_dataset(dataset_name_for("demo-fixture1"), data_dir=live_backend.data_dir)
    assert len(dataset) == reference_session_kwargs["history_days"]
    assert (dataset["origen"] == "sintetico").all()
    # Prefijo histórico termina antes del primer día de reproducción; no se
    # prepublica ningún día del período a reproducir.
    last_history_day = pd.to_datetime(dataset["timestamp"]).max().date()
    assert last_history_day == config.history_end

    manifest = load_manifest(live_backend.sessions_dir, "demo-fixture1")
    assert manifest.contract["horizon_days"] == 3
    assert manifest.last_generated_reading is not None
    assert manifest.last_generated_reading["et0"] is not None


def test_prepare_rejects_non_demo_prefixed_sensor(live_backend, reference_session_kwargs):
    config = DemoSessionConfig(**reference_session_kwargs)

    with pytest.raises(DemoConfigError, match="prefijo"):
        prepare_session(
            config,
            today=utc_today(),
            sessions_root=live_backend.sessions_dir,
            data_dir=live_backend.data_dir,
            session_id="sensor-a",
        )


def test_prepare_rejects_dataset_collision_without_overwriting(
    live_backend, reference_session_kwargs
):
    config = DemoSessionConfig(**reference_session_kwargs)
    existing = pd.DataFrame({"timestamp": [pd.Timestamp("2020-01-01")], "soil_moisture": [0.3]})
    dataset_path = live_backend.data_dir / f"{dataset_name_for('demo-collide')}.parquet"
    save_dataset(dataset_name_for("demo-collide"), existing, data_dir=live_backend.data_dir)
    before_bytes = dataset_path.read_bytes()

    with pytest.raises(DemoCollisionError, match="Ya existe un dataset"):
        prepare_session(
            config,
            today=utc_today(),
            sessions_root=live_backend.sessions_dir,
            data_dir=live_backend.data_dir,
            session_id="demo-collide",
        )

    assert dataset_path.read_bytes() == before_bytes


def test_prepare_rejects_feedback_collision_without_overwriting(
    live_backend, reference_session_kwargs
):
    config = DemoSessionConfig(**reference_session_kwargs)
    from human_feedback.registry import save_feedback_log
    from human_feedback.schema import init_feedback_log

    save_feedback_log(
        feedback_log_name_for("demo-fbcollide"),
        init_feedback_log(pd.Series([], dtype="datetime64[ns]"), pd.Series([], dtype="int64")),
        data_dir=live_backend.data_dir,
    )

    with pytest.raises(DemoCollisionError, match="Ya existe un registro de feedback"):
        prepare_session(
            config,
            today=utc_today(),
            sessions_root=live_backend.sessions_dir,
            data_dir=live_backend.data_dir,
            session_id="demo-fbcollide",
        )

    dataset_path = live_backend.data_dir / f"{dataset_name_for('demo-fbcollide')}.parquet"
    assert not dataset_path.exists()


def test_prepare_rejects_session_id_collision(live_backend, reference_session_kwargs):
    config = DemoSessionConfig(**reference_session_kwargs)
    prepare_session(
        config,
        today=utc_today(),
        sessions_root=live_backend.sessions_dir,
        data_dir=live_backend.data_dir,
        session_id="demo-dup",
    )

    with pytest.raises(DemoCollisionError, match="Ya existe una sesión"):
        prepare_session(
            config,
            today=utc_today(),
            sessions_root=live_backend.sessions_dir,
            data_dir=live_backend.data_dir,
            session_id="demo-dup",
        )


def test_prepare_rejects_future_start_date(live_backend, reference_session_kwargs):
    reference_session_kwargs = dict(reference_session_kwargs)
    reference_session_kwargs["start_date"] = utc_today()
    config = DemoSessionConfig(**reference_session_kwargs)

    with pytest.raises(DemoConfigError, match="pasada"):
        prepare_session(
            config,
            today=utc_today(),
            sessions_root=live_backend.sessions_dir,
            data_dir=live_backend.data_dir,
            session_id="demo-future",
        )


def test_prepare_leaves_other_sensor_files_untouched(live_backend, reference_session_kwargs):
    other_dataset = live_backend.data_dir / f"{dataset_name_for('sensor-existing')}.parquet"
    save_dataset(
        dataset_name_for("sensor-existing"),
        pd.DataFrame({"timestamp": [pd.Timestamp("2020-01-01")], "soil_moisture": [0.3]}),
        data_dir=live_backend.data_dir,
    )
    before = other_dataset.stat()

    config = DemoSessionConfig(**reference_session_kwargs)
    prepare_session(
        config,
        today=utc_today(),
        sessions_root=live_backend.sessions_dir,
        data_dir=live_backend.data_dir,
        session_id="demo-isolated",
    )

    after = other_dataset.stat()
    assert (before.st_mtime, before.st_size) == (after.st_mtime, after.st_size)
