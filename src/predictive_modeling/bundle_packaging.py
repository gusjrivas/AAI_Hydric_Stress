"""Packaging-time adapter for estimators fitted on a plain array (never a
DataFrame) — used only when building a bundle, never inside
`controlled_daily_v4`/`freezing.py`/`tuning.py`/the stage runners, which stay
frozen and untouched.

scikit-learn only autopopulates `feature_names_in_` when `.fit()` receives an
object with `.columns` (a DataFrame). `controlled_daily_v4` deliberately fits
on `ndarray` (frozen protocol decision), so its fitted estimators never get
that attribute, and the existing v2 loader (`load_operational_bundle`)
requires it on both `model` and `calibrator`. Restituting it here is not
falsifying metadata: the estimator was in fact fit on exactly these columns,
in this exact order (the array's column order), so the attribute reflects a
fact about the already-completed fit, not an invented claim.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class EstimatorNotFittedError(ValueError):
    """`attach_feature_names` requires an already-fitted estimator."""


class FeatureNameCountMismatchError(ValueError):
    """`feature_columns` length does not match the estimator's fitted input width."""


class IncompatibleFeatureNamesError(ValueError):
    """The estimator already has `feature_names_in_`, and it disagrees with
    `feature_columns` — refuses to silently overwrite it."""


def _fitted_n_features_in(estimator: Any) -> int | None:
    """`n_features_in_` on the estimator itself, or — for a wrapper around a
    custom ClassifierMixin that never calls `check_array`/`_validate_data`
    in its own `fit` (e.g. v4's `ScaledLogisticRegression`, alone or wrapped
    by `CalibratedClassifierCV(FrozenEstimator(...))`) — on the first fitted
    attribute found by unwrapping known delegation points. Never invents a
    count; a wrapper chain that never reaches one returns None."""
    current = estimator
    visited: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in visited:
            return None
        visited.add(id(current))
        if hasattr(current, "n_features_in_"):
            return current.n_features_in_
        calibrated_classifiers = getattr(current, "calibrated_classifiers_", None)
        if calibrated_classifiers:
            current = calibrated_classifiers[0]
            continue
        current = next(
            (
                candidate
                for attribute in ("model_", "estimator_", "base_estimator_", "estimator")
                if (candidate := getattr(current, attribute, None)) is not None
            ),
            None,
        )
    return None


def attach_feature_names(estimator: Any, feature_columns: list[str]) -> None:
    """Restore `feature_names_in_` on an estimator already fitted on an
    array, using the exact column order of the training matrix. Mutates
    `estimator` in place; does not change its predictions."""
    n_features_in = _fitted_n_features_in(estimator)
    if n_features_in is None:
        raise EstimatorNotFittedError(
            "attach_feature_names requiere un estimador ya ajustado "
            "(sin n_features_in_, no se puede confirmar que .fit() ya corrió)."
        )
    if n_features_in != len(feature_columns):
        raise FeatureNameCountMismatchError(
            f"El estimador fue ajustado con {n_features_in} columnas, "
            f"pero se pasaron {len(feature_columns)} nombres."
        )
    existing = getattr(estimator, "feature_names_in_", None)
    if existing is not None:
        if list(existing) != list(feature_columns):
            raise IncompatibleFeatureNamesError(
                f"El estimador ya tiene feature_names_in_={list(existing)!r}, "
                f"distinto de {feature_columns!r} — no se sobrescribe."
            )
        return
    estimator.feature_names_in_ = np.array(feature_columns, dtype=object)
