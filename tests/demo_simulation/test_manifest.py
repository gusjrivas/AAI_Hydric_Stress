from scripts.demo_simulation.manifest import (
    DemoManifest,
    StepRecord,
    load_manifest,
    save_manifest,
    session_exists,
)


def _manifest(session_id="demo-test1") -> DemoManifest:
    return DemoManifest(
        session_id=session_id,
        sensor_id=session_id,
        backend_url="http://127.0.0.1:8000",
        seed=42,
        interval_seconds=1,
        history_start="2025-09-04",
        history_end="2025-12-31",
        start_date="2026-01-01",
        days=5,
        end_date="2026-01-05",
        history_rows=120,
        contract={
            "horizon_days": 3,
            "contract_version": 1,
            "pipeline_version": "controlled_daily_v3",
        },
    )


def test_save_and_load_roundtrip(tmp_path):
    manifest = _manifest()
    save_manifest(manifest, tmp_path)

    loaded = load_manifest(tmp_path, manifest.session_id)

    assert loaded.session_id == manifest.session_id
    assert loaded.sensor_id == manifest.sensor_id
    assert loaded.history_rows == 120
    assert loaded.contract == manifest.contract
    assert loaded.status == "prepared"


def test_save_increments_revision_each_time(tmp_path):
    manifest = _manifest()
    save_manifest(manifest, tmp_path)
    assert manifest.revision == 1

    save_manifest(manifest, tmp_path)
    assert manifest.revision == 2

    loaded = load_manifest(tmp_path, manifest.session_id)
    assert loaded.revision == 2


def test_step_records_roundtrip(tmp_path):
    manifest = _manifest()
    manifest.steps["2026-01-01"] = StepRecord(
        date="2026-01-01",
        phase="completed",
        payload={"timestamp": "2026-01-01T00:00:00"},
        payload_hash="abc123",
    )
    save_manifest(manifest, tmp_path)

    loaded = load_manifest(tmp_path, manifest.session_id)

    assert loaded.steps["2026-01-01"].phase == "completed"
    assert loaded.steps["2026-01-01"].payload_hash == "abc123"


def test_session_exists(tmp_path):
    manifest = _manifest("demo-exists")
    assert session_exists(tmp_path, manifest.session_id) is False

    save_manifest(manifest, tmp_path)

    assert session_exists(tmp_path, manifest.session_id) is True


def test_load_missing_session_raises(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path, "demo-does-not-exist")


def test_no_leftover_tmp_file_after_save(tmp_path):
    manifest = _manifest("demo-atomic")
    path = save_manifest(manifest, tmp_path)

    tmp_files = list(path.parent.glob("*.tmp-*"))
    assert tmp_files == []
