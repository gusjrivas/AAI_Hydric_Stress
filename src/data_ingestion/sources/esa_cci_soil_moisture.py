"""Conector de ESA CCI Soil Moisture (CEDA Archive, sin registro — ver
docs/research/hu2-fuentes-datos-acceso.md). Provee humedad de suelo diaria
en una grilla global de 0.25°, un archivo NetCDF por día; se extrae el
píxel más cercano a un punto dado.
"""

from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
import xarray as xr

from data_ingestion.schema import normalize_to_schema

BASE_URL = "https://dap.ceda.ac.uk/neodc/esacci/soil_moisture/data/daily_files/COMBINED"
VERSION = "v09.2"


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


def fetch_esa_cci_soil_moisture(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Descarga humedad de suelo diaria de ESA CCI (CEDA Archive) para un
    punto y rango de fechas, extrayendo el píxel más cercano de cada grilla
    global diaria, y normaliza al esquema con procedencia 'real'. Los días
    sin archivo disponible (404) quedan como NaN, no interrumpen la serie.
    """
    http = session or requests
    rows: list[dict[str, object]] = []
    day = start
    while day <= end:
        response = http.get(_file_url(day), timeout=60)
        if getattr(response, "status_code", 200) >= 400:
            # Un archivo faltante (404) o un error transitorio del servidor
            # (ej. 500) no debe abortar la serie completa: se registra como
            # NaN y se continúa con el resto de los días.
            rows.append({"timestamp": day, "soil_moisture": float("nan")})
        else:
            value = _extract_point_soil_moisture(response.content, latitude, longitude)
            rows.append({"timestamp": day, "soil_moisture": value})
        day += timedelta(days=1)

    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return normalize_to_schema(frame, provenance="real")
