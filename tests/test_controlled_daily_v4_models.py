from __future__ import annotations

import numpy as np
import pytest

from experiment_runner.controlled_daily_v4.config import (
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    HistGradientBoostingGridSpec,
    LogisticRegressionGridSpec,
    RandomForestGridSpec,
)
from experiment_runner.controlled_daily_v4.models import (
    ModelConfig,
    SoftVotingSpec,
    build_estimator,
    build_soft_voting_estimator,
    compute_sample_weight,
    fit_candidate,
    fit_estimator,
    iter_hist_gradient_boosting_configs,
    iter_logistic_regression_configs,
    iter_random_forest_configs,
)


def test_grid_sizes_are_exact():
    assert len(iter_logistic_regression_configs()) == 8
    assert len(iter_random_forest_configs()) == 24
    assert len(iter_hist_gradient_boosting_configs()) == 32


def test_grid_specs_report_matching_n_configs():
    assert LogisticRegressionGridSpec().n_configs == 8
    assert RandomForestGridSpec().n_configs == 24
    assert HistGradientBoostingGridSpec().n_configs == 32


def test_sample_weight_formula():
    y = np.array([0, 0, 0, 0, 1, 1])  # n_train=6, n_classes=2, n0=4, n1=2
    weights = compute_sample_weight(y)
    assert weights[y == 0][0] == pytest.approx(6 / (2 * 4))
    assert weights[y == 1][0] == pytest.approx(6 / (2 * 2))


def test_sample_weight_uses_only_the_given_y():
    y_a = np.array([0, 0, 1])
    y_b = np.array([0, 1, 1, 1])
    weight_class_0_a = compute_sample_weight(y_a)[y_a == 0][0]
    weight_class_0_b = compute_sample_weight(y_b)[y_b == 0][0]
    # Distintos y_train producen distintos pesos: no hay estado compartido.
    assert weight_class_0_a != pytest.approx(weight_class_0_b)


@pytest.mark.parametrize(
    ("family", "params"),
    [
        (FAMILY_LOGISTIC_REGRESSION, {"C": 1.0}),
        (FAMILY_RANDOM_FOREST, {"n_estimators": 10, "max_depth": 4, "min_samples_leaf": 5}),
        (
            FAMILY_HIST_GRADIENT_BOOSTING,
            {"learning_rate": 0.1, "max_iter": 10, "max_leaf_nodes": 15, "l2_regularization": 0.0},
        ),
    ],
)
def test_no_class_weight_param_used(family, params):
    estimator = build_estimator(family, params)
    estimator_params = estimator.get_params()
    assert "class_weight" not in estimator_params or estimator_params.get("class_weight") is None


def test_scaler_is_fold_local_not_shared_across_fits():
    rng = np.random.default_rng(0)
    X_a = rng.normal(loc=0, scale=1, size=(30, 3))
    X_b = rng.normal(loc=100, scale=1, size=(30, 3))
    y = (rng.random(30) < 0.4).astype(int)

    est_a = fit_estimator(FAMILY_LOGISTIC_REGRESSION, {"C": 1.0, "weighting": "none"}, X_a, y)
    est_b = fit_estimator(FAMILY_LOGISTIC_REGRESSION, {"C": 1.0, "weighting": "none"}, X_b, y)

    assert not np.allclose(est_a.scaler_.mean_, est_b.scaler_.mean_)


def test_soft_voting_has_fixed_uniform_weights():
    base = {
        FAMILY_LOGISTIC_REGRESSION: ModelConfig(FAMILY_LOGISTIC_REGRESSION, {"C": 1.0}),
        FAMILY_RANDOM_FOREST: ModelConfig(
            FAMILY_RANDOM_FOREST, {"n_estimators": 10, "max_depth": 4, "min_samples_leaf": 5}
        ),
        FAMILY_HIST_GRADIENT_BOOSTING: ModelConfig(
            FAMILY_HIST_GRADIENT_BOOSTING,
            {"learning_rate": 0.1, "max_iter": 10, "max_leaf_nodes": 15, "l2_regularization": 0.0},
        ),
    }
    voting = build_soft_voting_estimator(base)
    assert voting.weights == pytest.approx([1 / 3, 1 / 3, 1 / 3])
    assert voting.voting == "soft"
    assert voting.n_jobs == 1


def test_fit_candidate_dispatches_soft_voting_and_single_family():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(40, 3))
    y = (rng.random(40) < 0.3).astype(int)

    single = fit_candidate(
        ModelConfig(FAMILY_LOGISTIC_REGRESSION, {"C": 1.0, "weighting": "none"}), X, y
    )
    assert hasattr(single, "predict_proba")

    base = {
        FAMILY_LOGISTIC_REGRESSION: ModelConfig(
            FAMILY_LOGISTIC_REGRESSION, {"C": 1.0, "weighting": "none"}
        ),
        FAMILY_RANDOM_FOREST: ModelConfig(
            FAMILY_RANDOM_FOREST,
            {"n_estimators": 10, "max_depth": 4, "min_samples_leaf": 5, "weighting": "none"},
        ),
        FAMILY_HIST_GRADIENT_BOOSTING: ModelConfig(
            FAMILY_HIST_GRADIENT_BOOSTING,
            {
                "learning_rate": 0.1,
                "max_iter": 10,
                "max_leaf_nodes": 15,
                "l2_regularization": 0.0,
                "weighting": "none",
            },
        ),
    }
    voting = fit_candidate(SoftVotingSpec(base), X, y)
    proba = voting.predict_proba(X)
    assert proba.shape == (40, 2)
