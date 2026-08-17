"""Reporte de calidad: faltantes, duplicados y atípicos (spec
data-quality, requirement "Reporte de calidad (faltantes, duplicados,
atípicos)"). Los atípicos se detectan por regla de rango explícita
(`data_quality.rules`), no por un modelo de aprendizaje automático.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from data_ingestion.schema import REQUIRED_COLUMNS, TIMESTAMP_COLUMN
from data_quality.rules import AGRONOMIC_RANGES


def quality_report(df: pd.DataFrame) -> dict[str, Any]:
    """Genera el reporte de calidad de `df`: % de faltantes por columna
    obligatoria, timestamps duplicados, y timestamps con un valor fuera
    del rango físico/climático plausible por columna.
    """
    total_rows = len(df)

    missing_pct: dict[str, float] = {}
    out_of_range: dict[str, list] = {}

    for column in REQUIRED_COLUMNS:
        if column == TIMESTAMP_COLUMN or column not in df.columns:
            continue

        missing_pct[column] = round(float(df[column].isna().mean() * 100), 2) if total_rows else 0.0

        if column in AGRONOMIC_RANGES:
            minimum, maximum = AGRONOMIC_RANGES[column]
            out_of_range_mask = (df[column] < minimum) | (df[column] > maximum)
            out_of_range[column] = df.loc[out_of_range_mask, TIMESTAMP_COLUMN].tolist()

    duplicate_mask = df[TIMESTAMP_COLUMN].duplicated(keep=False)
    duplicate_timestamps = sorted(set(df.loc[duplicate_mask, TIMESTAMP_COLUMN].tolist()))

    return {
        "missing_pct": missing_pct,
        "duplicate_timestamps": duplicate_timestamps,
        "out_of_range": out_of_range,
    }
