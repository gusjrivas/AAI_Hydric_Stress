"""Evaluación de relevancia de variables (spec predictive-modeling,
requirement "Evaluación de relevancia de variables").
"""

from __future__ import annotations

import pandas as pd


def feature_relevance(
    df: pd.DataFrame, feature_columns: list[str], target_column: str
) -> dict[str, float]:
    """Devuelve la correlación de cada columna de `feature_columns` con
    `target_column`, para orientar la selección de variables antes del
    modelado. Filas con valores faltantes en la columna o el objetivo se
    excluyen del cálculo de esa columna.
    """
    return {
        column: float(df[[column, target_column]].corr().iloc[0, 1]) for column in feature_columns
    }
