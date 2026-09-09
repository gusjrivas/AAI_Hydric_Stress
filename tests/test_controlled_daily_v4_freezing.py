from __future__ import annotations

import math

from experiment_runner.controlled_daily_v4.config import (
    FAMILY_LOGISTIC_REGRESSION,
    GAP,
    OUTER_N_SPLITS,
    STAGE_A_BOUNDS,
    LogisticRegressionGridSpec,
)
from experiment_runner.controlled_daily_v4.features import build_feature_frame, select_eligible_rows
from experiment_runner.controlled_daily_v4.freezing import fit_final_estimator, freeze_family
from experiment_runner.controlled_daily_v4.models import iter_logistic_regression_configs
from tests.controlled_daily_v4_fixtures import make_synthetic_daily_frame


def _eligible(n_days=500, seed=7):
    daily = make_synthetic_daily_frame(n_days=n_days, seed=seed)
    frame = build_feature_frame(daily, "soil_moisture_0_to_7cm")
    return select_eligible_rows(frame, STAGE_A_BOUNDS)


def test_freeze_family_picks_a_config_from_the_grid():
    eligible = _eligible()
    grid = LogisticRegressionGridSpec(C=(0.1, 1.0))
    configs = iter_logistic_regression_configs(grid)
    frozen = freeze_family(FAMILY_LOGISTIC_REGRESSION, configs, eligible, OUTER_N_SPLITS, GAP)
    assert frozen.family == FAMILY_LOGISTIC_REGRESSION
    assert frozen.config in configs
    assert len(frozen.fold_mcc) == OUTER_N_SPLITS


def test_freeze_family_never_uses_data_beyond_stage_a():
    eligible = _eligible()
    assert eligible["target_timestamp"].max().year <= 2022


def test_fit_final_estimator_refits_on_the_full_eligible_set():
    eligible = _eligible()
    grid = LogisticRegressionGridSpec(C=(1.0,))
    configs = iter_logistic_regression_configs(grid)
    frozen = freeze_family(FAMILY_LOGISTIC_REGRESSION, configs, eligible, OUTER_N_SPLITS, GAP)
    estimator, p20_train = fit_final_estimator(frozen, eligible)
    assert hasattr(estimator, "predict_proba")
    assert not math.isnan(p20_train)
    assert p20_train == eligible["future_soil_moisture"].quantile(0.20)
