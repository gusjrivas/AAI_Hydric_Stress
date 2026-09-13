"""Captura y validación real del entorno de ejecución (protocolo, sección 15).

Registra las versiones efectivamente importadas en la corrida, leídas de los
paquetes instalados y nunca declaradas a mano: el artefacto de entorno debe
poder contrastarse contra `docker/experiment-v4/constraints.txt` y contra la
sección `environment` del manifiesto de provenance.

La validación (hallazgo H-04) se ejecuta y decide ANTES del primer ajuste de
un modelo: `capture_environment()` se invoca y, en modo científico,
`validate_environment()` puede abortar la corrida antes de que
`run_stage_a` reciba ningún dato — nunca después de entrenar.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

from experiment_runner.controlled_daily_v4.manifest_reference import (
    DEFAULT_CONSTRAINTS_PATH,
    DEFAULT_MANIFEST_PATH,
    EnvironmentReference,
    load_environment_reference,
)

TRACKED_PACKAGES: tuple[tuple[str, str], ...] = (
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("scipy", "scipy"),
    ("scikit-learn", "sklearn"),
    ("pyarrow", "pyarrow"),
    ("joblib", "joblib"),
    ("threadpoolctl", "threadpoolctl"),
)

UNAVAILABLE = "not_installed"


def _package_version(module_name: str) -> str:
    try:
        module = import_module(module_name)
    except ImportError:
        return UNAVAILABLE
    return str(getattr(module, "__version__", UNAVAILABLE))


def capture_environment() -> dict[str, Any]:
    """Entorno de la corrida actual: versión de Python, plataforma y versiones
    exactas de las dependencias directas relevantes del protocolo."""
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor_architecture": platform.architecture()[0],
        "packages": {display: _package_version(module) for display, module in TRACKED_PACKAGES},
    }


@dataclass
class EnvironmentValidationReport:
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0


def validate_environment(
    captured: dict[str, Any],
    reference: EnvironmentReference | None = None,
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    constraints_path: str | Path = DEFAULT_CONSTRAINTS_PATH,
) -> EnvironmentValidationReport:
    """Contrasta el entorno capturado contra la referencia versionada de
    `constraints.txt`/manifiesto. Exclusiva del modo científico: nunca se
    invoca (ni bloquea nada) en modo sintético (hallazgo H-04)."""
    if reference is None:
        reference = load_environment_reference(manifest_path, constraints_path)

    report = EnvironmentValidationReport()
    if captured.get("python_version") != reference.python_version:
        report.issues.append(
            f"Python {captured.get('python_version')} no coincide con la versión fijada "
            f"{reference.python_version}"
        )

    captured_packages = captured.get("packages", {})
    module_to_display = {module: display for display, module in TRACKED_PACKAGES}
    for module_name, expected_version in reference.packages.items():
        display_name = module_to_display.get(module_name, module_name)
        found_version = captured_packages.get(display_name, UNAVAILABLE)
        if found_version == UNAVAILABLE:
            report.issues.append(
                f"'{display_name}' no está instalado (se esperaba {expected_version})"
            )
        elif found_version != expected_version:
            report.issues.append(
                f"'{display_name}' {found_version} no coincide con la versión fijada "
                f"{expected_version}"
            )
    return report
