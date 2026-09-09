"""Ingesta y alineación causal ERA5-Land/NASA POWER para Pergamino.

Construye la serie diaria continua 2015-2025 (sin filtrar por etapa): el
filtrado por etapa ocurre en `features.py`, nunca aquí, para no reiniciar
artificialmente lags/rolling en cada frontera (protocolo, sección 5).
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.config import (
    ALL_SOIL_MOISTURE_COLUMNS,
    NASA_POWER_MISSING_SENTINEL,
    RELATIVE_HUMIDITY_COLUMN,
    SOLAR_RADIATION_COLUMN,
)

ERA5_RAW_SOIL_MOISTURE_COLUMNS = (
    "soil_moisture_0_to_7cm (m³/m³)",
    "soil_moisture_7_to_28cm (m³/m³)",
    "soil_moisture_28_to_100cm (m³/m³)",
    "soil_moisture_100_to_255cm (m³/m³)",
)
_RAW_TO_SHORT = dict(zip(ERA5_RAW_SOIL_MOISTURE_COLUMNS, ALL_SOIL_MOISTURE_COLUMNS, strict=True))

NASA_POWER_VARIABLE_COLUMNS = (
    RELATIVE_HUMIDITY_COLUMN,
    SOLAR_RADIATION_COLUMN,
    "T2M",
    "PRECTOTCORR",
)


@dataclass(frozen=True)
class Era5Metadata:
    latitude: float
    longitude: float
    elevation_m: float
    utc_offset_seconds: int
    timezone: str
    timezone_abbreviation: str


def load_era5_hourly_raw(path: str | Path) -> tuple[Era5Metadata, pd.DataFrame]:
    """Lee el CSV horario de Open-Meteo/ERA5-Land tal cual (sin filtrar por etapa).

    Devuelve los metadatos embebidos (2 primeras líneas) y un DataFrame con
    columnas `time` (datetime naive, ya en huso local, ver metadatos) y las
    4 columnas de humedad de suelo, renombradas a nombres cortos.
    """
    with open(path, encoding="utf-8") as f:
        meta_header = f.readline().strip().split(",")
        meta_values = f.readline().strip().split(",")
    meta = dict(zip(meta_header, meta_values, strict=True))
    metadata = Era5Metadata(
        latitude=float(meta["latitude"]),
        longitude=float(meta["longitude"]),
        elevation_m=float(meta["elevation"]),
        utc_offset_seconds=int(meta["utc_offset_seconds"]),
        timezone=meta["timezone"],
        timezone_abbreviation=meta["timezone_abbreviation"],
    )
    df = pd.read_csv(path, skiprows=3, encoding="utf-8")
    df.columns = [c.strip() for c in df.columns]
    df["time"] = pd.to_datetime(df["time"])
    df = df.rename(columns=_RAW_TO_SHORT)
    return metadata, df


def aggregate_era5_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Promedio diario de las 4 columnas de humedad de suelo, más `n_obs`.

    No imputa días con menos de 24 observaciones — se conserva `n_obs` para
    que quien consuma el resultado pueda decidir si un día es completo.
    """
    d = df.copy()
    d["date"] = d["time"].dt.date
    grouped = d.groupby("date")
    counts = grouped.size().rename("n_obs")
    means = grouped[list(ALL_SOIL_MOISTURE_COLUMNS)].mean()
    daily = means.join(counts)
    daily.index = pd.to_datetime(daily.index)
    daily.index.name = "date"
    return daily


def load_nasa_power_daily_raw(path: str | Path) -> tuple[list[str], pd.DataFrame]:
    """Lee el CSV diario de NASA POWER tal cual (sin convertir `-999`, sin filtrar por etapa).

    Devuelve las líneas de metadatos del bloque `-BEGIN HEADER-`/`-END HEADER-`
    y un DataFrame indexado por fecha (reconstruida desde YEAR+DOY), con las
    4 variables en sus valores crudos (incluyendo el centinela `-999` intacto).
    """
    with open(path, encoding="ascii", errors="replace") as f:
        lines = f.readlines()
    header_end = next(i for i, line in enumerate(lines) if "-END HEADER-" in line)
    header_start = next(i for i, line in enumerate(lines) if "-BEGIN HEADER-" in line)
    meta_lines = [line.strip() for line in lines[header_start + 1 : header_end]]
    data_lines = lines[header_end + 1 :]
    df = pd.read_csv(StringIO("".join(data_lines)))
    df["date"] = pd.to_datetime(df["YEAR"].astype(str), format="%Y") + pd.to_timedelta(
        df["DOY"] - 1, unit="D"
    )
    df = df.set_index("date")
    df.index.name = "date"
    return meta_lines, df[list(NASA_POWER_VARIABLE_COLUMNS)]


def replace_missing_sentinel(nasa_power_df: pd.DataFrame) -> pd.DataFrame:
    """Convierte el centinela `-999` a `NaN`, solamente en memoria (protocolo, sección 16)."""
    return nasa_power_df.replace(NASA_POWER_MISSING_SENTINEL, np.nan)


@dataclass(frozen=True)
class DateAlignmentReport:
    n_dates_era5: int
    n_dates_nasa_power: int
    n_common: int
    n_only_era5: int
    n_only_nasa_power: int


def compute_date_alignment(
    era5_daily: pd.DataFrame, nasa_power_df: pd.DataFrame
) -> DateAlignmentReport:
    era5_dates = set(era5_daily.index)
    nasa_dates = set(nasa_power_df.index)
    return DateAlignmentReport(
        n_dates_era5=len(era5_dates),
        n_dates_nasa_power=len(nasa_dates),
        n_common=len(era5_dates & nasa_dates),
        n_only_era5=len(era5_dates - nasa_dates),
        n_only_nasa_power=len(nasa_dates - era5_dates),
    )


def build_daily_joined_series(
    era5_daily: pd.DataFrame, nasa_power_df: pd.DataFrame
) -> pd.DataFrame:
    """Serie diaria continua completa (2015-2025, sin filtrar por etapa).

    Inner join por fecha calendario. El centinela `-999` de NASA POWER ya
    debe haberse convertido a `NaN` (ver `replace_missing_sentinel`) antes de
    llamar a esta función, si corresponde.
    """
    joined = era5_daily.join(nasa_power_df, how="inner")
    return joined.sort_index()
