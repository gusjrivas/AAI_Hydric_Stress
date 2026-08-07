"""Conector de NASA POWER (comunidad Agroclimatology, sin registro ni API
key — ver docs/research/hu2-fuentes-datos-acceso.md). Provee variables
climáticas obligatorias del esquema; no provee humedad de suelo ni ET0
directamente (ET0 se deriva en preprocesamiento a partir de estas
variables, no se ingiere).
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import requests

from data_ingestion.schema import normalize_to_schema

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Mapeo de parámetros NASA POWER -> columnas del esquema (data_ingestion.schema)
_PARAMETER_TO_COLUMN = {
    "T2M": "temperature",
    "RH2M": "relative_humidity",
    "PRECTOTCORR": "precipitation",
    "ALLSKY_SFC_SW_DWN": "solar_radiation",
    "WS2M": "wind_speed",
}

_FILL_VALUE = -999.0  # valor centinela documentado por NASA POWER para datos faltantes


def fetch_nasa_power(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Descarga variables climáticas diarias de NASA POWER para un punto y
    rango de fechas, y las normaliza al esquema de data-ingestion con
    procedencia 'real'.
    """
    params = {
        "parameters": ",".join(_PARAMETER_TO_COLUMN),
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }

    http = session or requests
    response = http.get(NASA_POWER_BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    parameter_series = payload["properties"]["parameter"]
    frame = pd.DataFrame(
        {
            column: pd.Series(parameter_series[nasa_param])
            for nasa_param, column in _PARAMETER_TO_COLUMN.items()
            if nasa_param in parameter_series
        }
    )
    frame = frame.replace(_FILL_VALUE, pd.NA)
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d")
    frame = frame.reset_index(names="timestamp")

    return normalize_to_schema(frame, provenance="real")
