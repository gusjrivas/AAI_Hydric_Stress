"""Nested temporal CV de la Etapa A: `TimeSeriesSplit(n_splits=3, gap=3)`.

El invariante `max(target_timestamp_train) < min(feature_timestamp_validation)`
se verifica explícitamente en cada fold generado, outer e inner (protocolo,
secciones 6 y 8; delta de spec, escenario "Nested cross-validation temporal
con gap suficiente para el horizonte").
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit


class TemporalInvariantViolation(AssertionError):
    """El último target de train no es estrictamente anterior a la primera
    emisión de validación — no debería ocurrir con `gap` suficiente."""


def assert_temporal_invariant(train_frame: pd.DataFrame, val_frame: pd.DataFrame) -> None:
    if len(train_frame) == 0 or len(val_frame) == 0:
        return
    max_target_train = pd.to_datetime(train_frame["target_timestamp"]).max()
    min_feature_val = pd.to_datetime(val_frame["feature_timestamp"]).min()
    if not (max_target_train < min_feature_val):
        raise TemporalInvariantViolation(
            f"max(target_timestamp_train)={max_target_train} no es estrictamente "
            f"anterior a min(feature_timestamp_validation)={min_feature_val}"
        )


@dataclass(frozen=True)
class Fold:
    index: int
    segment_id: str
    train: pd.DataFrame
    validation: pd.DataFrame


def _split_frame(frame: pd.DataFrame, n_splits: int, gap: int, segment_prefix: str) -> list[Fold]:
    frame = frame.sort_values("feature_timestamp").reset_index(drop=True)
    n = len(frame)
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    folds: list[Fold] = []
    for i, (train_idx, val_idx) in enumerate(splitter.split(np.arange(n)), start=1):
        train_frame = frame.iloc[train_idx]
        val_frame = frame.iloc[val_idx]
        assert_temporal_invariant(train_frame, val_frame)
        folds.append(
            Fold(
                index=i,
                segment_id=f"{segment_prefix}_fold_{i}",
                train=train_frame,
                validation=val_frame,
            )
        )
    return folds


def generate_outer_folds(eligible: pd.DataFrame, n_splits: int, gap: int) -> list[Fold]:
    return _split_frame(eligible, n_splits, gap, segment_prefix="outer")


def generate_inner_folds(outer_train: pd.DataFrame, n_splits: int, gap: int) -> list[Fold]:
    return _split_frame(outer_train, n_splits, gap, segment_prefix="inner")
