"""Soft Voting con ponderaciones independientes por modelo base.

El protocolo (sección 7.5) compone el cuarto candidato con las configuraciones
ya seleccionadas de LR/RF/HGB, cada una con su propio modo de balanceo. Estos
tests fijan que ningún vector de `sample_weight` global se propague a los tres
estimadores: cada base calcula el suyo desde el `y` que recibe en su `fit`.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest
from sklearn.base import clone

from experiment_runner.controlled_daily_v4.config import (
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    WEIGHTING_BALANCED,
    WEIGHTING_MODES,
    WEIGHTING_NONE,
)
from experiment_runner.controlled_daily_v4.models import (
    ModelConfig,
    SelfWeightingClassifier,
    SoftVotingClassifier,
    build_soft_voting_estimator,
    fit_estimator,
    fit_soft_voting,
)

BASE_PARAMS = {
    FAMILY_LOGISTIC_REGRESSION: {"C": 1.0},
    FAMILY_RANDOM_FOREST: {"n_estimators": 25, "max_depth": 4, "min_samples_leaf": 5},
    FAMILY_HIST_GRADIENT_BOOSTING: {
        "learning_rate": 0.1,
        "max_iter": 25,
        "max_leaf_nodes": 15,
        "l2_regularization": 0.0,
    },
}


def _imbalanced_dataset(n=240, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 4))
    # Desbalanceada a propósito: sin desbalance, ponderar y no ponderar
    # producirían ajustes indistinguibles y el test no probaría nada.
    y = (X[:, 0] + rng.normal(0, 0.5, n) > 1.2).astype(int)
    return X, y


def _base_configs(modes: dict[str, str]) -> dict[str, ModelConfig]:
    return {
        family: ModelConfig(family, {**BASE_PARAMS[family], "weighting": modes[family]})
        for family in BASE_PARAMS
    }


MIXED_MODES = {
    FAMILY_LOGISTIC_REGRESSION: WEIGHTING_BALANCED,
    FAMILY_RANDOM_FOREST: WEIGHTING_NONE,
    FAMILY_HIST_GRADIENT_BOOSTING: WEIGHTING_BALANCED,
}


def test_mixed_logistic_regression_base_matches_standalone_balanced_fit():
    X, y = _imbalanced_dataset()
    voting = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    inside = voting.named_estimators_[FAMILY_LOGISTIC_REGRESSION].estimator_
    standalone = fit_estimator(
        FAMILY_LOGISTIC_REGRESSION,
        {**BASE_PARAMS[FAMILY_LOGISTIC_REGRESSION], "weighting": WEIGHTING_BALANCED},
        X,
        y,
    )
    np.testing.assert_allclose(inside.model_.coef_, standalone.model_.coef_)


def test_mixed_random_forest_base_matches_standalone_unweighted_fit():
    X, y = _imbalanced_dataset()
    voting = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    inside = voting.named_estimators_[FAMILY_RANDOM_FOREST].estimator_
    standalone = fit_estimator(
        FAMILY_RANDOM_FOREST,
        {**BASE_PARAMS[FAMILY_RANDOM_FOREST], "weighting": WEIGHTING_NONE},
        X,
        y,
    )
    np.testing.assert_allclose(inside.predict_proba(X), standalone.predict_proba(X))


def test_mixed_hist_gradient_boosting_base_matches_standalone_balanced_fit():
    X, y = _imbalanced_dataset()
    voting = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    inside = voting.named_estimators_[FAMILY_HIST_GRADIENT_BOOSTING].estimator_
    standalone = fit_estimator(
        FAMILY_HIST_GRADIENT_BOOSTING,
        {**BASE_PARAMS[FAMILY_HIST_GRADIENT_BOOSTING], "weighting": WEIGHTING_BALANCED},
        X,
        y,
    )
    np.testing.assert_allclose(inside.predict_proba(X), standalone.predict_proba(X))


@pytest.mark.parametrize(
    "modes",
    [
        dict(zip(BASE_PARAMS, combo, strict=True))
        for combo in itertools.product(WEIGHTING_MODES, repeat=3)
    ],
)
def test_every_weighting_combination_keeps_each_base_independent(modes):
    """Las 8 combinaciones de modos: cada base interna coincide exactamente
    con su ajuste standalone en su propio modo."""
    X, y = _imbalanced_dataset()
    voting = fit_soft_voting(_base_configs(modes), X, y)
    for family, mode in modes.items():
        inside = voting.named_estimators_[family].estimator_
        standalone = fit_estimator(family, {**BASE_PARAMS[family], "weighting": mode}, X, y)
        np.testing.assert_allclose(
            inside.predict_proba(X),
            standalone.predict_proba(X),
            err_msg=f"{family} con modo {mode} no coincide con su ajuste independiente",
        )


def test_ensemble_probability_is_the_exact_mean_of_the_three_bases():
    X, y = _imbalanced_dataset()
    voting = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    parts = [voting.named_estimators_[family].predict_proba(X)[:, 1] for family in BASE_PARAMS]
    expected = sum(parts) / 3.0
    np.testing.assert_allclose(voting.predict_proba(X)[:, 1], expected)


def test_mixed_and_all_unweighted_do_not_collapse_to_the_same_fit():
    """Regresión del defecto original: un único `sample_weight` global hacía
    que una combinación mixta se ajustara como si fuera toda sin ponderar."""
    X, y = _imbalanced_dataset()
    mixed = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    all_unweighted = fit_soft_voting(
        _base_configs(dict.fromkeys(BASE_PARAMS, WEIGHTING_NONE)), X, y
    )
    assert not np.allclose(mixed.predict_proba(X), all_unweighted.predict_proba(X))


def test_weights_are_fixed_and_uniform():
    voting = build_soft_voting_estimator(_base_configs(MIXED_MODES))
    assert voting.weights == pytest.approx([1 / 3, 1 / 3, 1 / 3])


def test_classes_are_exposed_and_probability_columns_follow_that_order():
    X, y = _imbalanced_dataset()
    voting = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    np.testing.assert_array_equal(voting.classes_, np.array([0, 1]))
    proba = voting.predict_proba(X)
    assert proba.shape == (len(y), 2)
    np.testing.assert_allclose(proba.sum(axis=1), np.ones(len(y)))


def test_predict_is_consistent_with_predict_proba():
    X, y = _imbalanced_dataset()
    voting = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    proba = voting.predict_proba(X)
    np.testing.assert_array_equal(voting.predict(X), voting.classes_[proba.argmax(axis=1)])


def test_probability_columns_are_aligned_when_a_base_sees_a_single_class():
    """Alineación explícita de clases: una base ajustada sobre `y` monoclase
    expone `classes_` de longitud 1 y no debe desalinear las columnas.

    Se excluye la Logistic Regression porque `lbfgs` rechaza por diseño un
    `y` monoclase; el ensamble parcial RF+HGB ejercita la misma alineación.
    """
    X, _ = _imbalanced_dataset()
    y_monoclass = np.ones(len(X), dtype=int)
    modes = {
        FAMILY_RANDOM_FOREST: WEIGHTING_NONE,
        FAMILY_HIST_GRADIENT_BOOSTING: WEIGHTING_BALANCED,
    }
    configs = {
        family: ModelConfig(family, {**BASE_PARAMS[family], "weighting": mode})
        for family, mode in modes.items()
    }
    voting = fit_soft_voting(configs, X, y_monoclass)
    np.testing.assert_array_equal(voting.classes_, np.array([1]))
    proba = voting.predict_proba(X)
    assert proba.shape == (len(X), 1)
    np.testing.assert_allclose(proba.sum(axis=1), np.ones(len(X)))


def test_probability_columns_stay_aligned_when_bases_see_different_class_sets():
    """Una base entrenada sobre ambas clases y otra sobre una sola conviven
    sin desalinear columnas: la de una clase aporta toda su masa a esa clase.
    """
    X, y = _imbalanced_dataset()
    rf = SelfWeightingClassifier(
        family=FAMILY_RANDOM_FOREST,
        model_params={**BASE_PARAMS[FAMILY_RANDOM_FOREST], "weighting": WEIGHTING_NONE},
    ).fit(X, y)
    voting = build_soft_voting_estimator(
        {FAMILY_RANDOM_FOREST: ModelConfig(FAMILY_RANDOM_FOREST, {})}
    )
    voting.classes_ = np.array([0, 1])
    aligned = voting._aligned_proba(np.ones((3, 1)), np.array([1]))
    np.testing.assert_allclose(aligned, np.array([[0.0, 1.0]] * 3))
    assert rf.classes_.tolist() == [0, 1]


def test_soft_voting_classifier_is_clonable_and_roundtrips_params():
    voting = build_soft_voting_estimator(_base_configs(MIXED_MODES))
    cloned = clone(voting)
    assert isinstance(cloned, SoftVotingClassifier)
    assert cloned.get_params()["base_configs"] == voting.get_params()["base_configs"]
    cloned.set_params(weights=[1 / 3, 1 / 3, 1 / 3])
    assert cloned.get_params()["weights"] == pytest.approx([1 / 3, 1 / 3, 1 / 3])


def test_self_weighting_classifier_is_clonable_and_computes_its_own_weights():
    wrapper = SelfWeightingClassifier(
        family=FAMILY_LOGISTIC_REGRESSION,
        model_params={**BASE_PARAMS[FAMILY_LOGISTIC_REGRESSION], "weighting": WEIGHTING_BALANCED},
    )
    cloned = clone(wrapper)
    assert cloned.get_params() == wrapper.get_params()

    X, y = _imbalanced_dataset()
    fitted = cloned.fit(X, y)
    standalone = fit_estimator(
        FAMILY_LOGISTIC_REGRESSION,
        {**BASE_PARAMS[FAMILY_LOGISTIC_REGRESSION], "weighting": WEIGHTING_BALANCED},
        X,
        y,
    )
    np.testing.assert_allclose(fitted.estimator_.model_.coef_, standalone.model_.coef_)


def test_fitting_is_deterministic_across_repeated_fits():
    X, y = _imbalanced_dataset()
    a = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    b = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    np.testing.assert_allclose(a.predict_proba(X), b.predict_proba(X))


def test_base_weighting_modes_are_exposed_for_serialization():
    X, y = _imbalanced_dataset()
    voting = fit_soft_voting(_base_configs(MIXED_MODES), X, y)
    assert voting.base_weighting_modes() == MIXED_MODES
