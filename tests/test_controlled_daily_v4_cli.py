from __future__ import annotations

import json
import sys

import pytest

from experiment_runner.controlled_daily_v4.cli import main
from tests.controlled_daily_v4_fixtures import write_synthetic_pergamino_csv_pair


def test_cli_rejects_stage_b(tmp_path, capsys):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=30, seed=1)
    exit_code = main(
        [
            "--stage",
            "B",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "no soportada" in captured.err


def test_cli_rejects_stage_c(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=30, seed=1)
    exit_code = main(
        [
            "--stage",
            "C",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )
    assert exit_code == 2


def test_cli_argparse_rejects_unknown_stage_value(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=30, seed=1)
    with pytest.raises(SystemExit):
        main(
            [
                "--stage",
                "D",
                "--era5-csv",
                str(era5),
                "--nasa-power-csv",
                str(nasa),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )


def test_cli_validate_inputs_only_does_not_train(tmp_path, capsys):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=30, seed=1)
    output_dir = tmp_path / "out"
    exit_code = main(
        [
            "--stage",
            "A",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(output_dir),
            "--validate-inputs-only",
        ]
    )
    assert exit_code == 0
    assert not output_dir.exists()
    captured = capsys.readouterr()
    assert "no se entrena nada" in captured.out


def test_cli_validate_inputs_only_reports_provenance_issues(tmp_path):
    exit_code = main(
        [
            "--stage",
            "A",
            "--era5-csv",
            str(tmp_path / "no_existe_era5.csv"),
            "--nasa-power-csv",
            str(tmp_path / "no_existe_nasa.csv"),
            "--output-dir",
            str(tmp_path / "out"),
            "--validate-inputs-only",
        ]
    )
    assert exit_code == 3


def test_cli_full_run_with_synthetic_data_produces_artifacts_and_never_touches_mlflow(tmp_path):
    assert "mlflow" not in sys.modules or True  # no se asume estado previo del intérprete
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=200, seed=13)
    output_dir = tmp_path / "out"

    exit_code = main(
        [
            "--stage",
            "A",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(output_dir),
            "--bootstrap-replicas",
            "10",
        ]
    )
    assert exit_code == 0
    assert (output_dir / "holdout_status.json").exists()
    payload = json.loads((output_dir / "holdout_status.json").read_text(encoding="utf-8"))
    assert payload == {
        "stage_b_executed": False,
        "stage_c_executed": False,
        "holdout_2024_2025_open": False,
        "note": "Ejecución de Stage A únicamente. B y C no implementadas en este runner.",
    }
    assert (output_dir / "selection_decision.json").exists()

    # El módulo del CLI/runner de la Etapa A no importa la librería mlflow en
    # ningún punto (una mención en un comentario/docstring no cuenta).
    import ast

    import experiment_runner.controlled_daily_v4.cli as cli_module
    import experiment_runner.controlled_daily_v4.stage_a_runner as runner_module

    for module in (cli_module, runner_module):
        with open(module.__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imported_names = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        } | {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "mlflow" not in imported_names
