from datetime import date

from historical_replay.projection import project
from historical_replay.records import build_records


def _record(target_observed=True, y_true=1.0):
    row = {
        "experiment_id": "4",
        "run_id": "1157696b7bb941e394c5af530c762b07",
        "config_name": "base",
        "seed": 4,
        "timestamp": "2024-10-19T00:00:00.000",
        "target_timestamp": "2024-10-22T00:00:00.000",
        "target_observed": target_observed,
        "y_true": y_true,
        "y_proba": 0.44,
        "y_pred": 0,
        "persistence": 1,
        "majority_class": 0,
        "always_stress": 1,
    }
    return build_records([row], horizon_days=3)[0]


def test_prediction_not_visible_before_its_origin():
    record = _record()

    view = project(record, date(2024, 10, 18))

    assert view is None


def test_prediction_visible_from_origin_without_observation():
    record = _record()

    view = project(record, date(2024, 10, 19))

    assert view is not None
    assert view["timestamp_origen"] == "2024-10-19"
    assert view["target_timestamp"] == "2024-10-22"
    assert view["y_proba"] == 0.44
    assert view["y_pred"] == 0
    assert "y_true" not in view
    assert "target_observed" not in view
    assert "persistence" not in view


def test_prediction_still_hidden_observation_the_day_before_target():
    record = _record()

    view = project(record, date(2024, 10, 21))

    assert view is not None
    assert "y_true" not in view


def test_observation_revealed_exactly_at_target_date():
    record = _record()

    view = project(record, date(2024, 10, 22))

    assert view["y_true"] == 1.0
    assert view["target_observed"] is True
    assert view["baselines"] == {"persistence": 1, "majority_class": 0, "always_stress": 1}


def test_jump_over_target_date_reveals_same_as_stepping_day_by_day():
    record = _record()

    jump_view = project(record, date(2024, 12, 31))
    stepwise_view = project(record, date(2024, 10, 22))

    assert jump_view["y_true"] == stepwise_view["y_true"]
    assert jump_view["target_observed"] == stepwise_view["target_observed"]


def test_target_not_observed_reveals_only_that_state_without_comparison():
    record = _record(target_observed=False, y_true=None)

    view = project(record, date(2024, 10, 22))

    assert view["target_observed"] is False
    assert "y_true" not in view
    assert "baselines" not in view


def test_rewinding_hides_the_observation_again_without_altering_the_record():
    record = _record()

    project(record, date(2024, 10, 22))  # revealed once
    view = project(record, date(2024, 10, 20))  # rewind before target

    assert "y_true" not in view
    assert record.y_true == 1.0  # internal record untouched


def test_re_advancing_reproduces_the_original_revelation():
    record = _record()

    first = project(record, date(2024, 10, 22))
    project(record, date(2024, 10, 20))  # rewind
    second = project(record, date(2024, 10, 22))  # advance again

    assert first == second


def test_projection_baselines_is_an_independent_copy():
    record = _record()

    view = project(record, date(2024, 10, 22))
    view["baselines"]["persistence"] = -1

    assert record.baselines["persistence"] == 1
