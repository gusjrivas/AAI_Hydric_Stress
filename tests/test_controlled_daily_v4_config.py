from __future__ import annotations

import pytest

from experiment_runner.controlled_daily_v4.config import (
    GAP,
    HORIZON_DAYS,
    INNER_N_SPLITS,
    OUTER_N_SPLITS,
    STAGE_A,
    STAGE_A_BOUNDS,
    STAGE_B,
    STAGE_C,
    UnsupportedStageError,
    require_stage_a,
)


def test_stage_a_bounds_match_protocol():
    assert str(STAGE_A_BOUNDS.emission_start) == "2015-01-07"
    assert str(STAGE_A_BOUNDS.emission_end) == "2022-12-28"
    assert str(STAGE_A_BOUNDS.target_start) == "2015-01-10"
    assert str(STAGE_A_BOUNDS.target_end) == "2022-12-31"


def test_horizon_gap_and_splits_are_normative():
    assert HORIZON_DAYS == 3
    assert GAP == 3
    assert OUTER_N_SPLITS == 3
    assert INNER_N_SPLITS == 3


def test_require_stage_a_accepts_a():
    require_stage_a(STAGE_A)


@pytest.mark.parametrize("stage", [STAGE_B, STAGE_C, "X"])
def test_require_stage_a_rejects_everything_else(stage):
    with pytest.raises(UnsupportedStageError):
        require_stage_a(stage)
