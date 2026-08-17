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
