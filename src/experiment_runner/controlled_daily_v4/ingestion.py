"""Ingesta y alineación causal ERA5-Land/NASA POWER para Pergamino.

Las funciones de lectura y agregación de este módulo (`load_*_raw`,
`aggregate_era5_daily`) son deliberadamente agnósticas de etapa: pueden
recibir la serie completa 2015-2025 y no filtran nada por sí solas. Eso NO
autoriza a un llamador a agregarlas/pasarlas a `replace_missing_sentinel`
sobre el archivo completo sin recortar antes: `restrict_era5_hourly_to_window`
y `restrict_nasa_power_daily_to_window` existen exactamente para que quien
orquesta una corrida de una etapa (la CLI, `stage_a_runner.py`) recorte las
entradas crudas a la ventana autorizada (más la historia causal mínima)
ANTES de agregar humedad, convertir el centinela `-999` o unir ambas fuentes
— nunca después (hallazgo H-03: la CLI llamaba `aggregate_era5_daily` y
`replace_missing_sentinel` sobre el rango completo, y solo el runner recortaba
después, con lo que un agregador llegaba a promediar humedad de 2024-2025).
`build_daily_joined_series` sigue siendo, por diseño, un join genérico sin
recorte propio: el recorte es responsabilidad exclusiva de quien orquesta la
corrida, usando las funciones de este módulo antes de invocarlo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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


def restrict_era5_hourly_to_window(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Recorta el CSV horario ERA5-Land a un rango de fechas calendario
    `[start, end]` (inclusive) ANTES de agregar a diario.

    Filtra únicamente por la fecha del timestamp `time` — un dato puramente
    estructural, no un valor de humedad — de modo que ninguna hora fuera de
    la ventana llegue jamás a `aggregate_era5_daily` (hallazgo H-03). Usar
    con los límites de `features.compute_stage_window_bounds` para aislar
    una etapa desde la ingesta, antes de cualquier agregación."""
    dates = df["time"].dt.date
    return df.loc[(dates >= start) & (dates <= end)].reset_index(drop=True)


def restrict_nasa_power_daily_to_window(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Recorta el CSV diario NASA POWER (ya indexado por fecha) al mismo
    rango `[start, end]` (inclusive), ANTES de convertir el centinela `-999`
    o unir con ERA5-Land (hallazgo H-03)."""
    index_dates = df.index.date
    return df.loc[(index_dates >= start) & (index_dates <= end)]


def _n_finite(series: pd.Series) -> int:
    return int(np.isfinite(series.to_numpy(dtype=float)).sum())


def aggregate_era5_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Promedio diario de las 4 columnas de humedad de suelo, más `n_obs`,
    `n_unique_hours` y `n_finite_<columna>` por columna.

    No imputa días con menos de 24 observaciones, ni corrige un día con una
    hora duplicada que oculte otra ausente — se conservan `n_obs` (cantidad
    de filas) y `n_unique_hours` (cantidad de horas distintas 0-23) para que
    quien consuma el resultado pueda exigir cobertura horaria completa dentro
    de su propio período autorizado (hallazgo H-02). Estas dos columnas son
    puramente temporales (no involucran valores de humedad): calcularlas
    sobre el archivo completo es estructura, no análisis de valores futuros
    (protocolo, sección 16).

    `n_finite_<columna>` cuenta, por columna de humedad de suelo, cuántas de
    las lecturas horarias del día son valores finitos: `groupby(...).mean()`
    ignora silenciosamente los `NaN` (`skipna=True`), de modo que un día con
    24 filas y 24 horas distintas pero una única lectura ausente/infinita
    igual produce un promedio "completo" en apariencia -- sin este contador
    esa lectura faltante queda invisible para quien valide cobertura después
    de agregar (hallazgo H-02)."""
    d = df.copy()
    d["date"] = d["time"].dt.date
    grouped = d.groupby("date")
    counts = grouped.size().rename("n_obs")
    n_unique_hours = grouped["time"].apply(lambda s: s.dt.hour.nunique()).rename("n_unique_hours")
    means = grouped[list(ALL_SOIL_MOISTURE_COLUMNS)].mean()
    finite_counts = grouped[list(ALL_SOIL_MOISTURE_COLUMNS)].agg(_n_finite)
    finite_counts = finite_counts.rename(
        columns={c: f"n_finite_{c}" for c in ALL_SOIL_MOISTURE_COLUMNS}
    )
    daily = means.join(counts).join(n_unique_hours).join(finite_counts)
    daily.index = pd.to_datetime(daily.index)
    daily.index.name = "date"
    return daily


def load_nasa_power_daily_raw(path: str | Path) -> tuple[list[str], pd.DataFrame]:
    """Lee el CSV diario de NASA POWER tal cual (sin convertir `-999`, sin filtrar por etapa).

    Devuelve las líneas de metadatos del bloque `-BEGIN HEADER-`/`-END HEADER-`
    y un DataFrame indexado por fecha (reconstruida desde YEAR+DOY), con las
    4 variables en sus valores crudos (incluyendo el centinela `-999` intacto).

    Levanta `ValueError` con diagnóstico explícito si falta alguna columna
    requerida -- nunca deja que una selección `df[columnas]` levante un
    `KeyError` genérico antes de que `provenance.py` pueda reportar el
    diagnóstico de columnas faltantes de forma controlada (hallazgo H-03)."""
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

    missing_columns = [c for c in NASA_POWER_VARIABLE_COLUMNS if c not in df.columns]
    if missing_columns:
        raise ValueError(f"columnas requeridas ausentes en NASA POWER: {missing_columns}")

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


def extract_era5_daily_dates(df: pd.DataFrame) -> set:
    """Fechas calendario presentes en el CSV horario, sin agregar ningún
    valor de humedad. Puramente estructural (protocolo, sección 16): permite
    verificar cobertura/alineación de fechas sin promediar humedad de suelo
    de todo el archivo, incluida la ventana de B/C (hallazgo H-03)."""
    return set(pd.to_datetime(df["time"]).dt.normalize())


def compute_date_alignment(era5_dates: set, nasa_dates: set) -> DateAlignmentReport:
    era5_dates = set(pd.Timestamp(d).normalize() for d in era5_dates)
    nasa_dates = set(pd.Timestamp(d).normalize() for d in nasa_dates)
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
