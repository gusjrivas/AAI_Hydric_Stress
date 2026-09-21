"""Smoke test for `scripts/run_operational_manifest_v3.py`: exercises the
CLI wiring itself (argument parsing, manifest identity verification,
dataset loading, isolated persistence) end to end, against a synthetic
fixture written to a throwaway temporary directory only.

Never touches `data/melchor_romero_2024_consolidado.parquet`, `config/`,
or any historical run directory.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from data_ingestion.storage import load_dataset_snapshot, save_dataset
from predictive_modeling.calibration_manifest import freeze_calibration_manifest
from tests.test_operational_run import _synthetic_frame, _synthetic_ready_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_operational_manifest_v3.py"


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def synthetic_run_inputs(tmp_path):
    df = _synthetic_frame()
    data_dir = tmp_path / "data"
    dataset_name = "synthetic-cli-smoke-fixture"
    save_dataset(dataset_name, df, data_dir=data_dir)
    dataset_sha256 = load_dataset_snapshot(dataset_name, data_dir=data_dir).dataset_sha256
    manifest = _synthetic_ready_manifest(dataset_sha256)
    manifest_path = tmp_path / "manifest.json"
    freeze_calibration_manifest(manifest, manifest_path)

    return {
        "manifest_path": manifest_path,
        "data_dir": data_dir,
        "dataset_name": dataset_name,
        "output_dir": tmp_path / "run-output",
    }


def test_cli_writes_isolated_artifacts_for_a_synthetic_manifest(synthetic_run_inputs):
    result = _run_cli(
        "--manifest",
        str(synthetic_run_inputs["manifest_path"]),
        "--dataset",
        synthetic_run_inputs["dataset_name"],
        "--data-dir",
        str(synthetic_run_inputs["data_dir"]),
        "--output-dir",
        str(synthetic_run_inputs["output_dir"]),
        "--run-id",
        "cli-smoke-test",
    )

    assert result.returncode == 0, result.stderr
    output_dir = synthetic_run_inputs["output_dir"]
    assert (output_dir / "run_metadata.json").exists()
    assert (output_dir / "report.md").exists()
    for horizon in (1, 2, 3):
        assert (output_dir / f"horizon_{horizon}" / "status.json").exists()


def test_cli_refuses_a_second_run_into_the_same_output_dir(synthetic_run_inputs):
    first = _run_cli(
        "--manifest",
        str(synthetic_run_inputs["manifest_path"]),
        "--dataset",
        synthetic_run_inputs["dataset_name"],
        "--data-dir",
        str(synthetic_run_inputs["data_dir"]),
        "--output-dir",
        str(synthetic_run_inputs["output_dir"]),
        "--run-id",
        "cli-smoke-test",
    )
    assert first.returncode == 0, first.stderr

    second = _run_cli(
        "--manifest",
        str(synthetic_run_inputs["manifest_path"]),
        "--dataset",
        synthetic_run_inputs["dataset_name"],
        "--data-dir",
        str(synthetic_run_inputs["data_dir"]),
        "--output-dir",
        str(synthetic_run_inputs["output_dir"]),
        "--run-id",
        "cli-smoke-test-again",
    )
    assert second.returncode != 0
    assert (
        "no se sobrescribe" in second.stderr.lower()
        or "no se sobrescribe" in str(second.stdout).lower()
    )


def test_cli_refuses_real_dataset_without_explicit_flag(tmp_path):
    df = _synthetic_frame()
    data_dir = tmp_path / "data"
    dataset_name = "not-actually-real-but-declared-real-fixture"
    save_dataset(dataset_name, df, data_dir=data_dir)
    dataset_sha256 = load_dataset_snapshot(dataset_name, data_dir=data_dir).dataset_sha256
    manifest = _synthetic_ready_manifest(dataset_sha256)
    manifest["dataset"] = {
        **manifest["dataset"],
        "source_kind": "real",
        "synthetic_fixture": False,
    }
    manifest_path = tmp_path / "manifest.json"
    freeze_calibration_manifest(manifest, manifest_path)

    result = _run_cli(
        "--manifest",
        str(manifest_path),
        "--dataset",
        dataset_name,
        "--data-dir",
        str(data_dir),
        "--output-dir",
        str(tmp_path / "run-output"),
        "--run-id",
        "should-not-run",
    )

    assert result.returncode != 0
    assert "--allow-real-data" in result.stderr
    assert not (tmp_path / "run-output").exists()
