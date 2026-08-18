"""Escenarios de escasez y ruido de datos (spec experiment-runner,
requirements "Escenario de escasez de datos" y "Escenario de ruido de
datos").
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

TIMESTAMP_COLUMN = "timestamp"


def subsample_training_period(
    df: pd.DataFrame, split_date: date, train_fraction: float
) -> pd.DataFrame:
    """Simula escasez de datos: conserva solo la fracción `train_fraction`
    más reciente del período de entrenamiento (fechas antes de
    `split_date`), sin tocar el período de evaluación (fechas iguales o
    posteriores). `train_fraction=1.0` devuelve `df` sin cambios.
    """
    if train_fraction >= 1.0:
        return df

    ordered = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)
    cutoff = pd.Timestamp(split_date)

    train_rows = ordered[ordered[TIMESTAMP_COLUMN] < cutoff]
    test_rows = ordered[ordered[TIMESTAMP_COLUMN] >= cutoff]

    n_keep = max(1, int(len(train_rows) * train_fraction))
    reduced_train = train_rows.tail(n_keep)

    return pd.concat([reduced_train, test_rows], ignore_index=True)


def inject_gaussian_noise(
    df: pd.DataFrame, columns: list[str], noise_std_ratio: float, random_state: int = 42
) -> pd.DataFrame:
    """Simula ruido de sensor: agrega a una copia de `df` ruido gaussiano
    de media cero sobre `columns`, con desvío proporcional
    (`noise_std_ratio`) al desvío observado de cada columna.
    `noise_std_ratio=0.0` devuelve los valores sin cambios.
    """
    result = df.copy()
    if noise_std_ratio == 0.0:
        return result

    rng = np.random.default_rng(random_state)
    for column in columns:
        column_std = result[column].std()
        noise = rng.normal(0, column_std * noise_std_ratio, size=len(result))
        result[column] = result[column] + noise

    return result
