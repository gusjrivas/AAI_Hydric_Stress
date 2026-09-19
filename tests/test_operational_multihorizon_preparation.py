from copy import deepcopy

import pandas as pd
import pytest

from predictive_modeling.operational_preparation import (
    DateRange,
    TemporalCutPlan,
    add_calendar_target,
    add_multihorizon_targets,
    partition_labeled_horizon,
    validate_utc_calendar,
)


def _frame(dates, moisture=None):
    values = moisture if moisture is not None else [0.4] * len(dates)
    return pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": values,
            "feature": list(range(len(dates))),
        }
    )


def test_exact_calendar_targets_are_independent_for_h1_h2_h3():
    frame = _frame(
        pd.date_range("2024-01-29", periods=7, freq="D"),
        [0.5, 0.4, 0.1, 0.6, 0.2, 0.7, 0.8],
    )

    targets = add_multihorizon_targets(
        frame, column="soil_moisture", thresholds={1: 0.3, 2: 0.3, 3: 0.3}
    )

    source = pd.Timestamp("2024-01-30")
    assert targets[1].set_index("timestamp").loc[source, "stress_label"] == 1
    assert targets[2].set_index("timestamp").loc[source, "stress_label"] == 0
    assert targets[3].set_index("timestamp").loc[source, "stress_label"] == 1
    assert targets[3].set_index("timestamp").loc[source, "target_date"] == pd.Timestamp(
        "2024-02-02"
    )


def test_missing_date_is_not_compacted_to_the_next_stored_row():
    frame = _frame(
        ["2024-01-01", "2024-01-03", "2024-01-04"],
        [0.5, 0.1, 0.6],
    )

    labeled = add_calendar_target(
        frame, column="soil_moisture", horizon_days=1, threshold=0.3
    ).set_index("timestamp")

    assert pd.isna(labeled.loc[pd.Timestamp("2024-01-01"), "stress_label"])
    assert not labeled.loc[pd.Timestamp("2024-01-01"), "supervised_eligible"]
    assert labeled.loc[pd.Timestamp("2024-01-01"), "inference_candidate"]
    assert labeled.loc[pd.Timestamp("2024-01-03"), "stress_label"] == 0


def test_missing_future_measurement_is_never_converted_to_a_negative_label():
    frame = _frame(
        ["2024-12-30", "2024-12-31", "2025-01-01"],
        [0.4, pd.NA, 0.2],
    )
    labeled = add_calendar_target(
        frame, column="soil_moisture", horizon_days=1, threshold=0.3
    ).set_index("timestamp")

    december_30 = labeled.loc[pd.Timestamp("2024-12-30")]
    assert pd.isna(december_30["stress_label"])
    assert not december_30["target_observed"]
    assert not december_30["supervised_eligible"]
    assert december_30["inference_candidate"]
    assert labeled.loc[pd.Timestamp("2024-12-31"), "stress_label"] == 1


def test_utc_calendar_handles_month_and_year_boundaries():
    frame = _frame(
        [
            "2024-12-30T00:00:00Z",
            "2024-12-31T00:00:00Z",
            "2025-01-01T00:00:00Z",
            "2025-01-02T00:00:00Z",
        ],
        [0.5, 0.5, 0.5, 0.1],
    )

    labeled = add_calendar_target(
        frame, column="soil_moisture", horizon_days=3, threshold=0.3
    ).set_index("timestamp")

    assert labeled.loc[pd.Timestamp("2024-12-30"), "target_date"] == pd.Timestamp("2025-01-02")
    assert labeled.loc[pd.Timestamp("2024-12-30"), "stress_label"] == 1


@pytest.mark.parametrize(
    "dates",
    [
        ["2024-01-01", "2024-01-01"],
        ["2024-01-01", "not-a-date"],
        ["2024-01-01T03:00:00Z", "2024-01-02T00:00:00Z"],
    ],
)
def test_calendar_rejects_duplicates_invalid_dates_and_subdaily_values(dates):
    with pytest.raises(ValueError):
        validate_utc_calendar(_frame(dates))


def _cuts():
    return TemporalCutPlan(
        allowed_data=DateRange("2024-01-01", "2024-01-15"),
        train=DateRange("2024-01-01", "2024-01-05"),
        calibration=DateRange("2024-01-06", "2024-01-10"),
        evaluation=DateRange("2024-01-11", "2024-01-14"),
        inference_as_of="2024-01-15",
    )


@pytest.mark.parametrize("horizon", [1, 2, 3])
def test_partition_purges_by_target_date_at_every_temporal_boundary(horizon):
    frame = _frame(pd.date_range("2024-01-01", periods=15, freq="D"))
    labeled = add_calendar_target(
        frame, column="soil_moisture", horizon_days=horizon, threshold=0.3
    )

    prepared = partition_labeled_horizon(labeled, cuts=_cuts())

    for part, bounds in (
        (prepared.train, _cuts().train),
        (prepared.calibration, _cuts().calibration),
        (prepared.evaluation, _cuts().evaluation),
    ):
        assert part["timestamp"].between(pd.Timestamp(bounds.start), pd.Timestamp(bounds.end)).all()
        assert (
            part["target_date"].between(pd.Timestamp(bounds.start), pd.Timestamp(bounds.end)).all()
        )
    assert prepared.train["timestamp"].max() == pd.Timestamp("2024-01-05") - pd.Timedelta(
        days=horizon
    )
    assert prepared.calibration["timestamp"].max() == pd.Timestamp("2024-01-10") - pd.Timedelta(
        days=horizon
    )
    assert prepared.evaluation["timestamp"].max() == pd.Timestamp("2024-01-14") - pd.Timedelta(
        days=horizon
    )
    assert pd.Timestamp("2024-01-15") in set(prepared.inference["timestamp"])


def test_labeled_rows_outside_declared_data_bounds_are_rejected():
    frame = _frame(pd.date_range("2023-12-31", periods=16, freq="D"))
    labeled = add_calendar_target(frame, column="soil_moisture", horizon_days=1, threshold=0.3)

    with pytest.raises(ValueError, match="fuera de allowed_data"):
        partition_labeled_horizon(labeled, cuts=_cuts())


def test_future_change_only_changes_the_corresponding_target_not_prior_inputs():
    base = _frame(
        pd.date_range("2024-01-01", periods=15, freq="D"),
        [0.4] * 15,
    )
    modified = deepcopy(base)
    modified.loc[7, "soil_moisture"] = 0.1  # 2024-01-08, target de h=2 para 2024-01-06

    base_labeled = add_calendar_target(base, column="soil_moisture", horizon_days=2, threshold=0.3)
    changed_labeled = add_calendar_target(
        modified, column="soil_moisture", horizon_days=2, threshold=0.3
    )
    base_prepared = partition_labeled_horizon(
        base_labeled, cuts=_cuts(), required_inference_columns=("feature",)
    )
    changed_prepared = partition_labeled_horizon(
        changed_labeled, cuts=_cuts(), required_inference_columns=("feature",)
    )

    cutoff = pd.Timestamp("2024-01-06")
    columns = ["timestamp", "feature"]
    pd.testing.assert_frame_equal(
        base_prepared.inference.loc[
            base_prepared.inference.timestamp <= cutoff, columns
        ].reset_index(drop=True),
        changed_prepared.inference.loc[
            changed_prepared.inference.timestamp <= cutoff, columns
        ].reset_index(drop=True),
    )
    changed_dates = base_labeled.loc[
        base_labeled["stress_label"].ne(changed_labeled["stress_label"]).fillna(False),
        "timestamp",
    ].tolist()
    assert changed_dates == [pd.Timestamp("2024-01-06")]


def test_invalid_or_implicit_threshold_is_rejected():
    frame = _frame(["2024-01-01", "2024-01-02"])
    with pytest.raises(ValueError, match="threshold"):
        add_calendar_target(frame, column="soil_moisture", horizon_days=1, threshold=float("nan"))
