"""Captura real del entorno de ejecución (protocolo, sección 15).

Registra las versiones efectivamente importadas en la corrida, leídas de los
paquetes instalados y nunca declaradas a mano: el artefacto de entorno debe
poder contrastarse contra `docker/experiment-v4/constraints.txt` y contra la
sección `environment` del manifiesto de provenance.
"""

from __future__ import annotations

import platform
import sys
from importlib import import_module
from typing import Any

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
        "packages": {name: _package_version(module) for name, module in TRACKED_PACKAGES},
    }
