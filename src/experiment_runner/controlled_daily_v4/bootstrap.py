"""Moving block bootstrap pareado y segment-aware (protocolo, secciones 8 y 10).

Dentro de cada `segment_id` outer se generan todos los bloques solapados
posibles de largo exacto `block_length` (`start ∈ [0, n_s - L]`). El
remuestreo con reemplazo ocurre de forma independiente en cada segmento y
repone exactamente su tamaño original `n_s`, de modo que ninguna réplica
sobrerrepresenta un outer fold. Los bloques nunca cruzan un segmento y, por
lo tanto, nunca cruzan un gap: los gaps no existen como filas del conjunto
OOF. El apareamiento entre candidatos se conserva aplicando exactamente los
mismos índices resampleados a `y_true` y a los dos vectores de predicción.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.config import BOOTSTRAP_BLOCK_DAYS, BOOTSTRAP_SEED

MetricFn = Callable[[np.ndarray, np.ndarray], float]

DISCARD_UNDEFINED_METRIC = "undefined_metric"

__all__ = [
    "BOOTSTRAP_BLOCK_DAYS",
    "BootstrapDiagnostics",
    "NoValidBootstrapReplicasError",
    "PairedBootstrapResult",
    "SegmentPlan",
    "SegmentTooShortForBlockError",
    "build_segment_plans",
    "moving_block_bootstrap_indices",
    "paired_bootstrap_delta",
    "percentile_interval",
]


class SegmentTooShortForBlockError(ValueError):
    """Un segmento outer tiene menos observaciones que el largo de bloque
    exigido, por lo que no admite ningún bloque móvil completo."""


class NoValidBootstrapReplicasError(RuntimeError):
    """Ninguna réplica produjo una métrica definida; no hay intervalo que
    reportar y el resultado no puede interpretarse como comparación válida."""


@dataclass(frozen=True)
class SegmentPlan:
    """Bloques móviles disponibles dentro de un único segmento outer."""

    segment_id: str
    positions: np.ndarray
    blocks: list[np.ndarray]

    @property
    def size(self) -> int:
        return len(self.positions)


@dataclass(frozen=True)
class BootstrapDiagnostics:
    """Provenance completa del procedimiento, para serializar como evidencia."""

    replicas_requested: int
    replicas_valid: int
    replicas_discarded: int
    n_segments: int
    block_length: int
    seed: int
    normative: bool
    segment_sizes: dict[str, int] = field(default_factory=dict)
    discard_reasons: dict[str, int] = field(default_factory=dict)
    interval_lower: float | None = None
    interval_upper: float | None = None


@dataclass(frozen=True)
class PairedBootstrapResult:
    deltas: np.ndarray
    interval: tuple[float, float]
    diagnostics: BootstrapDiagnostics


def build_segment_plans(
    frame: pd.DataFrame,
    block_length: int = BOOTSTRAP_BLOCK_DAYS,
    normative: bool = True,
) -> list[SegmentPlan]:
    """Bloques móviles solapados por segmento, en orden temporal.

    `frame` debe estar ordenado por `feature_timestamp` y contener la columna
    `segment_id`. En modo normativo el largo de bloque debe ser exactamente el
    del protocolo (30 días) y todo segmento debe admitirlo; un largo distinto
    solo se acepta con `normative=False`, reservado para tests.
    """
    if normative and block_length != BOOTSTRAP_BLOCK_DAYS:
        raise ValueError(
            f"El protocolo fija bloques de {BOOTSTRAP_BLOCK_DAYS} días; se recibió "
            f"{block_length}. Usar normative=False solo en tests no normativos."
        )

    plans: list[SegmentPlan] = []
    segment_ids = frame["segment_id"].to_numpy()
    for segment_id in pd.unique(segment_ids):
        positions = np.where(segment_ids == segment_id)[0]
        if len(positions) < block_length:
            raise SegmentTooShortForBlockError(
                f"El segmento '{segment_id}' tiene {len(positions)} observaciones, "
                f"menos que el largo de bloque {block_length}: no admite ningún "
                "bloque móvil completo."
            )
        blocks = [
            positions[start : start + block_length]
            for start in range(0, len(positions) - block_length + 1)
        ]
        plans.append(SegmentPlan(segment_id=str(segment_id), positions=positions, blocks=blocks))
    return plans


def moving_block_bootstrap_indices(
    plans: Sequence[SegmentPlan],
    n_replicas: int,
    seed: int = BOOTSTRAP_SEED,
) -> list[np.ndarray]:
    """`n_replicas` muestras de índices posicionales.

    Cada réplica se arma segmento por segmento: se eligen bloques con
    reemplazo dentro del propio segmento hasta reunir al menos `n_s`
    posiciones y se trunca a exactamente `n_s`. Las muestras por segmento se
    concatenan en el orden temporal de los segmentos, de modo que cada
    réplica conserva el tamaño original de cada segmento.
    """
    rng = np.random.default_rng(seed)
    replicas: list[np.ndarray] = []
    for _ in range(n_replicas):
        per_segment: list[np.ndarray] = []
        for plan in plans:
            chosen: list[np.ndarray] = []
            length = 0
            while length < plan.size:
                block = plan.blocks[rng.integers(0, len(plan.blocks))]
                chosen.append(block)
                length += len(block)
            per_segment.append(np.concatenate(chosen)[: plan.size])
        replicas.append(np.concatenate(per_segment))
    return replicas


def percentile_interval(
    values: np.ndarray, lower: float = 2.5, upper: float = 97.5
) -> tuple[float, float]:
    """Intervalo percentil sobre las réplicas válidas provistas."""
    finite = np.asarray(values)[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan"), float("nan")
    return (
        float(np.percentile(finite, lower, method="linear")),
        float(np.percentile(finite, upper, method="linear")),
    )


def paired_bootstrap_delta(
    y_true: np.ndarray,
    y_pred_a: np.ndarray,
    y_pred_b: np.ndarray,
    frame_with_segment_id: pd.DataFrame,
    metric_fn: MetricFn,
    n_replicas: int,
    seed: int = BOOTSTRAP_SEED,
    block_length: int = BOOTSTRAP_BLOCK_DAYS,
    normative: bool = True,
) -> PairedBootstrapResult:
    """Distribución bootstrap pareada de `metric_fn(a) - metric_fn(b)`.

    Las réplicas cuya métrica queda indefinida (por ejemplo, remuestreo
    monoclase) se descartan, pero se contabilizan explícitamente en las
    diagnósticas: nunca se descartan en silencio. Si ninguna réplica resulta
    válida se levanta `NoValidBootstrapReplicasError`.
    """
    y_true = np.asarray(y_true)
    y_pred_a = np.asarray(y_pred_a)
    y_pred_b = np.asarray(y_pred_b)

    plans = build_segment_plans(
        frame_with_segment_id, block_length=block_length, normative=normative
    )
    replicas = moving_block_bootstrap_indices(plans, n_replicas=n_replicas, seed=seed)

    valid: list[float] = []
    discard_reasons: dict[str, int] = {}
    for idx in replicas:
        delta = metric_fn(y_true[idx], y_pred_a[idx]) - metric_fn(y_true[idx], y_pred_b[idx])
        if np.isfinite(delta):
            valid.append(float(delta))
        else:
            discard_reasons[DISCARD_UNDEFINED_METRIC] = (
                discard_reasons.get(DISCARD_UNDEFINED_METRIC, 0) + 1
            )

    segment_sizes = {plan.segment_id: plan.size for plan in plans}
    if not valid:
        raise NoValidBootstrapReplicasError(
            f"Ninguna de las {n_replicas} réplicas produjo una métrica definida "
            f"(motivos: {discard_reasons or {DISCARD_UNDEFINED_METRIC: n_replicas}}). "
            "No hay intervalo pareado que reportar."
        )

    deltas = np.asarray(valid, dtype=float)
    interval = percentile_interval(deltas)
    diagnostics = BootstrapDiagnostics(
        replicas_requested=n_replicas,
        replicas_valid=len(valid),
        replicas_discarded=n_replicas - len(valid),
        n_segments=len(plans),
        block_length=block_length,
        seed=seed,
        normative=normative,
        segment_sizes=segment_sizes,
        discard_reasons=discard_reasons,
        interval_lower=interval[0],
        interval_upper=interval[1],
    )
    return PairedBootstrapResult(deltas=deltas, interval=interval, diagnostics=diagnostics)
