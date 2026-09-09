from __future__ import annotations

import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.config import (
    GAP,
    INNER_N_SPLITS,
    OUTER_N_SPLITS,
    STAGE_A_BOUNDS,
)
from experiment_runner.controlled_daily_v4.features import build_feature_frame, select_eligible_rows
from experiment_runner.controlled_daily_v4.splits import (
    TemporalInvariantViolation,
    assert_temporal_invariant,
    generate_inner_folds,
    generate_outer_folds,
)
from tests.controlled_daily_v4_fixtures import make_synthetic_daily_frame


def _eligible(n_days=500, seed=7):
    daily = make_synthetic_daily_frame(n_days=n_days, seed=seed)
    frame = build_feature_frame(daily, "soil_moisture_0_to_7cm")
    return select_eligible_rows(frame, STAGE_A_BOUNDS)


def test_outer_folds_respect_temporal_invariant():
    eligible = _eligible()
    folds = generate_outer_folds(eligible, n_splits=OUTER_N_SPLITS, gap=GAP)
    assert len(folds) == OUTER_N_SPLITS
    for fold in folds:
        max_target_train = pd.to_datetime(fold.train["target_timestamp"]).max()
        min_feature_val = pd.to_datetime(fold.validation["feature_timestamp"]).min()
        assert max_target_train < min_feature_val


def test_inner_folds_respect_temporal_invariant_within_outer_train():
    eligible = _eligible()
    outer_folds = generate_outer_folds(eligible, n_splits=OUTER_N_SPLITS, gap=GAP)
    for outer_fold in outer_folds:
        inner_folds = generate_inner_folds(outer_fold.train, n_splits=INNER_N_SPLITS, gap=GAP)
        assert len(inner_folds) == INNER_N_SPLITS
        for inner_fold in inner_folds:
            max_target_train = pd.to_datetime(inner_fold.train["target_timestamp"]).max()
            min_feature_val = pd.to_datetime(inner_fold.validation["feature_timestamp"]).min()
            assert max_target_train < min_feature_val


def test_assert_temporal_invariant_raises_on_violation():
    train = pd.DataFrame({"target_timestamp": pd.to_datetime(["2020-01-05"])})
    val = pd.DataFrame({"feature_timestamp": pd.to_datetime(["2020-01-04"])})
    with pytest.raises(TemporalInvariantViolation):
        assert_temporal_invariant(train, val)


def test_outer_validation_sets_do_not_overlap_and_exclude_gap_rows():
    eligible = _eligible()
    folds = generate_outer_folds(eligible, n_splits=OUTER_N_SPLITS, gap=GAP)
    all_val_timestamps = pd.concat([f.validation["feature_timestamp"] for f in folds])
    assert not all_val_timestamps.duplicated().any()

    n = len(eligible)
    fold_size = n // (OUTER_N_SPLITS + 1)
    total_val_rows = sum(len(f.validation) for f in folds)
    # Cada fold deja `gap` filas fuera (ni entrenamiento ni validación); el
    # total de validación no puede alcanzar n - fold_size (lo que ocuparía
    # sin gaps).
    assert total_val_rows < n - fold_size
