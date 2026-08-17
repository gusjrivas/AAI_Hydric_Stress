"""Conector de ESA CCI Soil Moisture (CEDA Archive, sin registro — ver
docs/research/hu2-fuentes-datos-acceso.md). Provee humedad de suelo diaria
en una grilla global de 0.25°, un archivo NetCDF por día; se extrae el
píxel más cercano a un punto dado.
"""

from __future__ import annotations

import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
import xarray as xr

from data_ingestion.schema import normalize_to_schema

BASE_URL = "https://dap.ceda.ac.uk/neodc/esacci/soil_moisture/data/daily_files/COMBINED"
VERSION = "v09.2"
MAX_ATTEMPTS = 3


def _file_url(day: date) -> str:
    stamp = day.strftime("%Y%m%d")
    return (
        f"{BASE_URL}/{VERSION}/{day.year}/"
        f"ESACCI-SOILMOISTURE-L3S-SSMV-COMBINED-{stamp}000000-f{VERSION}.nc?download=1"
    )


def _extract_point_soil_moisture(content: bytes, latitude: float, longitude: float) -> float:
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        with xr.open_dataset(tmp_path) as ds:
            point = ds.sel(lat=latitude, lon=longitude, method="nearest")
            return float(point["sm"].to_numpy().reshape(-1)[0])
    finally:
        tmp_path.unlink(missing_ok=True)


def _fetch_day(
    http,
    day: date,
    latitude: float,
    longitude: float,
    retry_delay: float,
) -> float:
    """Intenta descargar y extraer el valor de un día, con reintentos ante
    errores transitorios (de conexión o HTTP >= 400, ej. 500). Si todos los
    intentos fallan, o el archivo no existe (404 persistente), devuelve NaN
    en lugar de propagar la excepción: un día puntual no debe abortar la
    serie completa (fallas reales observadas: 500 en 2024-04-18,
    RemoteDisconnected en una corrida posterior).
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = http.get(_file_url(day), timeout=60)
        except requests.exceptions.RequestException:
            if attempt == MAX_ATTEMPTS:
                return float("nan")
            time.sleep(retry_delay)
            continue

        if getattr(response, "status_code", 200) >= 400:
            if attempt == MAX_ATTEMPTS:
                return float("nan")
            time.sleep(retry_delay)
            continue

        return _extract_point_soil_moisture(response.content, latitude, longitude)

    return float("nan")


def fetch_esa_cci_soil_moisture(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    session: requests.Session | None = None,
    retry_delay: float = 2.0,
) -> pd.DataFrame:
    """Descarga humedad de suelo diaria de ESA CCI (CEDA Archive) para un
    punto y rango de fechas, extrayendo el píxel más cercano de cada grilla
    global diaria, y normaliza al esquema con procedencia 'real'. Los días
    sin archivo disponible o con errores transitorios (de conexión o HTTP)
    quedan como NaN tras reintentar, sin interrumpir la serie.
    """
    http = session or requests
    rows: list[dict[str, object]] = []
    day = start
    while day <= end:
        value = _fetch_day(http, day, latitude, longitude, retry_delay)
        rows.append({"timestamp": day, "soil_moisture": value})
        day += timedelta(days=1)

    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return normalize_to_schema(frame, provenance="real")
