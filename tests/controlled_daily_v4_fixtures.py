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
