from __future__ import annotations

import json
import sys
from pathlib import Path

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
    # No se asume estado previo del intérprete: se compara qué módulos aparecen
    # como consecuencia de esta corrida.
    modules_before = set(sys.modules)
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

    # La corrida completa no importó mlflow en ningún momento.
    imported_by_the_run = set(sys.modules) - modules_before
    assert not [m for m in imported_by_the_run if m.split(".")[0] == "mlflow"]


def _imported_top_level_names(path) -> set[str]:
    import ast

    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


TRACKING_CALL_ATTRIBUTES = frozenset(
    {
        "set_tracking_uri",
        "set_registry_uri",
        "start_run",
        "log_metric",
        "log_metrics",
        "log_param",
        "log_params",
        "log_artifact",
        "log_model",
        "register_model",
        "autolog",
    }
)


def test_no_module_of_the_stage_a_package_imports_mlflow():
    """Barrido AST sobre TODO el subpaquete y sus tests, no solo el CLI y el
    runner: una mención en un comentario o docstring no cuenta como import."""
    import experiment_runner.controlled_daily_v4 as package

    package_dir = Path(package.__file__).parent
    modules = sorted(package_dir.glob("*.py"))
    assert len(modules) >= 15, "el barrido debe cubrir el subpaquete completo"

    offenders = [p.name for p in modules if "mlflow" in _imported_top_level_names(p)]
    assert offenders == []


def test_no_test_module_of_the_stage_a_suite_imports_mlflow():
    tests_dir = Path(__file__).parent
    modules = sorted(tests_dir.glob("*controlled_daily_v4*.py"))
    assert len(modules) >= 14, "el barrido debe cubrir la suite dirigida completa"

    offenders = [p.name for p in modules if "mlflow" in _imported_top_level_names(p)]
    assert offenders == []


def test_no_module_of_the_stage_a_package_calls_a_tracking_api():
    """Ninguna ruta del runner puede registrar runs ni modelos, ni fijar un
    tracking URI hacia `localhost:5000` o el MLflow compartido."""
    import ast

    import experiment_runner.controlled_daily_v4 as package

    package_dir = Path(package.__file__).parent
    offenders: list[str] = []
    for path in sorted(package_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in TRACKING_CALL_ATTRIBUTES:
                offenders.append(f"{path.name}:{node.lineno} -> {node.attr}")
    assert offenders == []


def test_no_module_of_the_stage_a_package_hardcodes_a_tracking_endpoint():
    import ast

    import experiment_runner.controlled_daily_v4 as package

    package_dir = Path(package.__file__).parent
    offenders: list[str] = []
    for path in sorted(package_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                lowered = node.value.lower()
                if "localhost:5000" in lowered or "127.0.0.1:5000" in lowered:
                    offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []
