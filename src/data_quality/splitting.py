"""Partición entrenamiento/evaluación sin fuga temporal (spec
data-quality, requirement "Partición entrenamiento/evaluación sin fuga
temporal").
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from data_ingestion.schema import TIMESTAMP_COLUMN


def temporal_train_test_split(
    df: pd.DataFrame, split_date: date
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parte `df` por corte cronológico simple en `split_date`: el
    conjunto de entrenamiento contiene únicamente fechas anteriores a
    `split_date`, y el de evaluación fechas iguales o posteriores. No
    mezcla fechas entre ambos conjuntos.
    """
    cutoff = pd.Timestamp(split_date)
    ordered = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)

    train = ordered[ordered[TIMESTAMP_COLUMN] < cutoff].reset_index(drop=True)
    test = ordered[ordered[TIMESTAMP_COLUMN] >= cutoff].reset_index(drop=True)

    return train, test


def purge_target_horizon(train: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    """Elimina las últimas `horizon_days` filas de `train` (ordenado por
    tiempo). Necesario porque la variable objetivo de una fila se
    calcula `horizon_days` filas adelante (`predictive_modeling.labeling
    .add_stress_label`): incluso después de partir train/test por fecha,
    las últimas `horizon_days` filas de train tienen un target que cae
    en el período de evaluación — su etiqueta usaría información del
    futuro perteneciente a test, aunque la fila en sí pertenezca a
    train. Con `horizon_days=0` devuelve `train` sin cambios.
    """
    if horizon_days <= 0:
        return train

    ordered = train.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)
    return ordered.iloc[: max(0, len(ordered) - horizon_days)].reset_index(drop=True)
