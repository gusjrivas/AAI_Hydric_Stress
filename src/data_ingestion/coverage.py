"""Reporte de cobertura por columna obligatoria (spec data-ingestion,
requirement 'Reporte de cobertura por columna obligatoria').
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import REQUIRED_COLUMNS, TIMESTAMP_COLUMN


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada columna obligatoria presente en `df`, devuelve el rango
    temporal cubierto y el porcentaje de completitud.
    """
    if TIMESTAMP_COLUMN not in df.columns:
        raise KeyError(f"El dataset no tiene la columna '{TIMESTAMP_COLUMN}'")

    timestamps = pd.to_datetime(df[TIMESTAMP_COLUMN])
    total_rows = len(df)

    rows = []
    for column in REQUIRED_COLUMNS:
        if column == TIMESTAMP_COLUMN or column not in df.columns:
            continue
        non_null = df[column].notna()
        completeness = float(non_null.mean()) if total_rows else 0.0
        covered_timestamps = timestamps[non_null]
        rows.append(
            {
                "column": column,
                "completeness_pct": round(completeness * 100, 2),
                "start": covered_timestamps.min() if not covered_timestamps.empty else None,
                "end": covered_timestamps.max() if not covered_timestamps.empty else None,
            }
        )

    return pd.DataFrame(rows)
