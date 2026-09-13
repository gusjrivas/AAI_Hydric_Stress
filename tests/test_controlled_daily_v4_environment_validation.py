"""Hallazgo H-04: validación previa del entorno.

`validate_environment` debe abortar en modo científico ANTES del primer
ajuste ante Python incompatible, un paquete ausente o de versión distinta a
la fijada en `docker/experiment-v4/constraints.txt`/el manifiesto -- nunca
declara un entorno válido sin haberlo contrastado.
"""

from __future__ import annotations

from experiment_runner.controlled_daily_v4.cli import main, normative_deviations
from experiment_runner.controlled_daily_v4.config import (
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
)
from experiment_runner.controlled_daily_v4.environment import (
    capture_environment,
    validate_environment,
)
from experiment_runner.controlled_daily_v4.manifest_reference import EnvironmentReference
from tests.controlled_daily_v4_fixtures import write_synthetic_pergamino_csv_pair


def _reference_matching_current_environment() -> EnvironmentReference:
    env = capture_environment()
    display_to_module = {
        "numpy": "numpy",
        "pandas": "pandas",
        "scipy": "scipy",
        "scikit-learn": "sklearn",
        "pyarrow": "pyarrow",
        "joblib": "joblib",
        "threadpoolctl": "threadpoolctl",
    }
    packages = {module: env["packages"][display] for display, module in display_to_module.items()}
    return EnvironmentReference(python_version=env["python_version"], packages=packages)


def test_compatible_environment_passes_validation():
    env = capture_environment()
    reference = _reference_matching_current_environment()
    report = validate_environment(env, reference)
    assert report.ok, report.issues


def test_incompatible_python_version_is_rejected():
    env = capture_environment()
    reference = _reference_matching_current_environment()
    wrong_reference = EnvironmentReference(python_version="1.2.3", packages=reference.packages)
    report = validate_environment(env, wrong_reference)
    assert not report.ok
    assert any("Python" in issue for issue in report.issues)


def test_incompatible_package_version_is_rejected():
    env = capture_environment()
    reference = _reference_matching_current_environment()
    tampered_packages = dict(reference.packages)
    tampered_packages["sklearn"] = "0.0.1"
    wrong_reference = EnvironmentReference(
        python_version=reference.python_version, packages=tampered_packages
    )
    report = validate_environment(env, wrong_reference)
    assert not report.ok
    assert any("scikit-learn" in issue for issue in report.issues)


def test_missing_package_is_rejected():
    """Reproduce la comprobación externa: PyArrow ausente debe rechazar en
    modo científico, no pasar con `[]`."""
    env = capture_environment()
    reference = _reference_matching_current_environment()
    env_without_pyarrow = {
        **env,
        "packages": {**env["packages"], "pyarrow": "not_installed"},
    }
    report = validate_environment(env_without_pyarrow, reference)
    assert not report.ok
    assert any("pyarrow" in issue for issue in report.issues)


def test_cli_scientific_mode_aborts_before_training_when_environment_is_incompatible(
    tmp_path, monkeypatch
):
    """En modo científico, un entorno incompatible debe abortar con un
    código de salida dedicado, sin llegar siquiera a importar `run_stage_a`
    -- prueba directa de que no se entrenó nada (hallazgo H-04)."""
    import experiment_runner.controlled_daily_v4.cli as cli_module
    from experiment_runner.controlled_daily_v4.environment import EnvironmentValidationReport
    from experiment_runner.controlled_daily_v4.provenance import ProvenanceReport

    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=30, seed=1)

    def _ok_provenance(*_args, **_kwargs):
        return ProvenanceReport(era5_path=str(era5), nasa_power_path=str(nasa), mode="scientific")

    def _failing_environment(*_args, **_kwargs):
        return EnvironmentValidationReport(issues=["forzado por el test: entorno incompatible"])

    monkeypatch.setattr(cli_module, "validate_pergamino_provenance", _ok_provenance)
    monkeypatch.setattr(cli_module, "validate_environment", _failing_environment)

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
        ]
    )
    assert exit_code == 4
    assert not output_dir.exists(), "no debe escribirse ningún artefacto sin entrenar"


def test_cli_synthetic_mode_does_not_block_on_an_incompatible_environment(tmp_path, monkeypatch):
    """El gate de entorno es exclusivo del modo científico: en modo
    sintético un entorno incompatible no impide continuar (queda registrado
    como desviación no normativa, nunca oculto)."""
    import experiment_runner.controlled_daily_v4.cli as cli_module
    from experiment_runner.controlled_daily_v4.environment import EnvironmentValidationReport

    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=200, seed=1)

    def _failing_environment(*_args, **_kwargs):
        return EnvironmentValidationReport(issues=["forzado por el test: entorno incompatible"])

    monkeypatch.setattr(cli_module, "validate_environment", _failing_environment)

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
            "--bootstrap-replicas",
            "10",
        ]
    )
    assert exit_code == 0
    import json

    resolved = json.loads((output_dir / "resolved_config.json").read_text(encoding="utf-8"))
    assert "environment" in resolved["normative_deviations"]
    assert resolved["scientific_run"] is False


def test_normative_run_requires_environment_ok_and_scientific_mode():
    assert (
        normative_deviations(
            seed=20250109,
            bootstrap_replicas=5000,
            input_mode=INPUT_MODE_SCIENTIFIC,
            environment_ok=True,
        )
        == []
    )
    assert "environment" in normative_deviations(
        seed=20250109,
        bootstrap_replicas=5000,
        input_mode=INPUT_MODE_SCIENTIFIC,
        environment_ok=False,
    )
    assert "input_mode" in normative_deviations(
        seed=20250109,
        bootstrap_replicas=5000,
        input_mode=INPUT_MODE_SYNTHETIC,
        environment_ok=True,
    )
