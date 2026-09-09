"""Selección de familia en la Etapa A (protocolo, sección 8).

Diferencia explícitamente ganador estable, empate práctico (`SIN_GANADOR_ESTABLE`
con desempate por simplicidad predeclarada) y ausencia de selección válida.
El desempate por simplicidad nunca se documenta como superioridad predictiva.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.bootstrap import (
    paired_bootstrap_delta,
    percentile_interval,
)
from experiment_runner.controlled_daily_v4.config import (
    BOOTSTRAP_REPLICAS_DEFAULT,
    BOOTSTRAP_SEED,
    FAMILY_SIMPLICITY_ORDER,
    PRACTICAL_MARGIN_DELTA_MCC,
)
from experiment_runner.controlled_daily_v4.metrics import mcc_strict

OUTCOME_STABLE_WINNER = "STABLE_WINNER"
OUTCOME_NO_STABLE_WINNER = "SIN_GANADOR_ESTABLE"
OUTCOME_NO_VALID_SELECTION = "NO_VALID_SELECTION"


@dataclass(frozen=True)
class CandidateOOF:
    family: str
    y_true: np.ndarray
    y_pred: np.ndarray
    y_score: np.ndarray
    frame_with_segment_id: pd.DataFrame
    per_fold_mcc: list[float] = field(default_factory=list)


@dataclass
class SelectionResult:
    outcome: str
    global_mcc_by_family: dict[str, float]
    pairwise_intervals: dict[tuple[str, str], tuple[float, float]]
    equivalence_set: list[str]
    stable_winner: str | None
    selected_family: str | None
    selection_reason: str


def _pairwise_key(a: str, b: str) -> tuple[str, str]:
    return (a, b)


def select_family(
    candidates: dict[str, CandidateOOF],
    delta: float = PRACTICAL_MARGIN_DELTA_MCC,
    n_replicas: int = BOOTSTRAP_REPLICAS_DEFAULT,
    seed: int = BOOTSTRAP_SEED,
) -> SelectionResult:
    families = list(candidates.keys())
    global_mcc = {f: mcc_strict(c.y_true, c.y_pred) for f, c in candidates.items()}

    if any(np.isnan(v) for v in global_mcc.values()):
        return SelectionResult(
            outcome=OUTCOME_NO_VALID_SELECTION,
            global_mcc_by_family=global_mcc,
            pairwise_intervals={},
            equivalence_set=[],
            stable_winner=None,
            selected_family=None,
            selection_reason="oof_concatenado_monoclase_o_mcc_indefinido",
        )

    pairwise_intervals: dict[tuple[str, str], tuple[float, float]] = {}
    for a in families:
        for b in families:
            if a == b:
                continue
            deltas = paired_bootstrap_delta(
                y_true=candidates[a].y_true,
                y_pred_a=candidates[a].y_pred,
                y_pred_b=candidates[b].y_pred,
                frame_with_segment_id=candidates[a].frame_with_segment_id,
                metric_fn=mcc_strict,
                n_replicas=n_replicas,
                seed=seed,
            )
            pairwise_intervals[_pairwise_key(a, b)] = percentile_interval(deltas)

    best = max(families, key=lambda f: global_mcc[f])

    def is_stable_winner(candidate: str) -> bool:
        for rival in families:
            if rival == candidate:
                continue
            diff = global_mcc[candidate] - global_mcc[rival]
            lower, _ = pairwise_intervals[_pairwise_key(candidate, rival)]
            if diff < delta or lower <= 0:
                return False
        return True

    if is_stable_winner(best):
        return SelectionResult(
            outcome=OUTCOME_STABLE_WINNER,
            global_mcc_by_family=global_mcc,
            pairwise_intervals=pairwise_intervals,
            equivalence_set=[best],
            stable_winner=best,
            selected_family=best,
            selection_reason="stable_winner",
        )

    equivalence_set = {best}
    for candidate in families:
        if candidate == best:
            continue
        diff = global_mcc[best] - global_mcc[candidate]
        lower, _ = pairwise_intervals[_pairwise_key(best, candidate)]
        if diff < delta or (lower <= 0):
            equivalence_set.add(candidate)

    simplicity_rank = {f: i for i, f in enumerate(FAMILY_SIMPLICITY_ORDER)}
    selected = min(
        equivalence_set, key=lambda f: simplicity_rank.get(f, len(FAMILY_SIMPLICITY_ORDER))
    )

    return SelectionResult(
        outcome=OUTCOME_NO_STABLE_WINNER,
        global_mcc_by_family=global_mcc,
        pairwise_intervals=pairwise_intervals,
        equivalence_set=sorted(equivalence_set, key=lambda f: simplicity_rank.get(f, 99)),
        stable_winner=None,
        selected_family=selected,
        selection_reason="tie_break_simplicity_predeclarada_no_superioridad",
    )
