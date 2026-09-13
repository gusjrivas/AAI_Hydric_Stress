"""Referencia de identidad y entorno leída del manifiesto de provenance versionado.

Extractor deliberadamente acotado (no un parser YAML general): lee, por
posición de bloque, exactamente los campos que la ruta científica necesita
contrastar (hallazgos H-01 y H-04) directamente desde
`docs/research/controlled-daily-v4-external-pergamino-manifest.yaml` y desde
`docker/experiment-v4/constraints.txt`. Nunca se copian estos valores a mano
en otro módulo: cualquier cambio en el manifiesto o en las constraints se
refleja automáticamente aquí, evitando listas manuales divergentes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_PATH = (
    _REPO_ROOT / "docs" / "research" / "controlled-daily-v4-external-pergamino-manifest.yaml"
)
DEFAULT_CONSTRAINTS_PATH = _REPO_ROOT / "docker" / "experiment-v4" / "constraints.txt"


class ManifestReferenceError(RuntimeError):
    """El manifiesto o las constraints versionadas no tienen la forma
    esperada: no se puede derivar una referencia confiable de ellos."""


def _extract_block(text: str, start_marker: str, end_markers: tuple[str, ...]) -> str:
    start = text.find(start_marker)
    if start == -1:
        raise ManifestReferenceError(f"No se encontró el bloque '{start_marker}' en el manifiesto")
    start += len(start_marker)
    end = len(text)
    for marker in end_markers:
        pos = text.find(marker, start)
        if pos != -1:
            end = min(end, pos)
    return text[start:end]


def _extract_scalar(block: str, key: str) -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*\"?([^\"\n]+?)\"?\s*$", block, re.MULTILINE)
    if not match:
        raise ManifestReferenceError(f"No se encontró el campo '{key}' en el bloque del manifiesto")
    return match.group(1).strip()


@dataclass(frozen=True)
class ProviderIdentityReference:
    sha256: str
    size_bytes: int
    latitude: float
    longitude: float
    elevation_m: float


@dataclass(frozen=True)
class ManifestIdentityReference:
    era5: ProviderIdentityReference
    nasa_power: ProviderIdentityReference


@dataclass(frozen=True)
class EnvironmentReference:
    python_version: str
    packages: dict[str, str]


def load_manifest_identity_reference(
    path: str | Path = DEFAULT_MANIFEST_PATH,
) -> ManifestIdentityReference:
    """Referencia de identidad por proveedor, leída del manifiesto versionado.

    Nunca se calcula a partir de los CSV recibidos en la corrida: proviene
    exclusivamente de este documento versionado, congelado por separado
    (hallazgo H-01)."""
    text = Path(path).read_text(encoding="utf-8")

    coords_block = _extract_block(text, "coordinates:\n", ("sources:\n",))
    era5_coords_block = _extract_block(
        coords_block, "returned_era5_land:\n", ("returned_nasa_power:\n",)
    )
    nasa_coords_block = _extract_block(coords_block, "returned_nasa_power:\n", ())

    era5_source_block = _extract_block(text, "  era5_land:\n", ("  nasa_power:\n",))
    nasa_source_block = _extract_block(text, "  nasa_power:\n", ("aggregation_rules:\n",))

    era5 = ProviderIdentityReference(
        sha256=_extract_scalar(era5_source_block, "sha256"),
        size_bytes=int(_extract_scalar(era5_source_block, "size_bytes")),
        latitude=float(_extract_scalar(era5_coords_block, "latitude")),
        longitude=float(_extract_scalar(era5_coords_block, "longitude")),
        elevation_m=float(_extract_scalar(era5_coords_block, "elevation_m")),
    )
    nasa_power = ProviderIdentityReference(
        sha256=_extract_scalar(nasa_source_block, "sha256"),
        size_bytes=int(_extract_scalar(nasa_source_block, "size_bytes")),
        latitude=float(_extract_scalar(nasa_coords_block, "latitude")),
        longitude=float(_extract_scalar(nasa_coords_block, "longitude")),
        elevation_m=float(_extract_scalar(nasa_coords_block, "elevation_m")),
    )
    return ManifestIdentityReference(era5=era5, nasa_power=nasa_power)


_PACKAGE_TO_MODULE = {
    "numpy": "numpy",
    "scipy": "scipy",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "scikit-learn": "sklearn",
    "joblib": "joblib",
    "threadpoolctl": "threadpoolctl",
}

_PYTHON_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")


def load_environment_reference(
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    constraints_path: str | Path = DEFAULT_CONSTRAINTS_PATH,
) -> EnvironmentReference:
    """Versiones exactas esperadas del entorno experimental, leídas de
    `constraints.txt` (paquetes) y del manifiesto (versión de Python) —
    nunca declaradas a mano en el código (hallazgo H-04)."""
    manifest_text = Path(manifest_path).read_text(encoding="utf-8")
    environment_block = _extract_block(manifest_text, "environment:\n", ("repository_state:\n",))
    python_version_field = _extract_scalar(environment_block, "python_version")
    match = _PYTHON_VERSION_RE.search(python_version_field)
    if not match:
        raise ManifestReferenceError(
            f"No se pudo extraer una versión de Python de '{python_version_field}'"
        )
    python_version = match.group(1)

    constraints_text = Path(constraints_path).read_text(encoding="utf-8")
    pinned: dict[str, str] = {}
    for line in constraints_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "==" not in stripped:
            continue
        name, _, version = stripped.partition("==")
        pinned[name.strip().lower()] = version.strip()

    packages: dict[str, str] = {}
    for pin_name, module_name in _PACKAGE_TO_MODULE.items():
        if pin_name not in pinned:
            raise ManifestReferenceError(
                f"'{pin_name}' no está fijado en {constraints_path}; no se puede validar "
                "el entorno científico contra una referencia incompleta"
            )
        packages[module_name] = pinned[pin_name]

    return EnvironmentReference(python_version=python_version, packages=packages)
