"""Recorte temporal previo a la construcción de features (protocolo, sección 5).

El pipeline procesa, en cada etapa, solo el período autorizado más la historia
causal estrictamente necesaria: no se calculan features ni `future_soil_moisture`
sobre toda la serie 2015-2025 para filtrar después. Estos tests instrumentan el
constructor de features para comprobar qué se le entrega realmente.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4 import stage_a_runner
from experiment_runner.controlled_daily_v4.config import (
    LAGS,
    PRIMARY_DEPTH_COLUMN,
    ROLLING_WINDOWS,
    STAGE_A_BOUNDS,
    HistGradientBoostingGridSpec,
    LogisticRegressionGridSpec,
    ProtocolConfig,
    RandomForestGridSpec,
)
from experiment_runner.controlled_daily_v4.features import (
    FEATURE_COLUMNS,
    required_history_days,
    restrict_to_stage_window,
)
from experiment_runner.controlled_daily_v4.stage_a_runner import build_eligible_frame, run_stage_a
from tests.controlled_daily_v4_fixtures import make_synthetic_daily_frame

FAST_CONFIG = ProtocolConfig(
    bootstrap_replicas=15,
    logistic_regression_grid=LogisticRegressionGridSpec(C=(1.0,)),
    random_forest_grid=RandomForestGridSpec(
        n_estimators=(25,), max_depth=(4,), min_samples_leaf=(5,)
    ),
    hist_gradient_boosting_grid=HistGradientBoostingGridSpec(
        learning_rate=(0.1,), max_iter=(25,), max_leaf_nodes=(15,), l2_regularization=(0.0,)
    ),
)

POISON = 1e9


def _series_through_2025(seed=9):
    """Serie diaria sintética 2015-01-01 -> más allá de 2025, para que el
    recorte de la Etapa A tenga algo real que descartar."""
    return make_synthetic_daily_frame(n_days=4020, seed=seed)


def _poison_after_stage_a(daily: pd.DataFrame) -> pd.DataFrame:
    poisoned = daily.copy()
    mask = pd.to_datetime(poisoned.index) > pd.Timestamp(STAGE_A_BOUNDS.target_end)
    poisoned.loc[mask, :] = POISON
    return poisoned


def test_required_history_covers_the_longest_causal_window():
    # rolling de 7 días necesita 6 observaciones previas; lag 3 solo 3.
    assert required_history_days(LAGS, ROLLING_WINDOWS) == 6


def test_restriction_keeps_only_the_authorized_window_plus_causal_history():
    daily = _series_through_2025()
    restricted = restrict_to_stage_window(daily, STAGE_A_BOUNDS)
    index = pd.to_datetime(restricted.index)
    assert index.min() == pd.Timestamp("2015-01-01")
    assert index.max() == pd.Timestamp(STAGE_A_BOUNDS.target_end)


def test_restriction_still_allows_the_first_authorized_emission():
    """El recorte no puede comerse el warm-up: la emisión 2015-01-07 debe
    seguir teniendo `roll_mean_7` completa."""
    daily = _series_through_2025()
    eligible = build_eligible_frame(daily, PRIMARY_DEPTH_COLUMN)
    assert str(pd.to_datetime(eligible["feature_timestamp"]).min().date()) == "2015-01-07"
    assert eligible[list(FEATURE_COLUMNS)].notna().all().all()


def test_feature_builder_never_receives_rows_after_the_stage_cutoff(monkeypatch):
    daily = _poison_after_stage_a(_series_through_2025())
    received: list[pd.Timestamp] = []
    original = stage_a_runner.build_feature_frame

    def spy(daily_series, depth_column):
        received.append(pd.to_datetime(daily_series.index).max())
        return original(daily_series, depth_column)

    monkeypatch.setattr(stage_a_runner, "build_feature_frame", spy)
    build_eligible_frame(daily, PRIMARY_DEPTH_COLUMN)

    assert received, "el constructor de features debe haber sido invocado"
    assert max(received) == pd.Timestamp(STAGE_A_BOUNDS.target_end)


def test_feature_builder_never_receives_poisoned_values(monkeypatch):
    daily = _poison_after_stage_a(_series_through_2025())
    seen_max: list[float] = []
    original = stage_a_runner.build_feature_frame

    def spy(daily_series, depth_column):
        seen_max.append(float(np.nanmax(daily_series[depth_column].to_numpy())))
        return original(daily_series, depth_column)

    monkeypatch.setattr(stage_a_runner, "build_feature_frame", spy)
    build_eligible_frame(daily, PRIMARY_DEPTH_COLUMN)

    assert max(seen_max) < POISON


def test_eligible_frame_has_no_row_beyond_the_authorized_boundaries():
    daily = _poison_after_stage_a(_series_through_2025())
    eligible = build_eligible_frame(daily, PRIMARY_DEPTH_COLUMN)
    assert pd.to_datetime(eligible["feature_timestamp"]).max() <= pd.Timestamp("2022-12-28")
    assert pd.to_datetime(eligible["target_timestamp"]).max() <= pd.Timestamp("2022-12-31")


def test_poisoned_holdout_does_not_change_the_eligible_frame():
    daily = _series_through_2025()
    clean = build_eligible_frame(daily, PRIMARY_DEPTH_COLUMN)
    poisoned = build_eligible_frame(_poison_after_stage_a(daily), PRIMARY_DEPTH_COLUMN)

    assert len(clean) == len(poisoned)
    columns = [*FEATURE_COLUMNS, "future_soil_moisture"]
    np.testing.assert_allclose(clean[columns].to_numpy(), poisoned[columns].to_numpy())
    pd.testing.assert_series_equal(
        pd.to_datetime(clean["feature_timestamp"]).reset_index(drop=True),
        pd.to_datetime(poisoned["feature_timestamp"]).reset_index(drop=True),
    )


@pytest.mark.parametrize("depth", [PRIMARY_DEPTH_COLUMN])
def test_poisoned_holdout_changes_neither_folds_nor_p20_nor_selection(depth):
    daily = make_synthetic_daily_frame(n_days=1500, seed=4)
    clean = run_stage_a(daily, depth, FAST_CONFIG)
    poisoned = run_stage_a(_poison_after_stage_a(daily), depth, FAST_CONFIG)

    assert [len(f.train) for f in clean.outer_folds] == [len(f.train) for f in poisoned.outer_folds]
    assert [len(f.validation) for f in clean.outer_folds] == [
        len(f.validation) for f in poisoned.outer_folds
    ]
    for family, results in clean.per_family_outer_results.items():
        other = poisoned.per_family_outer_results[family]
        assert [r.p20_train for r in results] == [r.p20_train for r in other]
        for a, b in zip(results, other, strict=True):
            np.testing.assert_array_equal(a.y_true, b.y_true)
            np.testing.assert_allclose(a.y_score, b.y_score)

    assert clean.selection.outcome == poisoned.selection.outcome
    assert clean.selection.selected_family == poisoned.selection.selected_family
    assert clean.selection.global_mcc_by_family == poisoned.selection.global_mcc_by_family
