"""Fixtures sintéticas para los tests de controlled_daily_v4 (Etapa A).

Nunca lee los CSV reales de Pergamino. Genera series diarias sintéticas
dentro del calendario real de la Etapa A (2015-2022) para que el filtrado
por `STAGE_A_BOUNDS` (fijo, normativo) siga siendo ejercitado por los tests.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ERA5_METADATA_HEADER = (
    "latitude,longitude,elevation,utc_offset_seconds,timezone,timezone_abbreviation"
)
ERA5_METADATA_VALUES = "-33.899998,-60.6,70.0,-10800,America/Argentina/Buenos_Aires,GMT-3"

ERA5_SOIL_MOISTURE_RAW_COLUMNS = [
    "soil_moisture_0_to_7cm (m³/m³)",
    "soil_moisture_7_to_28cm (m³/m³)",
    "soil_moisture_28_to_100cm (m³/m³)",
    "soil_moisture_100_to_255cm (m³/m³)",
]


def make_synthetic_daily_frame(n_days: int = 500, seed: int = 7) -> pd.DataFrame:
    """DataFrame indexado por fecha (desde 2015-01-01), con las 4 columnas
    de humedad de suelo, RH2M, ALLSKY_SFC_SW_DWN, T2M, PRECTOTCORR. Serie
    autocorrelacionada (random walk acotado) para que haya variabilidad
    suficiente y ambas clases del target aparezcan."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-01-01", periods=n_days, freq="D")

    base = 0.35 + 0.05 * np.sin(np.linspace(0, 6 * np.pi, n_days))
    noise = rng.normal(0, 0.02, n_days)
    soil_0_7 = np.clip(base + np.cumsum(rng.normal(0, 0.005, n_days)) * 0.1 + noise, 0.1, 0.6)
    soil_7_28 = np.clip(soil_0_7 + rng.normal(0, 0.01, n_days), 0.1, 0.6)
    soil_28_100 = np.clip(soil_0_7 + rng.normal(0, 0.005, n_days), 0.1, 0.6)
    soil_100_255 = np.clip(0.35 + rng.normal(0, 0.002, n_days), 0.1, 0.6)

    rh2m = np.clip(
        70 + 15 * np.sin(np.linspace(0, 6 * np.pi, n_days)) + rng.normal(0, 5, n_days), 10, 100
    )
    radiation = np.clip(
        18 + 8 * np.sin(np.linspace(0, 6 * np.pi, n_days) + 1) + rng.normal(0, 3, n_days), 0, 35
    )
    t2m = np.clip(
        18 + 8 * np.sin(np.linspace(0, 6 * np.pi, n_days) + 2) + rng.normal(0, 2, n_days), -5, 40
    )
    precip = np.clip(rng.exponential(2.0, n_days) - 1.5, 0, None)

    return pd.DataFrame(
        {
            "soil_moisture_0_to_7cm": soil_0_7,
            "soil_moisture_7_to_28cm": soil_7_28,
            "soil_moisture_28_to_100cm": soil_28_100,
            "soil_moisture_100_to_255cm": soil_100_255,
            "RH2M": rh2m,
            "ALLSKY_SFC_SW_DWN": radiation,
            "T2M": t2m,
            "PRECTOTCORR": precip,
        },
        index=dates,
    )


def write_synthetic_era5_csv(path: str | Path, daily_frame: pd.DataFrame) -> None:
    """Vuelca `daily_frame` como un CSV horario ERA5-Land sintético: cada
    día se repite 24 veces (mismo valor, sin variación horaria) para que la
    agregación diaria reproduzca exactamente `daily_frame`."""
    rows = []
    for date, row in daily_frame.iterrows():
        for hour in range(24):
            ts = f"{date.date()}T{hour:02d}:00"
            rows.append(
                [
                    ts,
                    round(float(row["soil_moisture_0_to_7cm"]), 6),
                    round(float(row["soil_moisture_7_to_28cm"]), 6),
                    round(float(row["soil_moisture_28_to_100cm"]), 6),
                    round(float(row["soil_moisture_100_to_255cm"]), 6),
                ]
            )
    hourly = pd.DataFrame(rows, columns=["time", *ERA5_SOIL_MOISTURE_RAW_COLUMNS])
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(ERA5_METADATA_HEADER + "\n")
        f.write(ERA5_METADATA_VALUES + "\n")
        f.write("\n")
        hourly.to_csv(f, index=False)


def write_synthetic_nasa_power_csv(path: str | Path, daily_frame: pd.DataFrame) -> None:
    """Vuelca `daily_frame` como un CSV diario NASA POWER sintético, con el
    bloque de header `-BEGIN HEADER-`/`-END HEADER-` real (rango de fechas
    coincidente con los datos)."""
    date_min = daily_frame.index.min()
    date_max = daily_frame.index.max()
    header = [
        "-BEGIN HEADER-",
        "NASA/POWER Source Native Resolution Daily Data ",
        f"Dates (month/day/year): {date_min:%m/%d/%Y} through {date_max:%m/%d/%Y} in LST",
        "Location: latitude  -33.891   longitude -60.5746 ",
        "elevation from MERRA-2: Average for 0.5 x 0.625 degree lat/lon region = 69.07 meters",
        "The value for missing source data that cannot be computed or is outside of the "
        "sources availability range: -999 ",
        "parameter(s): ",
        "RH2M                  MERRA-2 Relative Humidity at 2 Meters (%) ",
        "ALLSKY_SFC_SW_DWN     CERES SYN1deg All Sky Surface Shortwave Downward Irradiance "
        "(MJ/m^2/day) ",
        "T2M                   MERRA-2 Temperature at 2 Meters (C) ",
        "PRECTOTCORR           MERRA-2 Precipitation Corrected (mm/day) ",
        "-END HEADER-",
    ]
    rows = []
    for date, row in daily_frame.iterrows():
        year = date.year
        doy = date.dayofyear
        rows.append(
            [
                year,
                doy,
                round(float(row["RH2M"]), 2),
                round(float(row["ALLSKY_SFC_SW_DWN"]), 2),
                round(float(row["T2M"]), 2),
                round(float(row["PRECTOTCORR"]), 2),
            ]
        )
    data = pd.DataFrame(
        rows, columns=["YEAR", "DOY", "RH2M", "ALLSKY_SFC_SW_DWN", "T2M", "PRECTOTCORR"]
    )
    with open(path, "w", encoding="ascii", newline="\r\n") as f:
        for line in header:
            f.write(line + "\n")
        data.to_csv(f, index=False, lineterminator="\r\n")


def write_synthetic_pergamino_csv_pair(
    tmp_dir: str | Path, n_days: int = 500, seed: int = 7
) -> tuple[Path, Path]:
    tmp_dir = Path(tmp_dir)
    daily_frame = make_synthetic_daily_frame(n_days=n_days, seed=seed)
    era5_path = tmp_dir / "pergamino_era5land_soil_hourly_2015_2025.csv"
    nasa_power_path = tmp_dir / "pergamino_nasa_power_daily_2015_2025.csv"
    write_synthetic_era5_csv(era5_path, daily_frame)
    write_synthetic_nasa_power_csv(nasa_power_path, daily_frame)
    return era5_path, nasa_power_path


_ERA5_DATA_START_LINE = 4
"""2 líneas de metadatos + 1 línea en blanco + 1 encabezado tabular."""


def _era5_day_line_range(day_index: int) -> tuple[int, int]:
    start = _ERA5_DATA_START_LINE + 24 * day_index
    return start, start + 24


def drop_one_hourly_row(path: str | Path, day_index: int, hour: int = 12) -> None:
    """Elimina una única fila horaria de un día (queda con 23 observaciones),
    para reproducir el hallazgo H-02 ("día con 23 horas")."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    start, end = _era5_day_line_range(day_index)
    del lines[start + hour]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def duplicate_hour_hiding_missing_hour(
    path: str | Path, day_index: int, duplicated_hour: int = 6, missing_hour: int = 18
) -> None:
    """Reemplaza la fila de `missing_hour` por una copia de la de
    `duplicated_hour`: el día conserva 24 filas (`n_obs == 24`) pero solo 23
    horas distintas -- reproduce el hallazgo H-02 ("hora duplicada que
    mantiene 24 filas pero oculta otra hora ausente")."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    start, _end = _era5_day_line_range(day_index)
    lines[start + missing_hour] = lines[start + duplicated_hour]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def corrupt_era5_hourly_value(
    path: str | Path,
    day_index: int,
    hour: int,
    column_name: str,
    raw_value: str,
) -> None:
    """Reemplaza el valor crudo de una única columna en una fila horaria
    puntual (día/hora), preservando las otras 23 filas del día intactas --
    reproduce el hallazgo H-02 ("lectura horaria faltante/no finita con
    n_obs y n_unique_hours ambos en 24"). `raw_value` se escribe tal cual en
    el CSV (p.ej. `""` para vacío/NaN, `"inf"` para infinito)."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    start, _end = _era5_day_line_range(day_index)
    line_index = start + hour
    fields = lines[line_index].split(",")
    col_index = 1 + ERA5_SOIL_MOISTURE_RAW_COLUMNS.index(column_name)
    fields[col_index] = raw_value
    lines[line_index] = ",".join(fields)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def drop_nasa_power_column(path: str | Path, column_name: str) -> None:
    """Elimina por completo una columna (encabezado tabular + todas las
    filas) del CSV diario NASA POWER, para reproducir una entrada con una
    columna requerida ausente (hallazgo H-03/validación de columnas)."""
    path = Path(path)
    lines = path.read_bytes().decode("ascii").split("\r\n")
    header_idx = next(i for i, line in enumerate(lines) if line.startswith("YEAR,DOY"))
    columns = lines[header_idx].split(",")
    col_index = columns.index(column_name)
    del columns[col_index]
    lines[header_idx] = ",".join(columns)
    for i in range(header_idx + 1, len(lines)):
        if not lines[i].strip():
            continue
        fields = lines[i].split(",")
        if len(fields) <= col_index:
            continue
        del fields[col_index]
        lines[i] = ",".join(fields)
    path.write_bytes("\r\n".join(lines).encode("ascii"))


def remove_calendar_day(
    era5_path: str | Path,
    nasa_path: str | Path,
    date,
    *,
    from_era5: bool = True,
    from_nasa: bool = True,
) -> None:
    """Elimina por completo un día calendario de una o ambas fuentes, para
    reproducir el hallazgo H-02 (día faltante oculto por el inner join)."""
    date_str = str(date)
    if from_era5:
        era5_path = Path(era5_path)
        lines = era5_path.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if not line.startswith(date_str)]
        era5_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    if from_nasa:
        nasa_path = Path(nasa_path)
        content_lines = nasa_path.read_bytes().decode("ascii").splitlines()
        import pandas as pd

        target = pd.Timestamp(date_str)
        year, doy = target.year, target.dayofyear
        prefix = f"{year},{doy},"
        kept = [line for line in content_lines if not line.startswith(prefix)]
        nasa_path.write_bytes(("\r\n".join(kept) + "\r\n").encode("ascii"))


MANIFEST_REFERENCE_TEMPLATE = """\
coordinates:
  requested:
    latitude: -33.89101
    longitude: -60.57462
  returned_era5_land:
    latitude: {era5_lat}
    longitude: {era5_lon}
    elevation_m: {era5_elev}
  returned_nasa_power:
    latitude: {nasa_lat}
    longitude: {nasa_lon}
    elevation_m: {nasa_elev}

sources:
  era5_land:
    raw_file:
      size_bytes: {era5_size}
      sha256: {era5_sha256}
  nasa_power:
    raw_file:
      size_bytes: {nasa_size}
      sha256: {nasa_sha256}

aggregation_rules:
  hourly_to_daily: placeholder

environment:
  status: TEST_ONLY
  python_version: "{python_version} (referencia de test)"
  numpy_version: "0.0.0"

repository_state:
  branch: test
"""


def write_manifest_reference_fixture(
    path: str | Path,
    *,
    era5_sha256: str,
    nasa_sha256: str,
    era5_lat: float = -33.899998,
    era5_lon: float = -60.6,
    era5_elev: float = 70.0,
    nasa_lat: float = -33.891,
    nasa_lon: float = -60.5746,
    nasa_elev: float = 69.07,
    era5_size: int = 0,
    nasa_size: int = 0,
    python_version: str = "3.11.16",
) -> Path:
    """Manifiesto mínimo (mismos marcadores de bloque que el real) para
    ejercitar `manifest_reference.py` sin depender del manifiesto real ni de
    los CSV de Pergamino."""
    path = Path(path)
    path.write_text(
        MANIFEST_REFERENCE_TEMPLATE.format(
            era5_lat=era5_lat,
            era5_lon=era5_lon,
            era5_elev=era5_elev,
            nasa_lat=nasa_lat,
            nasa_lon=nasa_lon,
            nasa_elev=nasa_elev,
            era5_size=era5_size,
            era5_sha256=era5_sha256,
            nasa_size=nasa_size,
            nasa_sha256=nasa_sha256,
            python_version=python_version,
        ),
        encoding="utf-8",
    )
    return path
