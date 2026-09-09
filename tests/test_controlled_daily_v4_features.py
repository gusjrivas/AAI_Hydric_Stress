from __future__ import annotations

import pandas as pd

from experiment_runner.controlled_daily_v4.config import STAGE_A_BOUNDS
from experiment_runner.controlled_daily_v4.features import (
    FEATURE_COLUMNS,
    build_feature_frame,
    build_target,
    compute_p20_threshold,
    select_eligible_rows,
)
from tests.controlled_daily_v4_fixtures import make_synthetic_daily_frame


def test_target_is_strictly_less_than_p20():
    future = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
    target = build_target(future, p20_threshold=0.3)
    assert target.tolist() == [1, 1, 0, 0, 0]


def test_equality_with_p20_produces_class_zero():
    future = pd.Series([0.3, 0.3, 0.3])
    target = build_target(future, p20_threshold=0.3)
    assert (target == 0).all()


def test_p20_threshold_uses_only_the_given_series():
    train_only = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
    p20 = compute_p20_threshold(train_only)
    # quantile(0.20) of this exact series, not influenced by any external data
    assert p20 == train_only.quantile(0.20)


def test_lags_and_rolling_are_causal_only():
    daily = make_synthetic_daily_frame(n_days=60, seed=1)
    frame = build_feature_frame(daily, "soil_moisture_0_to_7cm")

    perturbed = daily.copy()
    future_date = daily.index[50]
    perturbed.loc[future_date, "soil_moisture_0_to_7cm"] = 999.0
    frame_perturbed = build_feature_frame(perturbed, "soil_moisture_0_to_7cm")

    earlier_date = daily.index[10]
    row_before = frame.loc[earlier_date, ["lag1", "lag2", "lag3", "roll_mean_3", "roll_mean_7"]]
    row_before_perturbed = frame_perturbed.loc[
        earlier_date, ["lag1", "lag2", "lag3", "roll_mean_3", "roll_mean_7"]
    ]
    pd.testing.assert_series_equal(row_before, row_before_perturbed)


def test_future_soil_moisture_is_the_value_at_horizon_plus_3_days():
    daily = make_synthetic_daily_frame(n_days=20, seed=2)
    frame = build_feature_frame(daily, "soil_moisture_0_to_7cm")
    d0 = daily.index[0]
    d3 = daily.index[3]
    assert frame.loc[d0, "future_soil_moisture"] == daily.loc[d3, "soil_moisture_0_to_7cm"]
    assert frame.loc[d0, "target_timestamp"] == d3


def test_eligible_rows_respect_stage_a_target_window():
    daily = make_synthetic_daily_frame(n_days=400, seed=3)
    frame = build_feature_frame(daily, "soil_moisture_0_to_7cm")
    eligible = select_eligible_rows(frame, STAGE_A_BOUNDS)

    assert eligible["target_timestamp"].min() >= pd.Timestamp(STAGE_A_BOUNDS.target_start)
    assert eligible["target_timestamp"].max() <= pd.Timestamp(STAGE_A_BOUNDS.target_end)
    assert eligible[list(FEATURE_COLUMNS)].notna().all().all()
    assert eligible["future_soil_moisture"].notna().all()


def test_eligible_rows_exclude_targets_outside_authorized_window():
    daily = make_synthetic_daily_frame(n_days=6, seed=4)
    # Con solo 6 días no alcanza el warm-up de 7 días de rolling: ninguna
    # fila puede tener features completas todavía.
    frame = build_feature_frame(daily, "soil_moisture_0_to_7cm")
    eligible = select_eligible_rows(frame, STAGE_A_BOUNDS)
    assert len(eligible) == 0


def test_eligible_rows_include_the_first_authorized_boundary_row():
    daily = make_synthetic_daily_frame(n_days=10, seed=4)
    # 2015-01-01..2015-01-10: la primera fila con features completas es
    # 2015-01-07 (rolling de 7 días), cuyo target (2015-01-10) coincide
    # exactamente con STAGE_A_BOUNDS.target_start -- debe quedar incluida.
    frame = build_feature_frame(daily, "soil_moisture_0_to_7cm")
    eligible = select_eligible_rows(frame, STAGE_A_BOUNDS)
    assert len(eligible) == 1
    assert str(eligible["feature_timestamp"].iloc[0].date()) == "2015-01-07"
