"""Tests de `warnings_capture.collect_context_warnings` (hallazgo H-05)."""

from __future__ import annotations

import warnings

from experiment_runner.controlled_daily_v4.warnings_capture import collect_context_warnings


def test_records_a_warning_with_its_context():
    log: list[dict] = []
    with collect_context_warnings(log, family="logistic_regression", outer_fold_index=1):
        warnings.warn("algo no convergió", UserWarning)

    assert len(log) == 1
    entry = log[0]
    assert entry["family"] == "logistic_regression"
    assert entry["outer_fold_index"] == 1
    assert entry["category"] == "UserWarning"
    assert entry["message"] == "algo no convergió"
    assert entry["count"] == 1


def test_deduplicates_repeated_identical_warnings_with_a_count():
    log: list[dict] = []
    with collect_context_warnings(log, phase="inner_tuning"):
        for _ in range(5):
            warnings.warn("mismo mensaje", UserWarning)

    assert len(log) == 1, "no debe volcar una entrada por cada repetición"
    assert log[0]["count"] == 5


def test_records_nothing_when_no_warning_is_emitted():
    log: list[dict] = []
    with collect_context_warnings(log, phase="final_fit"):
        pass
    assert log == []


def test_distinguishes_warnings_from_different_contexts():
    log: list[dict] = []
    with collect_context_warnings(log, outer_fold_index=1):
        warnings.warn("x", UserWarning)
    with collect_context_warnings(log, outer_fold_index=2):
        warnings.warn("x", UserWarning)

    assert len(log) == 2
    assert {entry["outer_fold_index"] for entry in log} == {1, 2}
