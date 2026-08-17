"""Reporte de distribuciones por variable (spec data-quality, requirement
"Reporte de distribuciones por variable").
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, TIMESTAMP_COLUMN


def describe_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada columna numérica del esquema presente en `df`, devuelve
    tipo de dato, mínimo, máximo, media y desvío estándar.
    """
    rows = []
    for column in {**REQUIRED_COLUMNS, **OPTIONAL_COLUMNS}:
        if column == TIMESTAMP_COLUMN or column not in df.columns:
            continue
        series = df[column]
        rows.append(
            {
                "column": column,
                "dtype": str(series.dtype),
                "min": series.min(),
                "max": series.max(),
                "mean": series.mean(),
                "std": series.std(),
            }
        )

    return pd.DataFrame(rows)
