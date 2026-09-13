from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from experiment_runner.controlled_daily_v4.cli import main
from tests.controlled_daily_v4_fixtures import (
    drop_nasa_power_column,
    write_synthetic_pergamino_csv_pair,
)


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
            "--input-mode",
            "synthetic",
        ]
    )
    assert exit_code == 0
    assert not output_dir.exists()
    captured = capsys.readouterr()
    assert "No se entrena nada" in captured.out
    assert "NO CIENTÍFICO" in captured.out


def test_cli_validate_inputs_only_defaults_to_scientific_mode_and_rejects_synthetic_fixtures(
    tmp_path,
):
    """El modo por defecto es `scientific`: nunca se degrada automáticamente
    a sintético ante un fallo de identidad (hallazgo H-01)."""
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
    assert exit_code == 3
    assert not output_dir.exists()


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
            "--input-mode",
            "synthetic",
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


class _StopAfterIngestion(RuntimeError):
    """Marca de test: la corrida se detiene apenas se invoca `run_stage_a`,
    después de que la ingesta ya ejecutó su propio recorte -- nunca se ajusta
    ningún modelo (hallazgo H-03, completado a nivel CLI)."""


def test_cli_never_aggregates_or_processes_values_outside_the_authorized_window(
    tmp_path, monkeypatch
):
    """Reproducción externa H-03 (CLI): con datos sintéticos que cubren
    fechas de A, B y C, `aggregate_era5_daily` y `replace_missing_sentinel`
    debían recibir el rango completo antes del recorte del runner -- una
    prueba instrumentada observó una media calculada para 2024-01-01 durante
    la preparación de A. Esta prueba demuestra, instrumentando esas dos
    funciones tal como las importa la CLI, que ya no reciben ninguna fila
    fuera de la ventana autorizada (más la historia causal mínima). No se
    entrena nada: `run_stage_a` se reemplaza por una marca que corta la
    ejecución apenas se invoca, después de que la ingesta ya se recortó."""
    import experiment_runner.controlled_daily_v4.ingestion as ingestion_module
    import experiment_runner.controlled_daily_v4.stage_a_runner as stage_a_runner_module
    from experiment_runner.controlled_daily_v4.config import STAGE_A_BOUNDS
    from experiment_runner.controlled_daily_v4.features import compute_stage_window_bounds

    # 2015-01-01 .. 2025-12-31 (~4018 días): cubre A, B y C, igual que el
    # rango real del manifiesto de Pergamino.
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=4018, seed=42)
    window_start, window_end = compute_stage_window_bounds(STAGE_A_BOUNDS)

    original_aggregate = ingestion_module.aggregate_era5_daily
    original_replace = ingestion_module.replace_missing_sentinel
    seen_era5_ranges: list[tuple] = []
    seen_nasa_ranges: list[tuple] = []

    def spy_aggregate(df):
        seen_era5_ranges.append((df["time"].min(), df["time"].max()))
        return original_aggregate(df)

    def spy_replace(df):
        seen_nasa_ranges.append((df.index.min(), df.index.max()))
        return original_replace(df)

    monkeypatch.setattr(ingestion_module, "aggregate_era5_daily", spy_aggregate)
    monkeypatch.setattr(ingestion_module, "replace_missing_sentinel", spy_replace)

    def _stop(*_args, **_kwargs):
        raise _StopAfterIngestion

    monkeypatch.setattr(stage_a_runner_module, "run_stage_a", _stop)

    with pytest.raises(_StopAfterIngestion):
        main(
            [
                "--stage",
                "A",
                "--era5-csv",
                str(era5),
                "--nasa-power-csv",
                str(nasa),
                "--output-dir",
                str(tmp_path / "out"),
                "--input-mode",
                "synthetic",
            ]
        )

    assert seen_era5_ranges, "aggregate_era5_daily debe haberse invocado"
    assert seen_nasa_ranges, "replace_missing_sentinel debe haberse invocado"
    era5_min, era5_max = seen_era5_ranges[0]
    nasa_min, nasa_max = seen_nasa_ranges[0]
    assert era5_min.date() >= window_start, "aggregate_era5_daily recibió filas anteriores a A"
    assert era5_max.date() <= window_end, "aggregate_era5_daily recibió filas de B/C"
    assert nasa_min.date() >= window_start, "replace_missing_sentinel recibió filas anteriores a A"
    assert nasa_max.date() <= window_end, "replace_missing_sentinel recibió filas de B/C"


def test_cli_scientific_mode_still_rejects_any_identity_change_after_isolation_fix(tmp_path):
    """El recorte de aislamiento (H-03) no debilita H-01: la ruta científica
    sigue rechazando cualquier CSV cuya identidad no coincida con la
    congelada en el manifiesto."""
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=30, seed=1)
    exit_code = main(
        [
            "--stage",
            "A",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(tmp_path / "out"),
            "--validate-inputs-only",
        ]
    )
    assert exit_code == 3


def test_cli_reports_a_controlled_error_when_a_required_nasa_column_is_missing(tmp_path, capsys):
    """La ausencia de una columna requerida (RH2M) debía producir un
    `KeyError` sin manejar dentro de `load_nasa_power_daily_raw`, antes de
    que `provenance.py` pudiera reportar el diagnóstico de columnas
    faltantes. Ahora termina con el código de entrada inválida, sin
    traceback sin manejar y sin entrenar nada."""
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=30, seed=21)
    drop_nasa_power_column(nasa, "RH2M")

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
            "--input-mode",
            "synthetic",
        ]
    )
    assert exit_code == 3
    assert not output_dir.exists()
    captured = capsys.readouterr()
    assert "RH2M" in captured.err


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
