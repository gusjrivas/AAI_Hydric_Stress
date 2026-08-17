"""Variables predictoras con retardos y ventanas móviles sin fuga
temporal (spec predictive-modeling, requirement "Variables predictoras
con retardos y ventanas móviles sin fuga temporal"). Todas las
variables se calculan exclusivamente con datos del día `t` o
anteriores, nunca posteriores.
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import TIMESTAMP_COLUMN


def add_lag_features(df: pd.DataFrame, columns: list[str], lags: list[int]) -> pd.DataFrame:
    """Agrega `<columna>_lag<n>` por cada combinación de `columns`/`lags`:
    el valor de esa columna `n` días antes. Los primeros `n` días de cada
    columna quedan en NaN (no hay pasado suficiente).
    """
    result = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True).copy()

    for column in columns:
        for lag in lags:
            result[f"{column}_lag{lag}"] = result[column].shift(lag)

    return result


def add_rolling_features(df: pd.DataFrame, columns: list[str], windows: list[int]) -> pd.DataFrame:
    """Agrega `<columna>_roll_mean<w>` por cada combinación de
    `columns`/`windows`: la media móvil de los últimos `w` días
    (incluyendo el día actual), sin mirar días posteriores.
    """
    result = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True).copy()

    for column in columns:
        for window in windows:
            result[f"{column}_roll_mean{window}"] = (
                result[column].rolling(window=window, min_periods=window).mean()
            )

    return result
