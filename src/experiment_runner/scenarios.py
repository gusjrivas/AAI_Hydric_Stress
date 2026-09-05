"""Controlled observational noise and separately identified scarcity mechanisms."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def subsample_training_period(df, split_date: date, train_fraction: float):
    """Historical recent-window helper; never use to construct positional targets."""
    if not 0 < train_fraction <= 1:
        raise ValueError("train_fraction debe estar en (0, 1].")
    ordered = df.sort_values("timestamp").reset_index(drop=True)
    train = ordered[ordered.timestamp < pd.Timestamp(split_date)]
    test = ordered[ordered.timestamp >= pd.Timestamp(split_date)]
    return pd.concat(
        [train.tail(max(1, int(len(train) * train_fraction))), test], ignore_index=True
    )


def select_training_dates(dates, train_fraction=1.0, mode="coverage", random_state=42):
    """Select supervised examples AFTER engineering, preserving the input calendar.

    Coverage: one random example per equal chronological stratum. Recent: an
    equally sized suffix. Both use exactly the same eligible population/budget.
    """
    if not 0 < train_fraction <= 1 or mode not in {"coverage", "recent"}:
        raise ValueError("Fracción o modalidad de escasez inválida.")
    ordered = pd.Series(dates).sort_values().reset_index(drop=True)
    if ordered.empty:
        raise ValueError("No hay ejemplos elegibles de entrenamiento.")
    n = max(1, int(len(ordered) * train_fraction))
    if mode == "recent":
        return ordered.tail(n).tolist()
    rng = np.random.default_rng(random_state)
    return [
        ordered.iloc[int(rng.choice(block))] for block in np.array_split(np.arange(len(ordered)), n)
    ]


def fit_noise_scales(train, columns):
    scales = train[columns].astype(float).std().fillna(0.0)
    if not np.isfinite(scales).all():
        raise ValueError("Escala de ruido no finita.")
    return scales.to_dict()


def inject_gaussian_noise(df, columns, noise_std_ratio, random_state=42, *, scales=None):
    """Apply externally fitted CLEAN TRAIN scales; never estimate from evaluation."""
    if noise_std_ratio < 0 or not np.isfinite(noise_std_ratio):
        raise ValueError("noise_std_ratio debe ser finito y no negativo.")
    result = df.copy()
    if noise_std_ratio == 0:
        return result
    if scales is None or any(c not in scales for c in columns):
        raise ValueError("Proveer escalas calculadas exclusivamente sobre entrenamiento limpio.")
    rng = np.random.default_rng(random_state)
    for column in columns:
        if not np.isfinite(scales[column]) or scales[column] < 0:
            raise ValueError("Escala de ruido inválida.")
        result[column] = result[column].astype(float) + rng.normal(
            0, scales[column] * noise_std_ratio, size=len(result)
        )
    return result
