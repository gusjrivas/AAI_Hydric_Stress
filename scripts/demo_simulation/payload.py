"""Construcción del payload HTTP de una lectura sintética a partir del
generador existente (`data_ingestion.mock_sensor.generate_next_reading`,
ADR-0007). A diferencia de `scripts/simulate_sensor_readings.py`, incluye
`et0` explícitamente (diseño, sección 2: "no se omite esa variable como
sucede en el cliente simple actual").
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from typing import Any

import pandas as pd

from data_ingestion.mock_sensor import generate_next_reading
from data_ingestion.schema import PROVENANCE_COLUMN, TIMESTAMP_COLUMN

_PAYLOAD_COLUMNS = (
    "soil_moisture",
    "temperature",
    "relative_humidity",
    "precipitation",
    "solar_radiation",
    "wind_speed",
    "et0",
)


def clean_float(value: Any) -> float | None:
    if value is None:
        return None
    value = float(value)
    return None if math.isnan(value) else value


def generate_day_reading(previous: dict[str, Any] | None, day: date, seed: int) -> dict[str, Any]:
    """Genera la lectura sintética de `day` encadenada desde `previous`
    (la última lectura generada por esta misma sesión, nunca releída
    del dataset del backend) con `random_state=seed`, reproducible dado
    el mismo `previous` y `seed`. `previous=None` arranca del punto
    medio del rango físico de cada variable (mismo comportamiento que
    `data_ingestion.mock_sensor.seed_mock_dataset` para el primer día).
    """
    previous_series = pd.Series(previous) if previous is not None else None
    timestamp = pd.Timestamp(day)
    reading = generate_next_reading(previous_series, timestamp, random_state=seed)
    return reading


def build_ingest_payload(reading: dict[str, Any]) -> dict[str, Any]:
    """Cuerpo JSON de `POST /sensors/{sensor_id}/readings` para
    `reading` (un dict producido por `generate_day_reading` o por el
    encadenado de historial de `prepare`).
    """
    payload: dict[str, Any] = {
        "timestamp": pd.Timestamp(reading[TIMESTAMP_COLUMN]).isoformat(),
        "procedencia": reading.get(PROVENANCE_COLUMN, "sintetico"),
    }
    for column in _PAYLOAD_COLUMNS:
        payload[column] = clean_float(reading.get(column))
    return payload


def reading_to_json(reading: dict[str, Any]) -> dict[str, Any]:
    """Serializa una lectura generada (dict con `pd.Timestamp`/`numpy`
    floats) a tipos nativos de JSON, para persistirla en el manifiesto
    como `last_generated_reading` (continuación del random walk propio
    de la sesión, nunca releído del dataset del backend).
    """
    return {
        key: (
            pd.Timestamp(value).isoformat()
            if key == TIMESTAMP_COLUMN
            else (clean_float(value) if isinstance(value, float | int) else value)
        )
        for key, value in reading.items()
    }


def payload_hash(payload: dict[str, Any]) -> str:
    """Hash estable de `payload` (claves ordenadas), para detectar en
    una recuperación futura (entrega 2) si el payload persistido antes
    del POST coincide con el que se intentaría reenviar.
    """
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
