"""Moving block bootstrap pareado y segment-aware (protocolo, secciones 8 y 10).

Bloques de `BOOTSTRAP_BLOCK_DAYS` días, sin cruzar el límite de ningún
segmento outer (ni los gaps entre segmentos): cada bloque se arma dentro de
un único `segment_id`. El apareamiento entre candidatos se conserva siempre
usando exactamente los mismos índices resampleados para ambos.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.config import BOOTSTRAP_BLOCK_DAYS, BOOTSTRAP_SEED

MetricFn = Callable[[np.ndarray, np.ndarray], float]


def build_blocks(frame: pd.DataFrame, block_days: int = BOOTSTRAP_BLOCK_DAYS) -> list[np.ndarray]:
    """Bloques de posiciones (índices posicionales 0..len(frame)-1), de a lo
    sumo `block_days` filas consecutivas, sin cruzar `segment_id`. `frame`
    debe estar ordenado por `feature_timestamp` dentro de cada segmento."""
    blocks: list[np.ndarray] = []
    for _, segment in frame.groupby("segment_id", sort=False):
        positions = np.where(frame.index.isin(segment.index))[0]
        positions = np.sort(positions)
        for start in range(0, len(positions), block_days):
            blocks.append(positions[start : start + block_days])
    return blocks


def moving_block_bootstrap_indices(
    blocks: Sequence[np.ndarray],
    total_length: int,
    n_replicas: int,
    seed: int = BOOTSTRAP_SEED,
) -> list[np.ndarray]:
    """`n_replicas` muestras de índices, cada una de longitud >= `total_length`
    (recortada a `total_length`), armadas concatenando bloques elegidos con
    reemplazo del pool completo de bloques."""
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    replicas = []
    for _ in range(n_replicas):
        chosen: list[np.ndarray] = []
        length = 0
        while length < total_length:
            block = blocks[rng.integers(0, n_blocks)]
            chosen.append(block)
            length += len(block)
        combined = np.concatenate(chosen)[:total_length]
        replicas.append(combined)
    return replicas


def paired_bootstrap_delta(
    y_true: np.ndarray,
    y_pred_a: np.ndarray,
    y_pred_b: np.ndarray,
    frame_with_segment_id: pd.DataFrame,
    metric_fn: MetricFn,
    n_replicas: int,
    seed: int = BOOTSTRAP_SEED,
    block_days: int = BOOTSTRAP_BLOCK_DAYS,
) -> np.ndarray:
    """Distribución bootstrap de `metric_fn(a) - metric_fn(b)`, pareada
    (mismos índices resampleados para ambos candidatos en cada réplica)."""
    y_true = np.asarray(y_true)
    y_pred_a = np.asarray(y_pred_a)
    y_pred_b = np.asarray(y_pred_b)

    blocks = build_blocks(frame_with_segment_id, block_days=block_days)
    replicas = moving_block_bootstrap_indices(
        blocks, total_length=len(y_true), n_replicas=n_replicas, seed=seed
    )

    deltas = np.empty(n_replicas)
    for i, idx in enumerate(replicas):
        metric_a = metric_fn(y_true[idx], y_pred_a[idx])
        metric_b = metric_fn(y_true[idx], y_pred_b[idx])
        deltas[i] = metric_a - metric_b
    return deltas


def percentile_interval(
    values: np.ndarray, lower: float = 2.5, upper: float = 97.5
) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan"), float("nan")
    return float(np.percentile(finite, lower)), float(np.percentile(finite, upper))
