from __future__ import annotations

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.bootstrap import (
    build_blocks,
    moving_block_bootstrap_indices,
    paired_bootstrap_delta,
    percentile_interval,
)
from experiment_runner.controlled_daily_v4.metrics import mcc_strict


def _two_segment_frame(n_per_segment=40):
    ids = ["outer_fold_1"] * n_per_segment + ["outer_fold_2"] * n_per_segment
    return pd.DataFrame({"segment_id": ids})


def test_blocks_never_cross_segment_boundaries():
    frame = _two_segment_frame(n_per_segment=40)
    blocks = build_blocks(frame, block_days=30)
    boundary = 40
    for block in blocks:
        segments = set(frame.iloc[block]["segment_id"])
        assert len(segments) == 1
        if segments == {"outer_fold_1"}:
            assert (block < boundary).all()
        else:
            assert (block >= boundary).all()


def test_bootstrap_replicas_preserve_total_length():
    frame = _two_segment_frame(n_per_segment=40)
    blocks = build_blocks(frame, block_days=30)
    replicas = moving_block_bootstrap_indices(blocks, total_length=80, n_replicas=10, seed=1)
    assert len(replicas) == 10
    for replica in replicas:
        assert len(replica) == 80


def test_bootstrap_is_deterministic_given_seed():
    frame = _two_segment_frame(n_per_segment=40)
    blocks = build_blocks(frame, block_days=30)
    replicas_a = moving_block_bootstrap_indices(blocks, total_length=80, n_replicas=5, seed=42)
    replicas_b = moving_block_bootstrap_indices(blocks, total_length=80, n_replicas=5, seed=42)
    for a, b in zip(replicas_a, replicas_b, strict=True):
        assert np.array_equal(a, b)


def test_paired_bootstrap_keeps_same_indices_for_both_candidates():
    rng = np.random.default_rng(0)
    n = 80
    frame = _two_segment_frame(n_per_segment=40)
    y_true = (rng.random(n) < 0.4).astype(int)
    y_pred_a = y_true.copy()  # candidato perfecto
    y_pred_b = 1 - y_true  # candidato siempre incorrecto

    deltas = paired_bootstrap_delta(
        y_true, y_pred_a, y_pred_b, frame, metric_fn=mcc_strict, n_replicas=30, seed=7
    )
    # A es perfecto (MCC=1) y B es siempre opuesto (MCC=-1) en cualquier
    # submuestra con ambas clases: el delta pareado debe ser consistentemente
    # positivo y cercano a 2 (salvo réplicas monoclase -> NaN, descartadas).
    finite = deltas[np.isfinite(deltas)]
    assert len(finite) > 0
    assert (finite > 0).all()


def test_percentile_interval_ignores_non_finite_values():
    values = np.array([1.0, 2.0, np.nan, 3.0, np.nan])
    lower, upper = percentile_interval(values, lower=0, upper=100)
    assert lower == 1.0
    assert upper == 3.0
