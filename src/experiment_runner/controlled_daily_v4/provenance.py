"""Validación de provenance de los dos CSV crudos de Pergamino.

Exclusivamente lectura: nunca modifica los archivos. El hash SHA-256 puede
recorrer el archivo completo porque no analiza resultados, targets ni
métricas — solo integridad física (protocolo, sección 3).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from experiment_runner.controlled_daily_v4.config import (
    ALL_SOIL_MOISTURE_COLUMNS,
    NASA_POWER_MISSING_SENTINEL,
)
from experiment_runner.controlled_daily_v4.ingestion import (
    NASA_POWER_VARIABLE_COLUMNS,
    aggregate_era5_daily,
    compute_date_alignment,
    load_era5_hourly_raw,
    load_nasa_power_daily_raw,
)

EXPECTED_ERA5_FILENAME = "pergamino_era5land_soil_hourly_2015_2025.csv"
EXPECTED_NASA_POWER_FILENAME = "pergamino_nasa_power_daily_2015_2025.csv"

EXPECTED_TIMEZONE = "America/Argentina/Buenos_Aires"

_NASA_DATE_RANGE_RE = re.compile(
    r"Dates \(month/day/year\):\s*(\d{2})/(\d{2})/(\d{4})\s*through\s*(\d{2})/(\d{2})/(\d{4})"
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
    n_dates_common: int = 0
    n_dates_only_era5: int = 0
    n_dates_only_nasa_power: int = 0

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0


def _validate_era5(path: Path, report: ProvenanceReport) -> tuple:
    if not path.exists():
        report.issues.append(f"ERA5-Land: archivo no encontrado en {path}")
        return None, None

    if path.name != EXPECTED_ERA5_FILENAME:
        report.issues.append(
            f"ERA5-Land: nombre inesperado '{path.name}' (se esperaba '{EXPECTED_ERA5_FILENAME}')"
        )

    report.era5_sha256 = compute_sha256(path)
    report.era5_size_bytes = path.stat().st_size

    metadata, df = load_era5_hourly_raw(path)
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
    else:
        report.era5_n_records = len(df)
        n_dup = int(df["time"].duplicated().sum())
        report.era5_n_duplicated_timestamps = n_dup
        if n_dup:
            report.issues.append(f"ERA5-Land: {n_dup} timestamps duplicados")

    daily = aggregate_era5_daily(df)
    return daily, metadata


def _validate_nasa_power(path: Path, report: ProvenanceReport) -> object:
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

    meta_lines, df = load_nasa_power_daily_raw(path)

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

    sentinel_present = (df == NASA_POWER_MISSING_SENTINEL).to_numpy().sum()
    if sentinel_present:
        report.issues.append(
            f"NASA POWER: {int(sentinel_present)} valores centinela -999 presentes "
            "(se convertirán a NaN solo en memoria durante la construcción de features, "
            "no en este archivo)"
        )

    return df


def validate_pergamino_provenance(
    era5_path: str | Path,
    nasa_power_path: str | Path,
    *,
    expected_era5_sha256: str | None = None,
    expected_nasa_power_sha256: str | None = None,
) -> ProvenanceReport:
    """Valida existencia, nombres, hash, tamaño, encabezados, columnas,
    variables, timezone, coordenadas, duplicados y alineación por fecha de
    los dos CSV de Pergamino. Nunca modifica los archivos."""

    era5_path = Path(era5_path)
    nasa_power_path = Path(nasa_power_path)
    report = ProvenanceReport(era5_path=str(era5_path), nasa_power_path=str(nasa_power_path))

    era5_daily, _era5_meta = _validate_era5(era5_path, report)
    nasa_df = _validate_nasa_power(nasa_power_path, report)

    if expected_era5_sha256 is not None and report.era5_sha256 != expected_era5_sha256:
        report.issues.append(
            f"ERA5-Land: SHA-256 no coincide (esperado {expected_era5_sha256}, "
            f"obtenido {report.era5_sha256})"
        )
    if (
        expected_nasa_power_sha256 is not None
        and report.nasa_power_sha256 != expected_nasa_power_sha256
    ):
        report.issues.append(
            f"NASA POWER: SHA-256 no coincide (esperado {expected_nasa_power_sha256}, "
            f"obtenido {report.nasa_power_sha256})"
        )

    if era5_daily is not None and nasa_df is not None:
        alignment = compute_date_alignment(era5_daily, nasa_df)
        report.n_dates_common = alignment.n_common
        report.n_dates_only_era5 = alignment.n_only_era5
        report.n_dates_only_nasa_power = alignment.n_only_nasa_power

    return report
