"""Generador de lecturas sintéticas de sensor por random walk acotado
(spec data-ingestion, requirements "Generación de lecturas sintéticas
por random walk acotado" y "Backfill inicial de un dataset en vivo").
No mantiene estado propio: cada lectura se genera a partir de la
anterior, que se lee del propio dataset persistido (ADR-0007).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data_ingestion.schema import (
    PROVENANCE_COLUMN,
    REQUIRED_COLUMNS,
    TIMESTAMP_COLUMN,
    normalize_to_schema,
)
from data_ingestion.storage import DEFAULT_DATA_DIR, save_dataset
from data_quality.reference_et import estimate_et0
from data_quality.rules import get_range

_STEP_FRACTION = 0.02  # tamaño del paso aleatorio, como fracción del ancho del rango físico


def generate_next_reading(
    previous: pd.Series | None, timestamp: pd.Timestamp, random_state: int | None = None
) -> dict[str, Any]:
    """Genera una lectura sintética para `timestamp`, columna
    obligatoria por columna obligatoria, dando un paso aleatorio chico
    desde `previous` (o partiendo del punto medio del rango físico si
    no hay lectura anterior), recortado a `data_quality.rules.get_range`.
    `et0` se deriva del resto de la lectura por
    `data_quality.reference_et.estimate_et0` en vez de generarse por
    random walk.
    """
    rng = np.random.default_rng(random_state)
    reading: dict[str, Any] = {TIMESTAMP_COLUMN: timestamp}

    for column in REQUIRED_COLUMNS:
        if column in (TIMESTAMP_COLUMN, "et0"):
            continue
        low, high = get_range(column)
        step = (high - low) * _STEP_FRACTION
        if previous is not None and pd.notna(previous.get(column)):
            base = float(previous[column])
        else:
            base = (low + high) / 2
        value = base + rng.normal(0.0, step)
        reading[column] = float(np.clip(value, low, high))

    reading["et0"] = estimate_et0(
        temperature=reading["temperature"],
        relative_humidity=reading["relative_humidity"],
        solar_radiation=reading["solar_radiation"],
        wind_speed=reading["wind_speed"],
        timestamp=timestamp,
    )
    reading[PROVENANCE_COLUMN] = "sintetico"
    return reading


def seed_mock_dataset(
    name: str,
    start_date: date,
    end_date: date,
    random_state: int = 42,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> pd.DataFrame:
    """Genera un backfill de lecturas sintéticas encadenadas, una por
    día entre `start_date` y `end_date` (incluidos), y las guarda bajo
    `name`. Devuelve el dataset generado, ya guardado.
    """
    dates = pd.date_range(start_date, end_date, freq="D")

    rows = []
    previous: pd.Series | None = None
    for offset, timestamp in enumerate(dates):
        reading = generate_next_reading(previous, timestamp, random_state=random_state + offset)
        rows.append(reading)
        previous = pd.Series(reading)

    generated = normalize_to_schema(pd.DataFrame(rows), provenance="sintetico")
    save_dataset(name, generated, data_dir=data_dir)
    return generated
