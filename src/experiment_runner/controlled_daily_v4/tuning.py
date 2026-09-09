"""Evaluación de una configuración de hiperparámetros sobre una lista de folds.

Reutilizado tanto por el tuning inner de la Etapa A como por el congelamiento
final (protocolo, secciones 6, 8 y 9). El target y `P20_train` se calculan
siempre dentro de esta función, fold-local, nunca antes.
"""

from __future__ import annotations

import numpy as np

from experiment_runner.controlled_daily_v4.features import (
    FEATURE_COLUMNS,
    build_target,
    compute_p20_threshold,
)
from experiment_runner.controlled_daily_v4.models import ModelConfig, fit_estimator
from experiment_runner.controlled_daily_v4.splits import Fold


def evaluate_config_on_folds(config: ModelConfig, folds: list[Fold]) -> list[float]:
    from experiment_runner.controlled_daily_v4.metrics import mcc_strict

    scores = []
    for fold in folds:
        p20_train = compute_p20_threshold(fold.train["future_soil_moisture"])
        y_train = build_target(fold.train["future_soil_moisture"], p20_train).to_numpy()
        y_val = build_target(fold.validation["future_soil_moisture"], p20_train).to_numpy()
        X_train = fold.train[list(FEATURE_COLUMNS)].to_numpy()
        X_val = fold.validation[list(FEATURE_COLUMNS)].to_numpy()
        estimator = fit_estimator(config.family, config.params, X_train, y_train)
        y_pred = estimator.predict(X_val)
        scores.append(mcc_strict(y_val, y_pred))
    return scores


def median_ignoring_nan(scores: list[float]) -> float:
    if all(np.isnan(s) for s in scores):
        return float("nan")
    return float(np.nanmedian(scores))


def select_best_config(
    configs: list[ModelConfig], folds: list[Fold]
) -> tuple[ModelConfig, float, list[float]]:
    """Configuración de mayor mediana de MCC entre folds (ignorando `NaN`),
    junto con su mediana y los MCC individuales por fold."""
    best_config = None
    best_median = float("nan")
    best_scores: list[float] = []
    for config in configs:
        scores = evaluate_config_on_folds(config, folds)
        median = median_ignoring_nan(scores)
        if best_config is None or (
            not np.isnan(median) and (np.isnan(best_median) or median > best_median)
        ):
            best_config, best_median, best_scores = config, median, scores
    assert best_config is not None
    return best_config, best_median, best_scores
