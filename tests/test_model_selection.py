import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier

from predictive_modeling.model_selection import select_best_candidate


def _separable_dataset(n=120, seed=0):
    rng = np.random.default_rng(seed)
    feature = rng.normal(0, 1, size=n)
    target = (feature > 0).astype(int)
    X = pd.DataFrame({"feature": feature})
    y = pd.Series(target, name="stress_label")
    return X, y


def test_select_best_candidate_uses_default_candidates_and_grids():
    X, y = _separable_dataset()

    result = select_best_candidate(X, y, n_splits=4)

    assert result["model_name"] in {"logistic_regression", "random_forest"}
    assert hasattr(result["model"], "predict_proba")
    assert "cv_mean_score" in result
    assert "cv_std_score" in result


def test_select_best_candidate_picks_the_higher_cv_mean_score():
    X, y = _separable_dataset(n=150, seed=1)

    candidates = {
        "bad": DummyClassifier(strategy="constant", constant=0),
        "good": RandomForestClassifier(random_state=0),
    }
    param_grids = {"bad": {}, "good": {"n_estimators": [50]}}

    result = select_best_candidate(X, y, candidates=candidates, param_grids=param_grids, n_splits=4)

    assert result["model_name"] == "good"


def test_select_best_candidate_breaks_exact_ties_deterministically_not_by_name_preference():
    X, y = _separable_dataset(n=150, seed=2)

    # ambos candidatos son el mismo clasificador constante -> cv_mean_score y
    # cv_std_score idénticos para los dos, un empate exacto genuino.
    candidates = {
        "logistic_regression": DummyClassifier(strategy="constant", constant=0),
        "random_forest": DummyClassifier(strategy="constant", constant=0),
    }
    param_grids = {"logistic_regression": {}, "random_forest": {}}

    result = select_best_candidate(X, y, candidates=candidates, param_grids=param_grids, n_splits=4)

    # el desempate ya no prefiere "random_forest" por nombre: es determinístico
    # (orden alfabético) y queda documentado en el resultado, no oculto.
    assert result["model_name"] == "logistic_regression"
    assert result["selection_warning"] is not None
    assert "empate" in result["selection_warning"].lower()


def test_select_best_candidate_reports_folds_without_positive_validation_examples():
    # un único positivo muy temprano (para que los folds de entrenamiento
    # siempre tengan al menos un caso de cada clase y los modelos puedan
    # ajustarse) y el resto de los positivos concentrados al final -> los
    # primeros folds de validación quedan sin ningún positivo.
    n = 60
    y = pd.Series([1] + [0] * 49 + [1] * 10)
    X = pd.DataFrame({"feature": range(n)})

    result = select_best_candidate(X, y, n_splits=3)

    assert "fold_diagnostics" in result
    assert len(result["fold_diagnostics"]) == 3
    assert result["selection_warning"] is not None
    assert "positivo" in result["selection_warning"].lower()


def test_select_best_candidate_has_no_warning_when_folds_are_well_balanced_and_not_tied():
    X, y = _separable_dataset(n=150, seed=1)

    candidates = {
        "bad": DummyClassifier(strategy="constant", constant=0),
        "good": RandomForestClassifier(random_state=0),
    }
    param_grids = {"bad": {}, "good": {"n_estimators": [50]}}

    result = select_best_candidate(X, y, candidates=candidates, param_grids=param_grids, n_splits=4)

    assert result["selection_warning"] is None


def test_select_best_candidate_accepts_gap_and_forwards_it_to_fold_diagnostics():
    X, y = _separable_dataset(n=150, seed=0)

    result_no_gap = select_best_candidate(X, y, n_splits=4, gap=0)
    result_with_gap = select_best_candidate(X, y, n_splits=4, gap=5)

    def _train_size(result, fold=0):
        d = result["fold_diagnostics"][fold]
        return d["train_positives"] + d["train_negatives"]

    assert _train_size(result_with_gap) < _train_size(result_no_gap)
