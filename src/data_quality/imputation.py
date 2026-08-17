"""Tratamiento de valores faltantes por interpolación temporal (spec
data-quality, requirement "Tratamiento de valores faltantes por
interpolación temporal").
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import TIMESTAMP_COLUMN


def interpolate_missing(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Devuelve una copia de `df` con los valores faltantes de `columns`
    interpolados linealmente en el tiempo, y una columna booleana
    `<columna>_imputado` por cada columna tratada, marcando qué filas
    fueron imputadas (no quedan indistinguibles de los valores originales).
    """
    result = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True).copy()

    for column in columns:
        was_missing = result[column].isna()
        result[column] = result[column].interpolate(method="linear", limit_direction="both")
        result[f"{column}_imputado"] = was_missing

    return result
