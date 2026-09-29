"""F01: `scripts/refresh_melchor_romero_historical_demo_readings.py`.

Exercises only the readings refresh (fast: reads the real, already-committed
Melchor Romero dataset and re-derives imputation flags -- no model
training), never `run_demo`/bundle export. All I/O happens under `tmp_path`,
never the repository's own `data/` directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from refresh_melchor_romero_historical_demo_readings import (  # noqa: E402
    RefreshError,
    refresh_readings,
)

from data_ingestion.sensor_naming import dataset_name_for  # noqa: E402
from data_ingestion.storage import load_dataset, save_dataset  # noqa: E402
from experiment_runner.melchor_romero_historical_demo_runner import (  # noqa: E402
    build_daily_frame_from_repo_dataset,
)

SENSOR_ID = "melchor-romero-demo"


def _write_legacy_readings(data_dir: Path, *, through_row: int = 40) -> None:
    """Simulates a readings file that lost/never had the per-variable
    `_imputado` columns (the F01 symptom), truncated to the first
    `through_row` rows of the real dataset -- mirrors what
    `prepare_melchor_romero_historical_demo.py` writes for a partial
    emission, minus the flag columns."""
    frame, _ = build_daily_frame_from_repo_dataset()
    legacy = frame.iloc[:through_row][
        ["timestamp", "soil_moisture", "relative_humidity", "solar_radiation"]
    ].copy()
    legacy["origen"] = "real"
    save_dataset(dataset_name_for(SENSOR_ID), legacy, data_dir=data_dir)


def test_refresh_adds_correct_imputation_flags_verified_against_the_source(tmp_path):
    _write_legacy_readings(tmp_path)

    result = refresh_readings(sensor_id=SENSOR_ID, data_dir=tmp_path)
    assert result["rows_verified"] == 40
    assert result["imputation_flag_columns_updated"] == 3

    updated = load_dataset(dataset_name_for(SENSOR_ID), data_dir=tmp_path)
    fresh_frame, _ = build_daily_frame_from_repo_dataset()
    fresh_by_date = fresh_frame.set_index(fresh_frame["timestamp"])

    assert "soil_moisture_imputado" in updated.columns
    for _, row in updated.iterrows():
        expected = fresh_by_date.loc[row["timestamp"]]
        assert bool(row["soil_moisture_imputado"]) == bool(expected["soil_moisture_imputado"])
        assert bool(row["relative_humidity_imputado"]) == bool(
            expected["relative_humidity_imputado"]
        )
        assert bool(row["solar_radiation_imputado"]) == bool(expected["solar_radiation_imputado"])
    # Dataset-level provenance untouched: this real dataset stays "real".
    assert (updated["origen"] == "real").all()


def test_refresh_is_idempotent(tmp_path):
    _write_legacy_readings(tmp_path)
    refresh_readings(sensor_id=SENSOR_ID, data_dir=tmp_path)
    first_pass = load_dataset(dataset_name_for(SENSOR_ID), data_dir=tmp_path)

    second_result = refresh_readings(sensor_id=SENSOR_ID, data_dir=tmp_path)
    assert second_result["imputation_flag_columns_updated"] == 0
    second_pass = load_dataset(dataset_name_for(SENSOR_ID), data_dir=tmp_path)

    assert first_pass.equals(second_pass)


def test_refresh_refuses_and_writes_nothing_when_a_value_does_not_match_the_source(tmp_path):
    _write_legacy_readings(tmp_path)
    tampered = load_dataset(dataset_name_for(SENSOR_ID), data_dir=tmp_path)
    tampered.loc[0, "soil_moisture"] = 999.0
    save_dataset(dataset_name_for(SENSOR_ID), tampered, data_dir=tmp_path)
    before = load_dataset(dataset_name_for(SENSOR_ID), data_dir=tmp_path)

    with pytest.raises(RefreshError, match="no coincide con la fuente"):
        refresh_readings(sensor_id=SENSOR_ID, data_dir=tmp_path)

    after = load_dataset(dataset_name_for(SENSOR_ID), data_dir=tmp_path)
    assert before.equals(after)


def test_refresh_aborts_without_overwriting_a_concurrent_correction(tmp_path, monkeypatch):
    """Deterministically intercalates a concurrent writer's correction
    BETWEEN this script's read/verify step and its final write, all inside
    a single process/thread (no real concurrency needed): the script reads
    and verifies against the source, then -- while still holding the lock,
    just before it re-checks and writes -- a monkeypatched hook writes
    directly to the readings file, bypassing the lock the same way a
    process with a stale, pre-acquired snapshot never could once this
    script's fix wraps read+verify+write under one lock. This simulates
    exactly the race the finding described (another writer's save landing
    between read and write) and asserts the script aborts, preserving the
    concurrent correction instead of clobbering it."""
    import experiment_runner.melchor_romero_historical_demo_runner as demo_runner_module

    _write_legacy_readings(tmp_path)
    name = dataset_name_for(SENSOR_ID)

    original_builder = build_daily_frame_from_repo_dataset
    concurrent_correction = load_dataset(name, data_dir=tmp_path).copy()
    concurrent_correction.loc[0, "relative_humidity"] = -1.0  # sentinel

    def _intercalate_then_build():
        # Runs after the script's first (pre-write) snapshot was already
        # captured and verified, and before its final re-check/write --
        # exactly where a concurrent writer's save could land in the bug
        # this fixes. Writes directly (not through `save_dataset`, which
        # would deadlock on the non-reentrant lock this test's caller
        # already holds) to simulate a writer with independent access to
        # the file.
        from data_ingestion.storage import atomic_write_bytes

        buffer_path = tmp_path / f"{name}.parquet"
        import io as _io

        buffer = _io.BytesIO()
        concurrent_correction.to_parquet(buffer, index=False)
        atomic_write_bytes(buffer_path, buffer.getvalue())
        return original_builder()

    monkeypatch.setattr(
        demo_runner_module, "build_daily_frame_from_repo_dataset", _intercalate_then_build
    )

    with pytest.raises(RefreshError, match="cambió concurrentemente"):
        refresh_readings(sensor_id=SENSOR_ID, data_dir=tmp_path)

    after = load_dataset(name, data_dir=tmp_path)
    assert after.loc[0, "relative_humidity"] == -1.0
    assert after.equals(concurrent_correction)


def test_refresh_refuses_a_date_absent_from_the_current_source(tmp_path):
    frame, _ = build_daily_frame_from_repo_dataset()
    legacy = frame.iloc[:5][
        ["timestamp", "soil_moisture", "relative_humidity", "solar_radiation"]
    ].copy()
    legacy["origen"] = "real"

    extra_row = legacy.iloc[[0]].copy()
    extra_row["timestamp"] = pd.Timestamp("1999-01-01")
    legacy = pd.concat([legacy, extra_row], ignore_index=True)
    save_dataset(dataset_name_for(SENSOR_ID), legacy, data_dir=tmp_path)

    with pytest.raises(RefreshError, match="no existen en la fuente"):
        refresh_readings(sensor_id=SENSOR_ID, data_dir=tmp_path)
