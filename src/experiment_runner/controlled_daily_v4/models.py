"""Cuatro candidatos de controlled_daily_v4_external_pergamino (ADR-0010).

Balanceo de clases exclusivamente vía `sample_weight` fold-local — nunca
`class_weight` (protocolo, sección 7.1; ADR-0011, alternativas consideradas).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from experiment_runner.controlled_daily_v4.config import (
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    WEIGHTING_BALANCED,
    HistGradientBoostingGridSpec,
    LogisticRegressionGridSpec,
    RandomForestGridSpec,
)


def compute_sample_weight(y: np.ndarray) -> np.ndarray:
    """`w_c = n_train / (n_classes * n_train_c)`, calculado con `y` del train
    correspondiente (fold-local). Nunca con datos de validación/test."""
    y = np.asarray(y)
    classes, counts = np.unique(y, return_counts=True)
    n_train = len(y)
    n_classes = len(classes)
    weight_by_class = {
        c: n_train / (n_classes * count) for c, count in zip(classes, counts, strict=True)
    }
    return np.array([weight_by_class[v] for v in y], dtype=float)


def _weight_for(y: np.ndarray, weighting: str) -> np.ndarray | None:
    if weighting == WEIGHTING_BALANCED:
        return compute_sample_weight(y)
    return None


@dataclass(frozen=True)
class ModelConfig:
    family: str
    params: dict[str, Any]

    @property
    def config_id(self) -> str:
        items = ",".join(f"{k}={v}" for k, v in sorted(self.params.items()))
        return f"{self.family}[{items}]"


def iter_logistic_regression_configs(
    grid: LogisticRegressionGridSpec | None = None,
) -> list[ModelConfig]:
    grid = grid or LogisticRegressionGridSpec()
    return [
        ModelConfig(FAMILY_LOGISTIC_REGRESSION, {"C": c, "weighting": w})
        for c, w in product(grid.C, grid.weighting)
    ]


def iter_random_forest_configs(grid: RandomForestGridSpec | None = None) -> list[ModelConfig]:
    grid = grid or RandomForestGridSpec()
    return [
        ModelConfig(
            FAMILY_RANDOM_FOREST,
            {
                "n_estimators": n,
                "max_depth": d,
                "min_samples_leaf": m,
                "weighting": w,
            },
        )
        for n, d, m, w in product(
            grid.n_estimators, grid.max_depth, grid.min_samples_leaf, grid.weighting
        )
    ]


def iter_hist_gradient_boosting_configs(
    grid: HistGradientBoostingGridSpec | None = None,
) -> list[ModelConfig]:
    grid = grid or HistGradientBoostingGridSpec()
    return [
        ModelConfig(
            FAMILY_HIST_GRADIENT_BOOSTING,
            {
                "learning_rate": lr,
                "max_iter": mi,
                "max_leaf_nodes": mln,
                "l2_regularization": l2,
                "weighting": w,
            },
        )
        for lr, mi, mln, l2, w in product(
            grid.learning_rate,
            grid.max_iter,
            grid.max_leaf_nodes,
            grid.l2_regularization,
            grid.weighting,
        )
    ]


class ScaledLogisticRegression(ClassifierMixin, BaseEstimator):
    """`StandardScaler` fold-local + `LogisticRegression`, expuestos como un
    único estimador scikit-learn compatible (clonable por `VotingClassifier`).
    Sin `random_state`: `lbfgs` es determinista para este problema (protocolo,
    sección 7.2). No pasa `penalty` explícito a `LogisticRegression`: en la
    versión fijada del entorno (scikit-learn 1.9.0, ver constraints.txt) ese
    parámetro está deprecado a favor de `l1_ratio`, y el valor por defecto ya
    es regularización L2 — exactamente lo que exige el protocolo — sin emitir
    `FutureWarning`."""

    def __init__(self, C: float = 1.0, max_iter: int = 2000, solver: str = "lbfgs"):
        self.C = C
        self.max_iter = max_iter
        self.solver = solver

    def fit(self, X, y, sample_weight=None):
        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(X)
        self.model_ = LogisticRegression(C=self.C, max_iter=self.max_iter, solver=self.solver)
        self.model_.fit(X_scaled, y, sample_weight=sample_weight)
        self.classes_ = self.model_.classes_
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(self.scaler_.transform(X))

    def predict(self, X):
        return self.model_.predict(self.scaler_.transform(X))


def build_estimator(family: str, params: dict[str, Any]):
    if family == FAMILY_LOGISTIC_REGRESSION:
        return ScaledLogisticRegression(C=params["C"])
    if family == FAMILY_RANDOM_FOREST:
        return RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            random_state=params.get("random_state", 42),
            n_jobs=1,
        )
    if family == FAMILY_HIST_GRADIENT_BOOSTING:
        return HistGradientBoostingClassifier(
            learning_rate=params["learning_rate"],
            max_iter=params["max_iter"],
            max_leaf_nodes=params["max_leaf_nodes"],
            l2_regularization=params["l2_regularization"],
            max_depth=None,
            early_stopping=False,
            random_state=params.get("random_state", 42),
        )
    raise ValueError(f"Familia desconocida: {family}")


def fit_estimator(family: str, params: dict[str, Any], X, y):
    """Instancia y ajusta un estimador de `family`, aplicando `sample_weight`
    fold-local (calculado con este mismo `y`) si `params['weighting']`
    indica ponderación balanceada. Nunca usa `class_weight`."""
    estimator = build_estimator(family, params)
    weights = _weight_for(np.asarray(y), params.get("weighting", "none"))
    estimator.fit(X, y, sample_weight=weights)
    return estimator


def build_soft_voting_estimator(
    base_configs: dict[str, ModelConfig],
) -> VotingClassifier:
    """`VotingClassifier(voting='soft')` con los tres candidatos base y
    pesos fijos (1/3, 1/3, 1/3). Reentrena sus tres modelos base al ajustar
    (protocolo, sección 7.5) — no admite estimadores ya entrenados."""
    estimators = [
        (family, build_estimator(family, config.params)) for family, config in base_configs.items()
    ]
    return VotingClassifier(
        estimators=estimators, voting="soft", weights=[1 / 3, 1 / 3, 1 / 3], n_jobs=1
    )


@dataclass(frozen=True)
class SoftVotingSpec:
    base_configs: dict[str, ModelConfig]


def fit_candidate(spec: ModelConfig | SoftVotingSpec, X, y):
    """Despacha a `fit_estimator` (familia individual) o `fit_soft_voting`
    (Soft Voting), según el tipo de `spec`. Ambas rutas exponen `predict`/
    `predict_proba` de forma uniforme."""
    if isinstance(spec, SoftVotingSpec):
        return fit_soft_voting(spec.base_configs, X, y)
    return fit_estimator(spec.family, spec.params, X, y)


def fit_soft_voting(base_configs: dict[str, ModelConfig], X, y) -> VotingClassifier:
    voting = build_soft_voting_estimator(base_configs)
    # VotingClassifier.fit no admite sample_weight por sub-estimador de forma
    # diferenciada en esta versión de scikit-learn; se aplica un único
    # sample_weight combinado si TODAS las configuraciones base piden
    # ponderación balanceada, replicando el criterio de cada familia.
    weightings = {c.params.get("weighting", "none") for c in base_configs.values()}
    weights = compute_sample_weight(np.asarray(y)) if weightings == {WEIGHTING_BALANCED} else None
    voting.fit(X, y, sample_weight=weights)
    return voting
