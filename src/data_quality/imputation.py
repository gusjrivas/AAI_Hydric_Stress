"""Tratamiento de valores faltantes por imputación causal (spec
data-quality, requirement "Tratamiento de valores faltantes por
imputación causal, sin fuga temporal").

Reemplaza la interpolación lineal bidireccional anterior
(`interpolate(method="linear", limit_direction="both")`), que podía
completar un hueco del período de entrenamiento usando una observación
posterior perteneciente al período de evaluación (fuga temporal
confirmada en la auditoría metodológica de la memoria técnica). La
imputación causal (forward-fill) solo usa observaciones estrictamente
anteriores, nunca posteriores, ni dentro del propio `df` ni a través de
`warm_start`.
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import TIMESTAMP_COLUMN


def interpolate_missing_causal(
    df: pd.DataFrame,
    columns: list[str],
    warm_start: pd.Series | None = None,
) -> pd.DataFrame:
    """Devuelve una copia de `df`, ordenada por tiempo, con los valores
    faltantes de `columns` completados por forward-fill: cada valor
    faltante se completa con el último valor observado en una fecha
    estrictamente anterior, nunca con un valor posterior (no se usa
    `bfill` ni interpolación lineal, que podría promediar con el
    siguiente valor conocido).

    `warm_start`, si se provee, es la última fila válida de un período
    anterior (por ejemplo, la cola ya imputada del conjunto de
    entrenamiento) y sirve de semilla para completar los primeros
    valores faltantes de `df` sin recurrir a un valor posterior dentro
    del propio `df` — es la forma en que el período de evaluación
    puede arrancar con el último estado conocido de entrenamiento, tal
    como estaría disponible en un escenario de operación real.

    Si no hay ningún valor previo disponible (ni en `df` ni en
    `warm_start`) para una fila, esa fila queda en `NaN` — la decisión
    de descartarla o no le corresponde a quien llama.

    Agrega una columna booleana `<columna>_imputado` por cada columna
    tratada, marcando qué filas fueron efectivamente completadas por
    esta función (no las que ya venían sin dato y siguen sin dato).
    """
    result = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True).copy()

    for column in columns:
        was_missing = result[column].isna()

        if warm_start is not None and pd.notna(warm_start.get(column)):
            seeded = pd.concat([pd.Series([warm_start[column]]), result[column]], ignore_index=True)
            filled = seeded.ffill().iloc[1:].reset_index(drop=True)
        else:
            filled = result[column].ffill()

        result[column] = filled
        result[f"{column}_imputado"] = was_missing & result[column].notna()

    return result
