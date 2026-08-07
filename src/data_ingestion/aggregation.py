"""Agregación a granularidad diaria, preservando la serie nativa (spec
data-ingestion, requirement 'Preservación de la resolución temporal nativa
junto a una vista diaria').
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import PROVENANCE_COLUMN, TIMESTAMP_COLUMN

_SUM_COLUMNS = {"precipitation"}


def to_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una vista agregada diaria de `df`. No modifica `df`: la
    serie nativa se conserva intacta en el dataset original.
    """
    if TIMESTAMP_COLUMN not in df.columns:
        raise KeyError(f"El dataset no tiene la columna '{TIMESTAMP_COLUMN}'")

    working = df.copy()
    working[TIMESTAMP_COLUMN] = pd.to_datetime(working[TIMESTAMP_COLUMN])
    working["_date"] = working[TIMESTAMP_COLUMN].dt.date

    numeric_columns = [
        c for c in working.select_dtypes(include="number").columns if c != "_date"
    ]
    agg_map = {c: ("sum" if c in _SUM_COLUMNS else "mean") for c in numeric_columns}

    daily = working.groupby("_date").agg(agg_map).reset_index()
    daily = daily.rename(columns={"_date": TIMESTAMP_COLUMN})
    daily[TIMESTAMP_COLUMN] = pd.to_datetime(daily[TIMESTAMP_COLUMN])

    if PROVENANCE_COLUMN in df.columns:
        provenance_by_day = (
            working.groupby("_date")[PROVENANCE_COLUMN].first().reset_index()
        )
        provenance_by_day = provenance_by_day.rename(columns={"_date": TIMESTAMP_COLUMN})
        provenance_by_day[TIMESTAMP_COLUMN] = pd.to_datetime(
            provenance_by_day[TIMESTAMP_COLUMN]
        )
        daily = daily.merge(provenance_by_day, on=TIMESTAMP_COLUMN)

    return daily
