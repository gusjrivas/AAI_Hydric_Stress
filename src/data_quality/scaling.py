"""Estandarización numérica reversible para modelado (spec data-quality,
requirement "Estandarización numérica reversible para modelado"), en
preparación para el consumo de HU4.
"""

from __future__ import annotations

import pandas as pd

ScalingParams = dict[str, tuple[float, float]]


def standardize(df: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, ScalingParams]:
    """Estandariza (media 0, desvío 1) las `columns` de `df`. Devuelve la
    copia estandarizada y los parámetros (media, desvío) por columna,
    necesarios para invertir la transformación con `inverse_standardize`.
    """
    result = df.copy()
    params: ScalingParams = {}

    for column in columns:
        mean = float(result[column].mean())
        std = float(result[column].std())
        params[column] = (mean, std)
        result[column] = (result[column] - mean) / std

    return result, params


def apply_standardization(df: pd.DataFrame, params: ScalingParams) -> pd.DataFrame:
    """Aplica una estandarización ya ajustada (`params`) a `df`, sin
    recalcular media/desvío a partir de `df`. Necesario para aplicar los
    parámetros ajustados sobre el conjunto de entrenamiento también al de
    evaluación (o a datos sintéticos), evitando fuga de información.
    """
    result = df.copy()

    for column, (mean, std) in params.items():
        result[column] = (result[column] - mean) / std

    return result


def inverse_standardize(df: pd.DataFrame, params: ScalingParams) -> pd.DataFrame:
    """Revierte la estandarización aplicada por `standardize`, usando los
    parámetros (media, desvío) guardados en su momento.
    """
    result = df.copy()

    for column, (mean, std) in params.items():
        result[column] = result[column] * std + mean

    return result
