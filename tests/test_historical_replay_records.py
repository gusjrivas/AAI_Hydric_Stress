from datetime import date

import pytest

from historical_replay.records import (
    DuplicateIdentityError,
    ForeignIdentityError,
    HorizonMismatchError,
    InvalidBooleanError,
    InvalidClassError,
    InvalidHorizonError,
    InvalidProbabilityError,
    MalformedRowError,
    MissingIdentityError,
    PredictionIdentity,
    TargetObservedCoherenceError,
    build_records,
)


def _row(**overrides):
    row = {
        "experiment_id": "4",
        "run_id": "1157696b7bb941e394c5af530c762b07",
        "config_name": "base",
        "seed": 4,
        "timestamp": "2024-10-19T00:00:00.000",
        "target_timestamp": "2024-10-22T00:00:00.000",
        "target_observed": True,
        "y_true": 1.0,
        "y_proba": 0.44,
        "y_pred": 0,
        "persistence": 1,
        "majority_class": 0,
        "always_stress": 1,
    }
    row.update(overrides)
    return row


def test_build_records_produces_stable_identity_with_normalized_date():
    records = build_records([_row()], horizon_days=3)

    assert len(records) == 1
    record = records[0]
    assert record.identity == PredictionIdentity(
        experiment_id="4",
        run_id="1157696b7bb941e394c5af530c762b07",
        config_name="base",
        seed=4,
        timestamp_origen=date(2024, 10, 19),
    )
    assert record.target_timestamp == date(2024, 10, 22)


def test_build_records_copies_archived_values_without_recalculating():
    records = build_records([_row()], horizon_days=3)

    record = records[0]
    assert record.y_true == 1.0
    assert record.y_proba == 0.44
    assert record.y_pred == 0
    assert record.target_observed is True
    assert dict(record.baselines) == {
        "persistence": 1,
        "majority_class": 0,
        "always_stress": 1,
    }


def test_baselines_are_immutable_even_though_the_record_is_frozen():
    record = build_records([_row()], horizon_days=3)[0]

    with pytest.raises(TypeError):
        record.baselines["persistence"] = 999


def test_duplicated_full_identity_is_rejected():
    row = _row()

    with pytest.raises(DuplicateIdentityError):
        build_records([row, dict(row)], horizon_days=3)


def test_equivalent_date_representations_are_treated_as_the_same_identity():
    first = _row(timestamp="2024-10-19T00:00:00.000")
    second = _row(timestamp="2024-10-19")  # misma fecha, otra representación

    with pytest.raises(DuplicateIdentityError):
        build_records([first, second], horizon_days=3)


def test_distinct_runs_sharing_target_timestamp_is_not_treated_as_duplicate():
    first = _row(run_id="run-a", timestamp="2024-10-19T00:00:00.000")
    second = _row(run_id="run-b", timestamp="2024-10-19T00:00:00.000")

    records = build_records([first, second], horizon_days=3)

    assert len(records) == 2
    assert records[0].identity != records[1].identity


def test_horizon_incompatible_row_is_rejected():
    row = _row(target_timestamp="2024-10-23T00:00:00.000")  # +4 days, not +3

    with pytest.raises(HorizonMismatchError):
        build_records([row], horizon_days=3)


def test_non_positive_horizon_is_rejected():
    with pytest.raises(InvalidHorizonError):
        build_records([_row()], horizon_days=0)


def test_records_are_sorted_chronologically_regardless_of_input_order():
    later = _row(
        run_id="run-a",
        timestamp="2024-10-20T00:00:00.000",
        target_timestamp="2024-10-23T00:00:00.000",
    )
    earlier = _row(
        run_id="run-a",
        timestamp="2024-10-19T00:00:00.000",
        target_timestamp="2024-10-22T00:00:00.000",
    )

    records = build_records([later, earlier], horizon_days=3)

    assert [r.identity.timestamp_origen for r in records] == [
        date(2024, 10, 19),
        date(2024, 10, 20),
    ]


def test_row_run_id_cannot_silently_override_the_authorized_run():
    row = _row(run_id="rogue-run-id")

    with pytest.raises(ForeignIdentityError):
        build_records(
            [row],
            experiment_id="4",
            run_id="1157696b7bb941e394c5af530c762b07",
            config_name="base",
            seed=4,
            horizon_days=3,
        )


def test_missing_required_identity_is_rejected_not_stringified():
    row = _row()
    del row["run_id"]

    with pytest.raises(MissingIdentityError):
        build_records([row], horizon_days=3)


def test_textual_boolean_for_target_observed_is_rejected():
    row = _row(target_observed="true")

    with pytest.raises(InvalidBooleanError):
        build_records([row], horizon_days=3)


def test_integer_for_target_observed_is_rejected():
    row = _row(target_observed=1)

    with pytest.raises(InvalidBooleanError):
        build_records([row], horizon_days=3)


def test_y_proba_out_of_range_is_rejected():
    row = _row(y_proba=1.5)

    with pytest.raises(InvalidProbabilityError):
        build_records([row], horizon_days=3)


def test_y_proba_non_finite_is_rejected():
    row = _row(y_proba=float("nan"))

    with pytest.raises(InvalidProbabilityError):
        build_records([row], horizon_days=3)


def test_y_pred_outside_admitted_classes_is_rejected():
    row = _row(y_pred=2)

    with pytest.raises(InvalidClassError):
        build_records([row], horizon_days=3)


def test_target_observed_true_requires_y_true_present():
    row = _row(target_observed=True, y_true=None)

    with pytest.raises(TargetObservedCoherenceError):
        build_records([row], horizon_days=3)


def test_target_observed_false_requires_y_true_absent():
    row = _row(target_observed=False, y_true=1.0)

    with pytest.raises(TargetObservedCoherenceError):
        build_records([row], horizon_days=3)


def test_target_observed_false_with_no_y_true_is_accepted():
    row = _row(target_observed=False, y_true=None)

    records = build_records([row], horizon_days=3)

    assert records[0].target_observed is False
    assert records[0].y_true is None


def test_malformed_row_missing_required_field_is_rejected():
    row = _row()
    del row["target_timestamp"]

    with pytest.raises(MalformedRowError):
        build_records([row], horizon_days=3)
