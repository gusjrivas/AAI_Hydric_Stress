"""Validación de identidad y provenance de los dos CSV crudos de Pergamino.

Exclusivamente lectura: nunca modifica los archivos.

Separación exigida por el protocolo (sección 16) y por el hallazgo H-03:
esta validación es *estructural* únicamente — existencia, nombre, hash
físico completo, encabezados, columnas, timezone declarado, coordenadas
declaradas por proveedor y cobertura de fechas. Nunca agrega, promedia,
cuenta centinelas ni analiza ningún valor de humedad/RH2M/radiación: eso es
análisis por etapa y ocurre exclusivamente en `ingestion.py`/`features.py`,
ya recortado a la ventana autorizada (`restrict_to_stage_window`). El
SHA-256 sí puede recorrer el archivo completo porque es integridad física,
no análisis de resultados (protocolo, sección 3).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from experiment_runner.controlled_daily_v4.config import (
    ALL_SOIL_MOISTURE_COLUMNS,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
    INPUT_MODES,
)
from experiment_runner.controlled_daily_v4.ingestion import (
    NASA_POWER_VARIABLE_COLUMNS,
    compute_date_alignment,
    extract_era5_daily_dates,
    load_era5_hourly_raw,
    load_nasa_power_daily_raw,
)
from experiment_runner.controlled_daily_v4.manifest_reference import (
    DEFAULT_MANIFEST_PATH,
    ManifestIdentityReference,
    ManifestReferenceError,
    load_manifest_identity_reference,
)

EXPECTED_ERA5_FILENAME = "pergamino_era5land_soil_hourly_2015_2025.csv"
EXPECTED_NASA_POWER_FILENAME = "pergamino_nasa_power_daily_2015_2025.csv"

EXPECTED_TIMEZONE = "America/Argentina/Buenos_Aires"

# Tolerancia de comparación de coordenadas por proveedor:
# 1e-4 grados equivale aproximadamente a 11,1 metros en el ecuador.
# Se aplica a cada coordenada respecto de su referencia en el manifiesto.
_COORDINATE_TOLERANCE_DEGREES = 1e-4

_NASA_DATE_RANGE_RE = re.compile(
    r"Dates \(month/day/year\):\s*(\d{2})/(\d{2})/(\d{4})\s*through\s*(\d{2})/(\d{2})/(\d{4})"
)
_NASA_LOCATION_RE = re.compile(
    r"Location:\s*latitude\s+(-?\d+(?:\.\d+)?)\s+longitude\s+(-?\d+(?:\.\d+)?)"
)


def compute_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class ProvenanceReport:
    era5_path: str
    nasa_power_path: str
    mode: str = INPUT_MODE_SCIENTIFIC
    issues: list[str] = field(default_factory=list)
    era5_sha256: str = ""
    era5_size_bytes: int = 0
    era5_n_records: int = 0
    era5_n_duplicated_timestamps: int = 0
    era5_latitude: float = 0.0
    era5_longitude: float = 0.0
    era5_timezone: str = ""
    nasa_power_sha256: str = ""
    nasa_power_size_bytes: int = 0
    nasa_power_n_records: int = 0
    nasa_power_n_duplicated_dates: int = 0
    nasa_power_declared_date_min: str | None = None
    nasa_power_declared_date_max: str | None = None
    nasa_power_declared_latitude: float | None = None
    nasa_power_declared_longitude: float | None = None
    n_dates_common: int = 0
    n_dates_only_era5: int = 0
    n_dates_only_nasa_power: int = 0

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0

    @property
    def scientific(self) -> bool:
        """Nunca `True` en modo sintético, sin importar el resultado de
        `issues`: las salidas sintéticas siempre quedan marcadas como no
        científicas (hallazgo H-01)."""
        return self.ok and self.mode == INPUT_MODE_SCIENTIFIC


def _validate_era5(
    path: Path,
    report: ProvenanceReport,
    reference: ManifestIdentityReference | None,
) -> Path | None:
    if not path.exists():
        report.issues.append(f"ERA5-Land: archivo no encontrado en {path}")
        return None

    if path.name != EXPECTED_ERA5_FILENAME:
        report.issues.append(
            f"ERA5-Land: nombre inesperado '{path.name}' (se esperaba '{EXPECTED_ERA5_FILENAME}')"
        )

    report.era5_sha256 = compute_sha256(path)
    report.era5_size_bytes = path.stat().st_size

    try:
        metadata, df = load_era5_hourly_raw(path)
    except (KeyError, ValueError) as exc:
        report.issues.append(f"ERA5-Land: metadatos de encabezado ausentes o inválidos ({exc})")
        return None

    report.era5_latitude = metadata.latitude
    report.era5_longitude = metadata.longitude
    report.era5_timezone = metadata.timezone
    if metadata.timezone != EXPECTED_TIMEZONE:
        report.issues.append(
            f"ERA5-Land: timezone inesperado '{metadata.timezone}' "
            f"(se esperaba '{EXPECTED_TIMEZONE}')"
        )

    missing_columns = [c for c in ALL_SOIL_MOISTURE_COLUMNS if c not in df.columns]
    if missing_columns:
        report.issues.append(f"ERA5-Land: columnas faltantes {missing_columns}")

    if "time" not in df.columns:
        report.issues.append("ERA5-Land: columna 'time' ausente")
        return None

    report.era5_n_records = len(df)
    n_dup = int(df["time"].duplicated().sum())
    report.era5_n_duplicated_timestamps = n_dup
    if n_dup:
        report.issues.append(f"ERA5-Land: {n_dup} timestamps duplicados")

    if reference is not None:
        if report.era5_sha256 != reference.era5.sha256:
            report.issues.append(
                f"ERA5-Land: SHA-256 no coincide con el manifiesto (esperado "
                f"{reference.era5.sha256}, obtenido {report.era5_sha256})"
            )
        if abs(metadata.latitude - reference.era5.latitude) > _COORDINATE_TOLERANCE_DEGREES:
            report.issues.append(
                f"ERA5-Land: latitud declarada {metadata.latitude} no coincide con la "
                f"referencia del manifiesto {reference.era5.latitude}"
            )
        if abs(metadata.longitude - reference.era5.longitude) > _COORDINATE_TOLERANCE_DEGREES:
            report.issues.append(
                f"ERA5-Land: longitud declarada {metadata.longitude} no coincide con la "
                f"referencia del manifiesto {reference.era5.longitude}"
            )

    # Solo fechas (estructural): nunca se agregan valores de humedad aquí
    # (hallazgo H-03) — eso ocurre exclusivamente ya recortado a la etapa.
    return extract_era5_daily_dates(df)


def _validate_nasa_power(
    path: Path,
    report: ProvenanceReport,
    reference: ManifestIdentityReference | None,
) -> Path | None:
    if not path.exists():
        report.issues.append(f"NASA POWER: archivo no encontrado en {path}")
        return None

    if path.name != EXPECTED_NASA_POWER_FILENAME:
        report.issues.append(
            f"NASA POWER: nombre inesperado '{path.name}' "
            f"(se esperaba '{EXPECTED_NASA_POWER_FILENAME}')"
        )

    report.nasa_power_sha256 = compute_sha256(path)
    report.nasa_power_size_bytes = path.stat().st_size

    try:
        meta_lines, df = load_nasa_power_daily_raw(path)
    except (StopIteration, ValueError) as exc:
        # Cubre tanto un bloque de encabezado ausente/inválido como una
        # columna requerida ausente (`load_nasa_power_daily_raw` levanta
        # `ValueError` en ambos casos, nunca un `KeyError` sin controlar).
        report.issues.append(f"NASA POWER: encabezado o columnas inválidos ({exc})")
        return None

    missing_columns = [c for c in NASA_POWER_VARIABLE_COLUMNS if c not in df.columns]
    if missing_columns:
        report.issues.append(f"NASA POWER: columnas faltantes {missing_columns}")

    report.nasa_power_n_records = len(df)
    n_dup = int(df.index.duplicated().sum())
    report.nasa_power_n_duplicated_dates = n_dup
    if n_dup:
        report.issues.append(f"NASA POWER: {n_dup} fechas duplicadas")

    declared_range_line = next((line for line in meta_lines if "Dates (" in line), None)
    if declared_range_line:
        match = _NASA_DATE_RANGE_RE.search(declared_range_line)
        if match:
            m1, d1, y1, m2, d2, y2 = match.groups()
            report.nasa_power_declared_date_min = f"{y1}-{m1}-{d1}"
            report.nasa_power_declared_date_max = f"{y2}-{m2}-{d2}"
            actual_min = str(df.index.min().date())
            actual_max = str(df.index.max().date())
            if actual_min != report.nasa_power_declared_date_min:
                report.issues.append(
                    f"NASA POWER: rango declarado inicia {report.nasa_power_declared_date_min}, "
                    f"datos inician {actual_min}"
                )
            if actual_max != report.nasa_power_declared_date_max:
                report.issues.append(
                    f"NASA POWER: rango declarado termina {report.nasa_power_declared_date_max}, "
                    f"datos terminan {actual_max}"
                )
    else:
        report.issues.append("NASA POWER: línea 'Dates (month/day/year)' ausente en el encabezado")

    location_line = next((line for line in meta_lines if "Location:" in line), None)
    if location_line:
        loc_match = _NASA_LOCATION_RE.search(location_line)
        if loc_match:
            report.nasa_power_declared_latitude = float(loc_match.group(1))
            report.nasa_power_declared_longitude = float(loc_match.group(2))
        else:
            report.issues.append("NASA POWER: línea 'Location' con formato inesperado")
    else:
        report.issues.append("NASA POWER: línea 'Location' ausente en el encabezado")

    if reference is not None:
        if report.nasa_power_sha256 != reference.nasa_power.sha256:
            report.issues.append(
                f"NASA POWER: SHA-256 no coincide con el manifiesto (esperado "
                f"{reference.nasa_power.sha256}, obtenido {report.nasa_power_sha256})"
            )
        if report.nasa_power_declared_latitude is None or (
            abs(report.nasa_power_declared_latitude - reference.nasa_power.latitude)
            > _COORDINATE_TOLERANCE_DEGREES
        ):
            report.issues.append(
                f"NASA POWER: latitud declarada {report.nasa_power_declared_latitude} no "
                f"coincide con la referencia del manifiesto {reference.nasa_power.latitude}"
            )
        if report.nasa_power_declared_longitude is None or (
            abs(report.nasa_power_declared_longitude - reference.nasa_power.longitude)
            > _COORDINATE_TOLERANCE_DEGREES
        ):
            report.issues.append(
                f"NASA POWER: longitud declarada {report.nasa_power_declared_longitude} no "
                f"coincide con la referencia del manifiesto {reference.nasa_power.longitude}"
            )

    # Estructural únicamente: el índice de fechas, nunca los valores de las
    # 4 variables (hallazgo H-03; el centinela -999 se cuenta y convierte
    # solo dentro de la ventana autorizada de cada etapa, en `ingestion.py`).
    return set(df.index)


def validate_pergamino_provenance(
    era5_path: str | Path,
    nasa_power_path: str | Path,
    *,
    mode: str = INPUT_MODE_SCIENTIFIC,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
) -> ProvenanceReport:
    """Valida identidad y estructura de los dos CSV de Pergamino. Nunca
    modifica los archivos ni analiza valores de humedad/RH2M/radiación.

    En modo `scientific` (por defecto): la referencia de hash y coordenadas
    por proveedor se lee del manifiesto versionado (`manifest_path`), nunca
    se calcula a partir de los archivos recibidos. Un fallo de esta
    validación nunca degrada la corrida a modo sintético — aborta la
    ejecución explícitamente (hallazgo H-01).

    En modo `synthetic` (exclusivo de tests/desarrollo): se omite la
    comparación contra el manifiesto real de Pergamino porque las fixtures
    sintéticas no representan esos archivos; el reporte queda marcado
    `scientific=False` sin importar el resultado de las demás validaciones
    estructurales, que sí se aplican en ambos modos."""
    if mode not in INPUT_MODES:
        raise ValueError(f"input_mode inválido: '{mode}' (válidos: {INPUT_MODES})")

    era5_path = Path(era5_path)
    nasa_power_path = Path(nasa_power_path)
    report = ProvenanceReport(
        era5_path=str(era5_path), nasa_power_path=str(nasa_power_path), mode=mode
    )

    reference: ManifestIdentityReference | None = None
    if mode == INPUT_MODE_SCIENTIFIC:
        try:
            reference = load_manifest_identity_reference(manifest_path)
        except (ManifestReferenceError, OSError) as exc:
            report.issues.append(
                f"No se pudo cargar la referencia de identidad del manifiesto versionado "
                f"({manifest_path}): {exc}"
            )

    era5_dates = _validate_era5(era5_path, report, reference)
    nasa_dates = _validate_nasa_power(nasa_power_path, report, reference)

    if era5_dates is not None and nasa_dates is not None:
        alignment = compute_date_alignment(era5_dates, nasa_dates)
        report.n_dates_common = alignment.n_common
        report.n_dates_only_era5 = alignment.n_only_era5
        report.n_dates_only_nasa_power = alignment.n_only_nasa_power

    return report


__all__ = [
    "EXPECTED_ERA5_FILENAME",
    "EXPECTED_NASA_POWER_FILENAME",
    "EXPECTED_TIMEZONE",
    "INPUT_MODE_SCIENTIFIC",
    "INPUT_MODE_SYNTHETIC",
    "ProvenanceReport",
    "compute_sha256",
    "validate_pergamino_provenance",
]
