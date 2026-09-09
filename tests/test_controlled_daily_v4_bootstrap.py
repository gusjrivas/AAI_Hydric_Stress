"""Moving block bootstrap pareado y segment-aware (protocolo, secciones 8 y 10).

Fija el contrato exigido: bloques solapados de largo exacto dentro de cada
segmento outer, remuestreo independiente por segmento que preserva su tamaño
original, apareamiento por índice entre los dos candidatos del par, y
contabilidad explícita de réplicas descartadas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.bootstrap import (
    BOOTSTRAP_BLOCK_DAYS,
    NoValidBootstrapReplicasError,
    SegmentTooShortForBlockError,
    build_segment_plans,
    moving_block_bootstrap_indices,
    paired_bootstrap_delta,
    percentile_interval,
)
from experiment_runner.controlled_daily_v4.config import BOOTSTRAP_SEED
from experiment_runner.controlled_daily_v4.metrics import mcc_strict


def _frame(sizes: dict[str, int]) -> pd.DataFrame:
    ids: list[str] = []
    for segment_id, size in sizes.items():
        ids += [segment_id] * size
    return pd.DataFrame({"segment_id": ids})


THREE_SEGMENTS = {"outer_fold_1": 100, "outer_fold_2": 100, "outer_fold_3": 100}


def test_blocks_are_overlapping_and_far_more_numerous_than_a_fixed_partition():
    frame = _frame(THREE_SEGMENTS)
    plans = build_segment_plans(frame, block_length=30)
    total_blocks = sum(len(p.blocks) for p in plans)
    # Partición fija anterior: ceil(100/30)=4 bloques por segmento = 12.
    # Esquema móvil: (100-30+1)=71 por segmento = 213.
    assert total_blocks == 213
    assert total_blocks > 12
    starts = [int(b[0]) for b in plans[0].blocks]
    assert starts == sorted(starts)
    assert len(set(starts)) == 71


def test_every_block_has_exactly_the_block_length():
    plans = build_segment_plans(_frame(THREE_SEGMENTS), block_length=30)
    for plan in plans:
        for block in plan.blocks:
            assert len(block) == 30


def test_consecutive_blocks_overlap():
    plans = build_segment_plans(_frame(THREE_SEGMENTS), block_length=30)
    first, second = plans[0].blocks[0], plans[0].blocks[1]
    assert len(set(first.tolist()) & set(second.tolist())) == 29


def test_no_block_crosses_a_segment_boundary():
    frame = _frame(THREE_SEGMENTS)
    plans = build_segment_plans(frame, block_length=30)
    segments = frame["segment_id"].to_numpy()
    for plan in plans:
        for block in plan.blocks:
            assert set(segments[block]) == {plan.segment_id}


def test_blocks_only_use_positions_of_their_own_segment():
    """Los gaps entre outer folds no existen como filas: al no cruzar
    segmentos, ningún bloque puede atravesar un gap."""
    frame = _frame(THREE_SEGMENTS)
    plans = build_segment_plans(frame, block_length=30)
    for plan in plans:
        expected = np.where(frame["segment_id"].to_numpy() == plan.segment_id)[0]
        np.testing.assert_array_equal(plan.positions, expected)
        for block in plan.blocks:
            assert set(block.tolist()) <= set(expected.tolist())


def test_each_replica_preserves_the_original_size_of_every_segment():
    frame = _frame({"outer_fold_1": 100, "outer_fold_2": 80, "outer_fold_3": 120})
    plans = build_segment_plans(frame, block_length=30)
    replicas = moving_block_bootstrap_indices(plans, n_replicas=50, seed=BOOTSTRAP_SEED)
    segments = frame["segment_id"].to_numpy()
    for replica in replicas:
        assert len(replica) == len(frame)
        counts = pd.Series(segments[replica]).value_counts().to_dict()
        assert counts == {"outer_fold_1": 100, "outer_fold_2": 80, "outer_fold_3": 120}


def test_replicas_are_deterministic_given_the_seed():
    plans = build_segment_plans(_frame(THREE_SEGMENTS), block_length=30)
    a = moving_block_bootstrap_indices(plans, n_replicas=10, seed=BOOTSTRAP_SEED)
    b = moving_block_bootstrap_indices(plans, n_replicas=10, seed=BOOTSTRAP_SEED)
    for x, y in zip(a, b, strict=True):
        np.testing.assert_array_equal(x, y)


def test_different_seeds_produce_different_replicas():
    plans = build_segment_plans(_frame(THREE_SEGMENTS), block_length=30)
    a = moving_block_bootstrap_indices(plans, n_replicas=10, seed=BOOTSTRAP_SEED)
    b = moving_block_bootstrap_indices(plans, n_replicas=10, seed=BOOTSTRAP_SEED + 1)
    assert any(not np.array_equal(x, y) for x, y in zip(a, b, strict=True))


def test_a_segment_shorter_than_the_block_fails_explicitly_in_normative_mode():
    frame = _frame({"outer_fold_1": 100, "outer_fold_2": 12})
    with pytest.raises(SegmentTooShortForBlockError) as exc:
        build_segment_plans(frame, block_length=BOOTSTRAP_BLOCK_DAYS)
    assert "outer_fold_2" in str(exc.value)


def test_a_shorter_block_is_only_allowed_in_explicit_non_normative_mode():
    frame = _frame({"outer_fold_1": 40, "outer_fold_2": 12})
    # En modo normativo el largo de bloque es parte del protocolo: cualquier
    # valor distinto de 30 se rechaza antes de mirar los segmentos.
    with pytest.raises(ValueError, match="fija bloques de 30"):
        build_segment_plans(frame, block_length=10)
    plans = build_segment_plans(frame, block_length=10, normative=False)
    assert [p.segment_id for p in plans] == ["outer_fold_1", "outer_fold_2"]
    assert all(len(b) == 10 for p in plans for b in p.blocks)


def test_paired_delta_applies_exactly_the_same_indices_to_both_candidates():
    frame = _frame(THREE_SEGMENTS)
    rng = np.random.default_rng(0)
    n = len(frame)
    y_true = (rng.random(n) < 0.4).astype(int)
    y_pred_a = np.where(rng.random(n) < 0.2, 1 - y_true, y_true)
    y_pred_b = np.where(rng.random(n) < 0.4, 1 - y_true, y_true)

    result = paired_bootstrap_delta(
        y_true, y_pred_a, y_pred_b, frame, metric_fn=mcc_strict, n_replicas=25, seed=BOOTSTRAP_SEED
    )
    plans = build_segment_plans(frame, block_length=BOOTSTRAP_BLOCK_DAYS)
    replicas = moving_block_bootstrap_indices(plans, n_replicas=25, seed=BOOTSTRAP_SEED)
    expected = [
        mcc_strict(y_true[i], y_pred_a[i]) - mcc_strict(y_true[i], y_pred_b[i]) for i in replicas
    ]
    expected = [d for d in expected if np.isfinite(d)]
    np.testing.assert_allclose(result.deltas, expected)


def test_diagnostics_record_discarded_replicas_with_their_reason():
    # Un único positivo: las réplicas que no lo incluyen quedan monoclase.
    frame = _frame({"outer_fold_1": 60})
    n = len(frame)
    y_true = np.zeros(n, dtype=int)
    y_true[0] = 1
    y_pred_a = np.zeros(n, dtype=int)
    y_pred_b = np.ones(n, dtype=int)

    result = paired_bootstrap_delta(
        y_true, y_pred_a, y_pred_b, frame, metric_fn=mcc_strict, n_replicas=40, seed=BOOTSTRAP_SEED
    )
    d = result.diagnostics
    assert d.replicas_requested == 40
    assert d.replicas_discarded > 0
    assert d.replicas_valid + d.replicas_discarded == 40
    assert d.replicas_valid == len(result.deltas)
    assert d.discard_reasons["undefined_metric"] == d.replicas_discarded


def test_diagnostics_record_the_full_provenance_of_the_procedure():
    frame = _frame({"outer_fold_1": 100, "outer_fold_2": 80})
    rng = np.random.default_rng(1)
    n = len(frame)
    y_true = (rng.random(n) < 0.4).astype(int)
    result = paired_bootstrap_delta(
        y_true,
        y_true,
        1 - y_true,
        frame,
        metric_fn=mcc_strict,
        n_replicas=12,
        seed=BOOTSTRAP_SEED,
    )
    d = result.diagnostics
    assert d.n_segments == 2
    assert d.segment_sizes == {"outer_fold_1": 100, "outer_fold_2": 80}
    assert d.block_length == BOOTSTRAP_BLOCK_DAYS
    assert d.seed == BOOTSTRAP_SEED
    assert d.normative is True
    assert d.interval_lower == pytest.approx(result.interval[0])
    assert d.interval_upper == pytest.approx(result.interval[1])


def test_no_valid_replica_raises_a_clear_error():
    frame = _frame({"outer_fold_1": 60})
    y_true = np.zeros(len(frame), dtype=int)  # monoclase completo
    with pytest.raises(NoValidBootstrapReplicasError) as exc:
        paired_bootstrap_delta(
            y_true,
            y_true,
            y_true,
            frame,
            metric_fn=mcc_strict,
            n_replicas=10,
            seed=BOOTSTRAP_SEED,
        )
    assert "undefined_metric" in str(exc.value)


def test_percentile_interval_uses_the_valid_replicas():
    values = np.array([1.0, 2.0, 3.0])
    lower, upper = percentile_interval(values, lower=0, upper=100)
    assert lower == 1.0
    assert upper == 3.0
