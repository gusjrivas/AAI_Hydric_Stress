from __future__ import annotations

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.selection import (
    OUTCOME_NO_STABLE_WINNER,
    OUTCOME_NO_VALID_SELECTION,
    OUTCOME_STABLE_WINNER,
    CandidateOOF,
    is_practically_equivalent,
    select_family,
)


def _make_candidate(family, y_true, y_pred, segment_ids):
    frame = pd.DataFrame({"segment_id": segment_ids})
    return CandidateOOF(
        family=family,
        y_true=y_true,
        y_pred=y_pred,
        y_score=y_pred.astype(float),
        frame_with_segment_id=frame,
    )


def _segments(n, n_segments=2):
    size = n // n_segments
    ids = []
    for i in range(n_segments):
        ids += [f"outer_fold_{i + 1}"] * size
    ids += [f"outer_fold_{n_segments}"] * (n - len(ids))
    return ids


def test_stable_winner_when_one_candidate_is_clearly_better():
    rng = np.random.default_rng(0)
    n = 120
    y_true = (rng.random(n) < 0.3).astype(int)
    segments = _segments(n)

    y_pred_good = y_true.copy()
    flip = rng.random(n) < 0.35
    y_pred_bad = np.where(flip, 1 - y_true, y_true)

    candidates = {
        "logistic_regression": _make_candidate("logistic_regression", y_true, y_pred_bad, segments),
        "random_forest": _make_candidate("random_forest", y_true, y_pred_bad, segments),
        "hist_gradient_boosting_classifier": _make_candidate(
            "hist_gradient_boosting_classifier", y_true, y_pred_bad, segments
        ),
        "soft_voting": _make_candidate("soft_voting", y_true, y_pred_good, segments),
    }

    result = select_family(candidates, delta=0.05, n_replicas=50, seed=1)
    assert result.outcome == OUTCOME_STABLE_WINNER
    assert result.stable_winner == "soft_voting"
    assert result.selected_family == "soft_voting"


def test_practical_tie_falls_back_to_simplicity_not_superiority():
    rng = np.random.default_rng(1)
    n = 120
    y_true = (rng.random(n) < 0.3).astype(int)
    segments = _segments(n)
    y_pred = y_true.copy()  # los cuatro candidatos predicen exactamente igual

    candidates = {
        "logistic_regression": _make_candidate("logistic_regression", y_true, y_pred, segments),
        "random_forest": _make_candidate("random_forest", y_true, y_pred, segments),
        "hist_gradient_boosting_classifier": _make_candidate(
            "hist_gradient_boosting_classifier", y_true, y_pred, segments
        ),
        "soft_voting": _make_candidate("soft_voting", y_true, y_pred, segments),
    }

    result = select_family(candidates, delta=0.05, n_replicas=50, seed=1)
    assert result.outcome == OUTCOME_NO_STABLE_WINNER
    assert result.stable_winner is None
    # Empatan los cuatro; el desempate elige el más simple (LR).
    assert result.selected_family == "logistic_regression"
    assert "simplicidad" in result.selection_reason or "simplicity" in result.selection_reason
    assert set(result.equivalence_set) == set(candidates)


def test_monoclass_global_oof_yields_no_valid_selection():
    n = 50
    y_true = np.zeros(n, dtype=int)
    y_pred = np.zeros(n, dtype=int)
    segments = _segments(n)
    candidates = {
        "logistic_regression": _make_candidate("logistic_regression", y_true, y_pred, segments),
        "random_forest": _make_candidate("random_forest", y_true, y_pred, segments),
        "hist_gradient_boosting_classifier": _make_candidate(
            "hist_gradient_boosting_classifier", y_true, y_pred, segments
        ),
        "soft_voting": _make_candidate("soft_voting", y_true, y_pred, segments),
    }
    result = select_family(candidates, delta=0.05, n_replicas=50, seed=1)
    assert result.outcome == OUTCOME_NO_VALID_SELECTION
    assert result.selected_family is None


def test_practical_equivalence_requires_the_interval_to_contain_zero():
    """Protocolo, sección 8: un candidato entra al conjunto de equivalencia
    si su diferencia es `< δ` o si su intervalo pareado *incluye el cero*.
    Un intervalo íntegramente negativo no incluye el cero y por lo tanto no
    basta por sí solo para declarar equivalencia práctica."""
    # Diferencia menor que delta -> equivalente, sin importar el intervalo.
    assert is_practically_equivalent(diff=0.01, interval=(0.2, 0.5), delta=0.05)
    # Diferencia >= delta pero el intervalo cruza el cero -> equivalente.
    assert is_practically_equivalent(diff=0.20, interval=(-0.1, 0.4), delta=0.05)
    # Diferencia >= delta y el intervalo es estrictamente positivo -> no.
    assert not is_practically_equivalent(diff=0.20, interval=(0.05, 0.4), delta=0.05)
    # Diferencia >= delta y el intervalo es íntegramente negativo: no incluye
    # el cero, de modo que no habilita equivalencia práctica.
    assert not is_practically_equivalent(diff=0.20, interval=(-0.4, -0.05), delta=0.05)
    # El cero exactamente en un borde cuenta como incluido.
    assert is_practically_equivalent(diff=0.20, interval=(0.0, 0.4), delta=0.05)
    assert is_practically_equivalent(diff=0.20, interval=(-0.4, 0.0), delta=0.05)


def test_selection_exposes_bootstrap_diagnostics_per_pair():
    rng = np.random.default_rng(5)
    n = 200
    y_true = (rng.random(n) < 0.35).astype(int)
    segments = _segments(n)
    y_pred = np.where(rng.random(n) < 0.2, 1 - y_true, y_true)
    candidates = {
        f: _make_candidate(f, y_true, y_pred, segments)
        for f in (
            "logistic_regression",
            "random_forest",
            "hist_gradient_boosting_classifier",
            "soft_voting",
        )
    }
    result = select_family(candidates, delta=0.05, n_replicas=15, seed=20250109)
    assert result.bootstrap_diagnostics, "la selección debe registrar diagnósticas por par"
    for key, diagnostics in result.bootstrap_diagnostics.items():
        assert len(key) == 2
        assert diagnostics.replicas_requested == 15
        assert diagnostics.block_length == 30
        assert diagnostics.seed == 20250109
        assert diagnostics.n_segments == 2
        assert diagnostics.replicas_valid + diagnostics.replicas_discarded == 15
