"""Congelamiento final de hiperparámetros tras seleccionar familia (protocolo, sección 9).

Segunda pasada, independiente de los 9 pares outer×inner de la selección de
familia: un nuevo `TimeSeriesSplit(n_splits=3, gap=3)` sobre TODA la Etapa A,
exclusivamente para fijar la configuración final. Nunca usa 2023.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from experiment_runner.controlled_daily_v4.config import GAP, OUTER_N_SPLITS
from experiment_runner.controlled_daily_v4.features import (
    FEATURE_COLUMNS,
    build_target,
    compute_p20_threshold,
)
from experiment_runner.controlled_daily_v4.models import ModelConfig, fit_estimator
from experiment_runner.controlled_daily_v4.splits import generate_outer_folds
from experiment_runner.controlled_daily_v4.tuning import select_best_config


@dataclass(frozen=True)
class FrozenConfig:
    family: str
    config: ModelConfig
    median_mcc: float
    fold_mcc: list[float]


def freeze_family(
    family: str,
    configs: list[ModelConfig],
    eligible_frame: pd.DataFrame,
    n_splits: int = OUTER_N_SPLITS,
    gap: int = GAP,
) -> FrozenConfig:
    """Elige, entre `configs` de una única familia, la de mayor mediana de
    MCC sobre una segunda pasada de `TimeSeriesSplit(n_splits, gap)` sobre
    TODA la Etapa A. No ajusta el estimador final — eso lo hace
    `fit_final_estimator`, sobre el conjunto completo."""
    folds = generate_outer_folds(eligible_frame, n_splits=n_splits, gap=gap)
    best_config, median, scores = select_best_config(configs, folds)
    return FrozenConfig(family=family, config=best_config, median_mcc=median, fold_mcc=scores)


def fit_final_estimator(frozen: FrozenConfig, eligible_frame: pd.DataFrame) -> tuple[Any, float]:
    """Reentrena la configuración congelada sobre TODA la Etapa A (2015-2022),
    aprendiendo `P20_train` exclusivamente sobre ese mismo conjunto completo.
    Nunca usa 2023. Devuelve `(estimador_ajustado, p20_train)`."""
    p20_train = compute_p20_threshold(eligible_frame["future_soil_moisture"])
    y = build_target(eligible_frame["future_soil_moisture"], p20_train).to_numpy()
    X = eligible_frame[list(FEATURE_COLUMNS)].to_numpy()
    estimator = fit_estimator(frozen.family, frozen.config.params, X, y)
    return estimator, p20_train
