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
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from experiment_runner.controlled_daily_v4.config import (
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    FAMILY_SIMPLICITY_ORDER,
    RANDOM_STATE,
    WEIGHTING_BALANCED,
    WEIGHTING_NONE,
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
        ModelConfig(
            FAMILY_LOGISTIC_REGRESSION,
            {
                "C": c,
                "weighting": w,
                # `solver` y `max_iter` provienen de la grilla normativa en
                # lugar de quedar implícitos en los defaults del estimador.
                "solver": grid.solver,
                "max_iter": grid.max_iter,
            },
        )
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
                "random_state": grid.random_state,
                "n_jobs": grid.n_jobs,
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
                "max_depth": grid.max_depth,
                "early_stopping": grid.early_stopping,
                "random_state": grid.random_state,
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
    único estimador scikit-learn compatible (clonable, y utilizable como base
    del `SoftVotingClassifier` de este módulo).
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
        return ScaledLogisticRegression(
            C=params["C"],
            max_iter=params.get("max_iter", 2000),
            solver=params.get("solver", "lbfgs"),
        )
    if family == FAMILY_RANDOM_FOREST:
        return RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            random_state=params.get("random_state", RANDOM_STATE),
            n_jobs=params.get("n_jobs", 1),
        )
    if family == FAMILY_HIST_GRADIENT_BOOSTING:
        return HistGradientBoostingClassifier(
            learning_rate=params["learning_rate"],
            max_iter=params["max_iter"],
            max_leaf_nodes=params["max_leaf_nodes"],
            l2_regularization=params["l2_regularization"],
            max_depth=params.get("max_depth", None),
            early_stopping=params.get("early_stopping", False),
            random_state=params.get("random_state", RANDOM_STATE),
        )
    raise ValueError(f"Familia desconocida: {family}")


def effective_logistic_regularization(estimator: ScaledLogisticRegression) -> dict[str, Any]:
    """Regularización efectivamente aplicada por la Logistic Regression ya
    ajustada, leída de la API del estimador y no del valor declarado.

    En scikit-learn 1.9.0 el parámetro `penalty` está deprecado y su atributo
    expone el centinela `'deprecated'`; la regularización real la determina
    `l1_ratio` (`0.0` equivale a L2 puro, exactamente lo que exige el
    protocolo, sección 7.2)."""
    model = estimator.model_
    l1_ratio = getattr(model, "l1_ratio", None)
    if l1_ratio == 0.0 or l1_ratio is None:
        effective = "l2"
    elif l1_ratio == 1.0:
        effective = "l1"
    else:
        effective = "elasticnet"
    return {
        "effective_regularization": effective,
        "l1_ratio": l1_ratio,
        "C": float(model.C),
        "solver": model.solver,
        "penalty_attribute": str(getattr(model, "penalty", "absent")),
        "matches_protocol_l2": effective == "l2",
    }


def fit_estimator(family: str, params: dict[str, Any], X, y):
    """Instancia y ajusta un estimador de `family`, aplicando `sample_weight`
    fold-local (calculado con este mismo `y`) si `params['weighting']`
    indica ponderación balanceada. Nunca usa `class_weight`."""
    estimator = build_estimator(family, params)
    weights = _weight_for(np.asarray(y), params.get("weighting", "none"))
    estimator.fit(X, y, sample_weight=weights)
    return estimator


class SelfWeightingClassifier(ClassifierMixin, BaseEstimator):
    """Estimador base que calcula su propio `sample_weight` dentro de `fit`.

    Existe para que el Soft Voting respete el modo de balanceo seleccionado
    independientemente por cada familia (protocolo, secciones 7.1 y 7.5). No
    acepta `sample_weight` externo por diseño: los pesos derivan
    exclusivamente del `y` que recibe este `fit`, de modo que ninguna base
    puede heredar los pesos calculados para otra."""

    def __init__(self, family: str | None = None, model_params: dict[str, Any] | None = None):
        self.family = family
        self.model_params = model_params

    def weighting_mode(self) -> str:
        return dict(self.model_params or {}).get("weighting", WEIGHTING_NONE)

    def fit(self, X, y):
        params = dict(self.model_params or {})
        y = np.asarray(y)
        self.estimator_ = build_estimator(self.family, params)
        self.estimator_.fit(X, y, sample_weight=_weight_for(y, self.weighting_mode()))
        self.classes_ = np.asarray(self.estimator_.classes_)
        return self

    def predict_proba(self, X):
        return self.estimator_.predict_proba(X)

    def predict(self, X):
        return self.estimator_.predict(X)


class SoftVotingClassifier(ClassifierMixin, BaseEstimator):
    """Soft Voting propio: clona y ajusta cada base por separado y promedia
    `predict_proba` con pesos fijos (1/3, 1/3, 1/3).

    Reemplaza a `sklearn.ensemble.VotingClassifier`, que solo admite un único
    vector de `sample_weight` propagado a los tres sub-estimadores y por lo
    tanto no puede representar una combinación mixta de modos de balanceo.
    Las columnas de probabilidad se alinean explícitamente contra `classes_`
    del ensamble, sin suponer que cada base observó las dos clases."""

    def __init__(
        self,
        base_configs: dict[str, ModelConfig] | None = None,
        weights: list[float] | None = None,
    ):
        self.base_configs = base_configs
        self.weights = weights

    def _ordered_families(self) -> list[str]:
        """Orden determinista por simplicidad predeclarada, independiente del
        orden de inserción del diccionario recibido."""
        configs = self.base_configs or {}
        known = [f for f in FAMILY_SIMPLICITY_ORDER if f in configs]
        extra = sorted(f for f in configs if f not in FAMILY_SIMPLICITY_ORDER)
        return known + extra

    def base_weighting_modes(self) -> dict[str, str]:
        configs = self.base_configs or {}
        return {
            family: configs[family].params.get("weighting", WEIGHTING_NONE)
            for family in self._ordered_families()
        }

    def base_config_ids(self) -> dict[str, str]:
        configs = self.base_configs or {}
        return {family: configs[family].config_id for family in self._ordered_families()}

    def fit(self, X, y):
        configs = self.base_configs or {}
        if not configs:
            raise ValueError("Soft Voting requiere al menos una configuración base.")
        y = np.asarray(y)
        self.classes_ = np.unique(y)
        self.families_ = self._ordered_families()
        self.weights_ = (
            [float(w) for w in self.weights]
            if self.weights is not None
            else [1.0 / len(self.families_)] * len(self.families_)
        )
        self.named_estimators_ = {
            family: SelfWeightingClassifier(
                family=family, model_params=dict(configs[family].params)
            ).fit(X, y)
            for family in self.families_
        }
        return self

    def _aligned_proba(self, proba: np.ndarray, base_classes: np.ndarray) -> np.ndarray:
        position = {c: i for i, c in enumerate(self.classes_)}
        aligned = np.zeros((proba.shape[0], len(self.classes_)), dtype=float)
        for column, klass in enumerate(base_classes):
            aligned[:, position[klass]] = proba[:, column]
        return aligned

    def predict_proba(self, X):
        total = None
        for weight, family in zip(self.weights_, self.families_, strict=True):
            estimator = self.named_estimators_[family]
            contribution = (
                self._aligned_proba(estimator.predict_proba(X), estimator.classes_) * weight
            )
            total = contribution if total is None else total + contribution
        return total

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(axis=1)]


def build_soft_voting_estimator(
    base_configs: dict[str, ModelConfig],
) -> SoftVotingClassifier:
    """Soft Voting con los candidatos base y pesos fijos (1/3, 1/3, 1/3).
    Reentrena sus modelos base al ajustar (protocolo, sección 7.5) — no
    admite estimadores ya entrenados."""
    n = len(base_configs)
    return SoftVotingClassifier(base_configs=dict(base_configs), weights=[1 / n] * n)


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


def fit_soft_voting(base_configs: dict[str, ModelConfig], X, y) -> SoftVotingClassifier:
    """Ajusta el Soft Voting sin propagar ningún `sample_weight` global: cada
    base lo calcula internamente desde el mismo `y`, según su propio modo
    seleccionado (protocolo, secciones 7.1, 7.5 y 9)."""
    return build_soft_voting_estimator(base_configs).fit(X, y)
