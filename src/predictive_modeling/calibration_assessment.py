"""Motor de evaluacion operacional de calibracion (spec `predictive-modeling`,
manifiesto congelado
`config/producer-calibration-plan.frozen.v3.json`, y
[design.md](../../openspec/changes/add-daily-multihorizon-predictors/design.md),
secciones "Evaluacion directa y dependencia temporal" y "Regla de
presentacion, por horizonte").

Funciones de dominio puras: no entrenan, ajustan ni cargan ningun modelo, no
leen `data/melchor_romero_2024_consolidado.parquet` ni ningun split real. El
llamador provee pares (fecha, probabilidad, resultado) ya calculados
(sinteticos en pruebas; reales solo en una evaluacion futura fuera de este
modulo).

Notas de implementacion no fijadas explicitamente por el manifiesto (se
documentan aqui en vez de decidirse en silencio dentro de las specs):

- El remuestreo por bloques de una definicion de periodo (periodo completo o
  cada ventana de estabilidad) se sortea UNA vez por replica y se comparte
  entre todos los alcances horizonte/semilla que usan ese mismo calendario
  ("sincronizado entre horizontes y semillas"). Definiciones de periodo
  distintas (periodo completo vs. cada ventana) tienen particiones de
  bloques independientes y se sortean del mismo generador aleatorio con
  semilla fija, en un orden de declaracion estable, en TODAS las replicas
  -- incluso despues de que un periodo anterior en esa misma replica ya la
  haya vuelto no evaluable -- para que la secuencia de sorteos nunca dependa
  del resultado de replicas previas.
- La regla de invalidez de replica (`uncertainty.invalid_replicate_rule` del
  manifiesto) se aplica a la familia conjunta que el llamador construye en
  una misma llamada a `run_joint_multiplicity_bootstrap`: si falta un
  componente en cualquier alcance/bin de esa familia, la replica entera
  queda no evaluable para todos los alcances de esa llamada, no solo para
  el periodo o alcance donde ocurrio.
- Los controles de Brier/log-loss (`compare_against_baselines`) reciben ya
  calculadas las probabilidades calibrada, raw y de persistencia, y el
  escalar de climatologia: este modulo no ajusta ni deriva ningun baseline
  a partir de datos crudos (eso sigue siendo responsabilidad exclusiva del
  llamador, incluida la causalidad de `raw`/`persistence` y que
  `climatology_probability` provenga solo de `partitions.train`). Lo que
  el modulo SI garantiza es que las tres series de probabilidad y los
  resultados compartan exactamente el mismo conjunto de fechas antes de
  comparar nada (`build_baseline_comparison_inputs`), y que la decision
  final nunca sea `passed` con un control ausente, un alcance requerido
  incompleto o un valor no finito.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

# ---------------------------------------------------------------------------
# Bins de probabilidad: inclusion en ECE vs. familia de bins respaldados
# ---------------------------------------------------------------------------


def assign_bin_index(
    probability: float, *, bin_count: int = 10, include_one_in_last: bool = True
) -> int:
    """Bin equal-width de `probability` en [0, `bin_count`).

    Con `include_one_in_last=True` (`probability_bins.include_one_in_last`
    del manifiesto), `probability == 1.0` cae en el ultimo bin en vez de
    quedar fuera de rango.
    """
    if isinstance(probability, bool) or not isinstance(probability, int | float):
        raise ValueError("probability debe ser numerico.")
    if not (0.0 <= probability <= 1.0):
        raise ValueError("probability debe estar en [0, 1].")
    if bin_count <= 0:
        raise ValueError("bin_count debe ser positivo.")
    if probability >= 1.0:
        if include_one_in_last:
            return bin_count - 1
        raise ValueError("probability == 1.0 requiere include_one_in_last=True.")
    # Un epsilon diminuto evita que el error de redondeo binario de
    # `probability * bin_count` (p.ej. 0.3 * 10 == 2.9999999999999996 en
    # coma flotante) empuje un valor de borde legitimo al bin anterior.
    index = int(probability * bin_count + 1e-9)
    return min(index, bin_count - 1)


@dataclass(frozen=True)
class BinStat:
    index: int
    count: int
    frequency: float | None
    mean_probability: float | None


def compute_bin_stats(
    pairs: Sequence[tuple[float, int]], *, bin_count: int = 10, include_one_in_last: bool = True
) -> tuple[BinStat, ...]:
    """`frequency`/`mean_probability` quedan en `None` para bins vacios
    (`count == 0`): design.md define el ECE solo "sobre los intervalos no
    vacios", por lo que un bin vacio no tiene una frecuencia observable.
    """
    sum_outcome = [0.0] * bin_count
    sum_probability = [0.0] * bin_count
    counts = [0] * bin_count
    for probability, outcome in pairs:
        if outcome not in (0, 1):
            raise ValueError("outcome debe ser 0 o 1.")
        idx = assign_bin_index(
            probability, bin_count=bin_count, include_one_in_last=include_one_in_last
        )
        counts[idx] += 1
        sum_outcome[idx] += float(outcome)
        sum_probability[idx] += float(probability)
    stats = []
    for i in range(bin_count):
        if counts[i] == 0:
            stats.append(BinStat(i, 0, None, None))
        else:
            stats.append(
                BinStat(i, counts[i], sum_outcome[i] / counts[i], sum_probability[i] / counts[i])
            )
    return tuple(stats)


def ece_bin_inclusion_indices(bin_stats: Sequence[BinStat]) -> frozenset[int]:
    """`uncertainty.ece_bin_inclusion`: todos los bins no vacios, sin filtrar
    por soporte. Predeclarar esta familia UNA vez a partir de los datos
    completos (no resampleados) de un alcance es responsabilidad del
    llamador: no volver a invocar esta funcion sobre datos remuestreados
    para redefinir la familia por replica.
    """
    return frozenset(stat.index for stat in bin_stats if stat.count > 0)


def backed_bin_indices(bin_stats: Sequence[BinStat], *, minimum_bin_count: int) -> frozenset[int]:
    """`uncertainty.backed_bin_family`: subconjunto respaldado
    (`count >= minimum_bin_count`) del conjunto observado completo. Misma
    advertencia que `ece_bin_inclusion_indices`: fijar una unica vez sobre
    datos completos, no por replica.
    """
    return frozenset(stat.index for stat in bin_stats if stat.count >= minimum_bin_count)


def compute_ece(
    bin_stats: Sequence[BinStat], included_indices: frozenset[int], *, total_n: int
) -> float:
    """ECE = suma, sobre `included_indices`, de n_b/N * |frecuencia_b -
    probabilidad_media_b|. `total_n` (N) es el tamano total del alcance
    evaluado, no la suma de los bins incluidos: un bin excluido de
    `included_indices` (nunca deberia ocurrir para un bin no vacio, ya que
    `included_indices` se predeclara como todos los bins no vacios) no
    reduce N.
    """
    if total_n <= 0:
        raise ValueError("total_n debe ser positivo para calcular ECE.")
    total = 0.0
    for stat in bin_stats:
        if stat.index not in included_indices or stat.count == 0:
            continue  # bin no incluido, o conteo 0 en esta muestra: aporta 0 (n_b/N=0)
        total += (stat.count / total_n) * abs(stat.frequency - stat.mean_probability)
    return total


def compute_backed_bin_errors(
    bin_stats: Sequence[BinStat], backed_indices: frozenset[int], *, minimum_bin_count: int
) -> dict[int, float | None]:
    """Error absoluto por bin respaldado. `None` marca un bin de
    `backed_indices` que en ESTA muestra (por ejemplo, una replica
    remuestreada) perdio el soporte minimo: el llamador decide como tratar
    ese `None` (ver `uncertainty.invalid_replicate_rule`: no se descarta solo
    ese componente, se propaga como "no evaluable" a toda la replica).
    """
    by_index = {stat.index: stat for stat in bin_stats}
    result: dict[int, float | None] = {}
    for idx in backed_indices:
        stat = by_index.get(idx, BinStat(idx, 0, None, None))
        if stat.count >= minimum_bin_count:
            result[idx] = abs(stat.frequency - stat.mean_probability)
        else:
            result[idx] = None
    return result


# ---------------------------------------------------------------------------
# Bloques temporales y remuestreo (uncertainty.method / block_length_days)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemporalBlocks:
    period_start: date
    period_end: date
    block_length_days: int
    num_blocks: int

    def block_index_for(self, day: date) -> int:
        if day < self.period_start or day > self.period_end:
            raise ValueError(
                f"{day} esta fuera del periodo {self.period_start}..{self.period_end}."
            )
        offset = (day - self.period_start).days
        return min(offset // self.block_length_days, self.num_blocks - 1)


def build_temporal_blocks(
    period_start: date, period_end: date, *, block_length_days: int
) -> TemporalBlocks:
    if period_end < period_start:
        raise ValueError("period_end no puede preceder a period_start.")
    if block_length_days <= 0:
        raise ValueError("block_length_days debe ser positivo.")
    total_days = (period_end - period_start).days + 1
    num_blocks = -(-total_days // block_length_days)  # techo (ceil) sin importar float
    return TemporalBlocks(period_start, period_end, block_length_days, num_blocks)


def draw_block_replicate(blocks: TemporalBlocks, rng: random.Random) -> tuple[int, ...]:
    """Bootstrap de bloques moviles: `num_blocks` indices de bloque
    remuestreados con reemplazo, uno por posicion original."""
    return tuple(rng.randrange(blocks.num_blocks) for _ in range(blocks.num_blocks))


def distinct_blocks_count(drawn_block_indices: Sequence[int]) -> int:
    return len(set(drawn_block_indices))


def select_pairs_for_blocks(
    pairs: Sequence[tuple[date, float, int]],
    blocks: TemporalBlocks,
    drawn_block_indices: Sequence[int],
) -> tuple[tuple[float, int], ...]:
    """Reconstruye los pares (probabilidad, resultado) de una replica
    concatenando, en el orden sorteado, las observaciones de cada bloque
    remuestreado."""
    by_block: dict[int, list[tuple[float, int]]] = {}
    for day, probability, outcome in pairs:
        idx = blocks.block_index_for(day)
        by_block.setdefault(idx, []).append((probability, outcome))
    result: list[tuple[float, int]] = []
    for block_idx in drawn_block_indices:
        result.extend(by_block.get(block_idx, ()))
    return tuple(result)


# ---------------------------------------------------------------------------
# Alcances (horizonte x semilla x periodo) y estadisticas fijas por alcance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopeObservations:
    """Pares (target_date, probabilidad, resultado) ya causalmente purgados
    y restringidos al rango de fechas de `period_id`, para un unico
    horizonte/semilla."""

    horizon: int
    seed: int
    period_id: str
    pairs: tuple[tuple[date, float, int], ...]


@dataclass(frozen=True)
class ScopeFullStats:
    """Estadisticas fijas de un alcance, calculadas UNA sola vez sobre el
    conjunto observado completo (sin remuestrear): fija `ece_indices` y
    `backed_indices` para todas las replicas de ese alcance."""

    scope: ScopeObservations
    bin_stats: tuple[BinStat, ...]
    ece_indices: frozenset[int]
    backed_indices: frozenset[int]
    total_n: int


def build_scope_full_stats(
    scope: ScopeObservations, *, bin_count: int, include_one_in_last: bool, minimum_bin_count: int
) -> ScopeFullStats:
    prob_outcome_pairs = [(probability, outcome) for _, probability, outcome in scope.pairs]
    bin_stats = compute_bin_stats(
        prob_outcome_pairs, bin_count=bin_count, include_one_in_last=include_one_in_last
    )
    return ScopeFullStats(
        scope=scope,
        bin_stats=bin_stats,
        ece_indices=ece_bin_inclusion_indices(bin_stats),
        backed_indices=backed_bin_indices(bin_stats, minimum_bin_count=minimum_bin_count),
        total_n=len(prob_outcome_pairs),
    )


@dataclass(frozen=True)
class SupportCheckResult:
    """Precondicion 1 de la "Regla de presentacion, por horizonte" de
    design.md, sobre el conjunto observado completo (no bootstrapeado)."""

    ok: bool
    reasons: tuple[str, ...]


def check_full_sample_support(
    scope_stats: ScopeFullStats,
    blocks: TemporalBlocks,
    *,
    minimum_class_count: int,
    minimum_temporal_blocks: int,
    coverage_minimum: float,
) -> SupportCheckResult:
    reasons: list[str] = []
    pairs = scope_stats.scope.pairs
    n_class0 = sum(1 for _, _, outcome in pairs if outcome == 0)
    n_class1 = sum(1 for _, _, outcome in pairs if outcome == 1)
    if n_class0 < minimum_class_count or n_class1 < minimum_class_count:
        reasons.append("insufficient_class_support")
    represented_blocks = {blocks.block_index_for(day) for day, _, _ in pairs}
    if len(represented_blocks) < minimum_temporal_blocks:
        reasons.append("insufficient_temporal_blocks")
    backed_n = sum(
        stat.count for stat in scope_stats.bin_stats if stat.index in scope_stats.backed_indices
    )
    coverage = (backed_n / scope_stats.total_n) if scope_stats.total_n else 0.0
    if coverage < coverage_minimum:
        reasons.append("insufficient_coverage")
    return SupportCheckResult(ok=not reasons, reasons=tuple(reasons))


# ---------------------------------------------------------------------------
# Familia conjunta por replica: componentes de ECE + error por bin
# ---------------------------------------------------------------------------

ScopeKey = tuple[int, int, str]
BinComponentKey = tuple[int, int, str, int]


@dataclass(frozen=True)
class ReplicateComponents:
    """`None` marca un componente no estimable en esta replica particular."""

    ece_by_scope: dict[ScopeKey, float | None]
    bin_error_by_component: dict[BinComponentKey, float | None]

    @property
    def is_evaluable(self) -> bool:
        """Toda la familia conjunta debe ser estimable: ningun `None`."""
        return all(value is not None for value in self.ece_by_scope.values()) and all(
            value is not None for value in self.bin_error_by_component.values()
        )

    def joint_maximum(self) -> float | None:
        """`None` si algun componente no es estimable: nunca se calcula un
        maximo parcial omitiendolo (`uncertainty.invalid_replicate_rule`)."""
        if not self.is_evaluable:
            return None
        values = [*self.ece_by_scope.values(), *self.bin_error_by_component.values()]
        if not values:
            raise ValueError("La familia conjunta esta vacia: no hay componentes que maximizar.")
        return max(values)


def compute_replicate_components(
    scope_stats_by_period: Mapping[str, Sequence[ScopeFullStats]],
    blocks_by_period: Mapping[str, TemporalBlocks],
    drawn_blocks_by_period: Mapping[str, tuple[int, ...]],
    *,
    bin_count: int,
    include_one_in_last: bool,
    minimum_class_count: int,
    minimum_temporal_blocks: int,
    minimum_bin_count: int,
) -> ReplicateComponents:
    ece_by_scope: dict[ScopeKey, float | None] = {}
    bin_error_by_component: dict[BinComponentKey, float | None] = {}
    for period_id, scope_list in scope_stats_by_period.items():
        blocks = blocks_by_period[period_id]
        drawn = drawn_blocks_by_period[period_id]
        distinct = distinct_blocks_count(drawn)
        for scope_stats in scope_list:
            key: ScopeKey = (scope_stats.scope.horizon, scope_stats.scope.seed, period_id)
            resampled_pairs = select_pairs_for_blocks(scope_stats.scope.pairs, blocks, drawn)
            n_class0 = sum(1 for _, outcome in resampled_pairs if outcome == 0)
            n_class1 = sum(1 for _, outcome in resampled_pairs if outcome == 1)
            structural_ok = (
                n_class0 >= minimum_class_count
                and n_class1 >= minimum_class_count
                and distinct >= minimum_temporal_blocks
            )
            if not structural_ok:
                ece_by_scope[key] = None
                for idx in scope_stats.backed_indices:
                    bin_error_by_component[(*key, idx)] = None
                continue
            replicate_bin_stats = compute_bin_stats(
                resampled_pairs, bin_count=bin_count, include_one_in_last=include_one_in_last
            )
            ece_by_scope[key] = compute_ece(
                replicate_bin_stats, scope_stats.ece_indices, total_n=len(resampled_pairs)
            )
            errors = compute_backed_bin_errors(
                replicate_bin_stats, scope_stats.backed_indices, minimum_bin_count=minimum_bin_count
            )
            for idx, value in errors.items():
                bin_error_by_component[(*key, idx)] = value
    return ReplicateComponents(ece_by_scope, bin_error_by_component)


def _percentile(values: Sequence[float], percentile: float) -> float:
    """Percentil por interpolacion lineal (metodo por defecto de numpy),
    implementado sin dependencia extra para mantener este modulo puro."""
    if not values:
        raise ValueError("No hay valores para calcular un percentil.")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (percentile / 100) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


@dataclass(frozen=True)
class JointBootstrapResult:
    replicates_requested: int
    evaluable_replicates: int
    joint_upper_bound: float | None
    insufficient_evidence: bool
    coverage_guarantee_caveat: str = (
        "Limite superior aproximado por percentil bootstrap sobre bloques temporalmente "
        "dependientes; no ofrece una garantia demostrada de cobertura simultanea exacta "
        "en muestra finita (uncertainty.coverage_guarantee_caveat)."
    )


def run_joint_multiplicity_bootstrap(
    scope_stats_by_period: Mapping[str, Sequence[ScopeFullStats]],
    blocks_by_period: Mapping[str, TemporalBlocks],
    *,
    replicates: int,
    resampling_seed: int,
    bin_count: int,
    include_one_in_last: bool,
    minimum_class_count: int,
    minimum_temporal_blocks: int,
    minimum_bin_count: int,
    nominal_level: float = 0.95,
) -> JointBootstrapResult:
    """`multiplicity.method`: un unico maximo conjunto por replica sobre
    TODOS los componentes predeclarados (ECE de cada alcance + error de
    cada bin respaldado, en todos los `scope_stats_by_period`); el limite
    reportado es el percentil `nominal_level` de esa unica distribucion.

    Si mas de la mitad de las replicas resultan no evaluables
    (`uncertainty.invalid_replicate_rule`), el resultado es
    `insufficient_evidence` y no se reporta ningun percentil calculado
    sobre la minoria evaluable.
    """
    if not (0.0 < nominal_level < 1.0):
        raise ValueError("nominal_level debe estar en (0, 1).")
    if replicates <= 0:
        raise ValueError("replicates debe ser positivo.")
    rng = random.Random(resampling_seed)
    period_ids = tuple(scope_stats_by_period)  # orden fijo para reproducibilidad del sorteo
    maxima: list[float] = []
    for _ in range(replicates):
        drawn_by_period = {
            period_id: draw_block_replicate(blocks_by_period[period_id], rng)
            for period_id in period_ids
        }
        components = compute_replicate_components(
            scope_stats_by_period,
            blocks_by_period,
            drawn_by_period,
            bin_count=bin_count,
            include_one_in_last=include_one_in_last,
            minimum_class_count=minimum_class_count,
            minimum_temporal_blocks=minimum_temporal_blocks,
            minimum_bin_count=minimum_bin_count,
        )
        joint_max = components.joint_maximum()
        if joint_max is not None:
            maxima.append(joint_max)
    evaluable = len(maxima)
    if evaluable <= replicates / 2:
        return JointBootstrapResult(replicates, evaluable, None, True)
    upper_bound = _percentile(maxima, nominal_level * 100)
    return JointBootstrapResult(replicates, evaluable, upper_bound, False)


# ---------------------------------------------------------------------------
# Clasificacion por horizonte: passed / failed / insufficient_evidence
# ---------------------------------------------------------------------------

ASSESSMENT_PASSED = "passed"
ASSESSMENT_FAILED = "failed"
ASSESSMENT_INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class HorizonAssessment:
    horizon: int
    assessment_result: str
    reasons: tuple[str, ...]
    joint_upper_bound: float | None
    epsilon_ece: float
    epsilon_bin: float
    evaluable_replicate_fraction: float | None
    coverage_guarantee_caveat: str


def classify_horizon(
    horizon: int,
    *,
    support_results: Sequence[SupportCheckResult],
    bootstrap_result: JointBootstrapResult,
    epsilon_ece: float,
    epsilon_bin: float,
) -> HorizonAssessment:
    """design.md, "Regla de presentacion, por horizonte": exige soporte
    completo en TODOS los alcances predeclarados de este horizonte (todas
    las semillas, el periodo completo y cada ventana) y, si eso se cumple,
    el limite conjunto U (`bootstrap_result`, compartido por toda la familia
    evaluada junto con este horizonte) acotado por ambas tolerancias.

    Nota de alcance: esta funcion NO evalua los controles auxiliares de
    Brier/log-loss frente a climatologia/persistencia (design.md,
    "Regla de presentacion", punto 3) porque requieren predicciones baseline
    que este motor no calcula; esa comparacion queda pendiente (tarea 11 de
    `openspec/changes/add-daily-multihorizon-predictors/tasks.md`).
    """
    reasons: list[str] = []
    for result in support_results:
        for reason in result.reasons:
            if reason not in reasons:
                reasons.append(reason)
    evaluable_fraction = (
        bootstrap_result.evaluable_replicates / bootstrap_result.replicates_requested
        if bootstrap_result.replicates_requested
        else None
    )
    if reasons:
        return HorizonAssessment(
            horizon,
            ASSESSMENT_INSUFFICIENT_EVIDENCE,
            tuple(reasons),
            None,
            epsilon_ece,
            epsilon_bin,
            evaluable_fraction,
            bootstrap_result.coverage_guarantee_caveat,
        )
    if bootstrap_result.insufficient_evidence:
        return HorizonAssessment(
            horizon,
            ASSESSMENT_INSUFFICIENT_EVIDENCE,
            ("insufficient_evidence_bootstrap",),
            None,
            epsilon_ece,
            epsilon_bin,
            evaluable_fraction,
            bootstrap_result.coverage_guarantee_caveat,
        )
    upper_bound = bootstrap_result.joint_upper_bound
    assert upper_bound is not None  # garantizado por insufficient_evidence=False
    if upper_bound <= epsilon_ece and upper_bound <= epsilon_bin:
        return HorizonAssessment(
            horizon,
            ASSESSMENT_PASSED,
            (),
            upper_bound,
            epsilon_ece,
            epsilon_bin,
            evaluable_fraction,
            bootstrap_result.coverage_guarantee_caveat,
        )
    return HorizonAssessment(
        horizon,
        ASSESSMENT_FAILED,
        ("simultaneous_upper_bound_exceeds_tolerance",),
        upper_bound,
        epsilon_ece,
        epsilon_bin,
        evaluable_fraction,
        bootstrap_result.coverage_guarantee_caveat,
    )


# ---------------------------------------------------------------------------
# Carga de configuracion desde un manifiesto congelado/borrador
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationConfig:
    """Parametros numericos del motor, extraidos del manifiesto (no
    hardcodeados): construir con `EvaluationConfig.from_manifest` a partir
    de `config/producer-calibration-plan.frozen.v3.json` (verificado con
    `calibration_manifest.verify_frozen_calibration_manifest`) para no
    reinventar valores ya decididos."""

    bin_count: int
    include_one_in_last: bool
    minimum_bin_count: int
    minimum_class_count: int
    minimum_temporal_blocks: int
    coverage_minimum: float
    block_length_days: int
    replicates: int
    resampling_seed: int
    nominal_level: float
    epsilon_ece: float
    epsilon_bin: float
    log_loss_clipping_epsilon: float

    @classmethod
    def from_manifest(cls, manifest: Mapping[str, object]) -> EvaluationConfig:
        probability_bins = manifest["probability_bins"]
        support = manifest["support"]
        coverage = manifest["coverage"]
        uncertainty = manifest["uncertainty"]
        tolerances = manifest["tolerances"]
        log_loss = manifest["log_loss"]
        return cls(
            bin_count=probability_bins["count"],
            include_one_in_last=probability_bins["include_one_in_last"],
            minimum_bin_count=support["minimum_bin_count"],
            minimum_class_count=support["minimum_class_count"],
            minimum_temporal_blocks=support["minimum_temporal_blocks"],
            coverage_minimum=coverage["minimum"],
            block_length_days=uncertainty["block_length_days"],
            replicates=uncertainty["replicates"],
            resampling_seed=uncertainty["resampling_seed"],
            nominal_level=uncertainty["nominal_level"],
            epsilon_ece=tolerances["epsilon_ece"],
            epsilon_bin=tolerances["epsilon_bin"],
            log_loss_clipping_epsilon=log_loss["clipping_epsilon"],
        )


# ---------------------------------------------------------------------------
# Brier / log-loss y controles adicionales frente a baselines
# (design.md, "Evaluacion directa y dependencia temporal" y "Regla de
# presentacion, por horizonte", punto 3)
# ---------------------------------------------------------------------------


def _require_finite_probability(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} debe ser numerico.")
    if not math.isfinite(value):
        raise ValueError(f"{name} debe ser un valor finito.")
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} debe estar en [0, 1].")


def _require_matching_probability_outcome_series(
    probabilities: Sequence[float], outcomes: Sequence[int]
) -> None:
    if len(probabilities) == 0 or len(outcomes) == 0:
        raise ValueError("probabilities/outcomes no pueden estar vacios.")
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities y outcomes deben tener la misma longitud.")
    for probability in probabilities:
        _require_finite_probability(probability, "probability")
    for outcome in outcomes:
        if outcome not in (0, 1):
            raise ValueError("outcome debe ser 0 o 1.")


def brier_score(probabilities: Sequence[float], outcomes: Sequence[int]) -> float:
    """Brier = promedio de (probabilidad - resultado)^2. Entrada vacia,
    desalineada o con valores no finitos/fuera de [0, 1] falla explicito
    (nunca produce silenciosamente un puntaje que pueda leerse como
    aprobacion)."""
    _require_matching_probability_outcome_series(probabilities, outcomes)
    n = len(outcomes)
    return (
        sum((probability - outcome) ** 2 for probability, outcome in zip(probabilities, outcomes))
        / n
    )


def log_loss_score(
    probabilities: Sequence[float], outcomes: Sequence[int], *, clipping_epsilon: float
) -> float:
    """Log-loss binario con clipping simetrico `clipping_epsilon` (mismo
    valor para todos los comparadores, `log_loss.clipping_epsilon` del
    manifiesto): evita log(0) sin ocultar fallos de un baseline."""
    _require_matching_probability_outcome_series(probabilities, outcomes)
    if isinstance(clipping_epsilon, bool) or not isinstance(clipping_epsilon, int | float):
        raise ValueError("clipping_epsilon debe ser numerico.")
    if not (0.0 < clipping_epsilon < 0.5):
        raise ValueError("clipping_epsilon debe estar en (0, 0.5).")
    n = len(outcomes)
    total = 0.0
    for probability, outcome in zip(probabilities, outcomes):
        clipped = min(max(probability, clipping_epsilon), 1.0 - clipping_epsilon)
        total += -(outcome * math.log(clipped) + (1 - outcome) * math.log(1.0 - clipped))
    return total / n


def climatology_probability_from_training(training_outcomes: Sequence[int]) -> float:
    """Prevalencia observada EXCLUSIVAMENTE en `partitions.train`
    (design.md: "climatologia ajustada en entrenamiento"). El llamador es
    responsable de que `training_outcomes` provenga solo del tramo de
    entrenamiento, nunca de calibracion o evaluacion."""
    if len(training_outcomes) == 0:
        raise ValueError("training_outcomes no puede estar vacio.")
    for outcome in training_outcomes:
        if outcome not in (0, 1):
            raise ValueError("training_outcomes debe contener solo 0 o 1.")
    return sum(training_outcomes) / len(training_outcomes)


@dataclass(frozen=True)
class BaselineComparisonInputs:
    """Probabilidades calibrada, raw y de persistencia, junto con los
    resultados observados, para UN alcance (horizonte, semilla, periodo).
    `climatology_probability` es un escalar ya estimado solo en
    entrenamiento (`climatology_probability_from_training`), no una serie
    por fecha: la climatologia no varia por fecha de emision.

    Construir con `build_baseline_comparison_inputs`, que verifica que las
    tres series compartan EXACTAMENTE el mismo conjunto de fechas
    (design.md: "comparar... sobre exactamente las mismas fechas") antes de
    aceptar la entrada; instanciar este dataclass directamente con series
    desalineadas o con fechas de mas/de menos falla en `__post_init__`.
    """

    horizon: int
    seed: int
    period_id: str
    outcomes_by_date: Mapping[date, int]
    calibrated_by_date: Mapping[date, float]
    raw_by_date: Mapping[date, float]
    persistence_by_date: Mapping[date, float]
    climatology_probability: float

    def __post_init__(self) -> None:
        if not self.outcomes_by_date:
            raise ValueError("outcomes_by_date no puede estar vacio.")
        reference_dates = set(self.outcomes_by_date)
        for name, series in (
            ("calibrated_by_date", self.calibrated_by_date),
            ("raw_by_date", self.raw_by_date),
            ("persistence_by_date", self.persistence_by_date),
        ):
            if set(series) != reference_dates:
                raise ValueError(
                    f"{name} debe cubrir exactamente las mismas fechas que outcomes_by_date "
                    "(fechas incompatibles entre calibrado/raw/persistencia/resultados)."
                )
            for probability in series.values():
                _require_finite_probability(probability, name)
        for outcome in self.outcomes_by_date.values():
            if outcome not in (0, 1):
                raise ValueError("outcomes_by_date debe contener solo 0 o 1.")
        _require_finite_probability(self.climatology_probability, "climatology_probability")

    @property
    def sorted_dates(self) -> tuple[date, ...]:
        return tuple(sorted(self.outcomes_by_date))

    def aligned_outcomes(self) -> tuple[int, ...]:
        dates = self.sorted_dates
        return tuple(self.outcomes_by_date[day] for day in dates)

    def aligned(self, series: Mapping[date, float]) -> tuple[float, ...]:
        dates = self.sorted_dates
        return tuple(series[day] for day in dates)


def build_baseline_comparison_inputs(
    *,
    horizon: int,
    seed: int,
    period_id: str,
    outcomes: Sequence[tuple[date, int]],
    calibrated_probabilities: Sequence[tuple[date, float]],
    raw_probabilities: Sequence[tuple[date, float]],
    persistence_probabilities: Sequence[tuple[date, float]],
    climatology_probability: float,
) -> BaselineComparisonInputs:
    """Arma `BaselineComparisonInputs` a partir de series (fecha, valor)
    posiblemente en cualquier orden; rechaza fechas duplicadas dentro de
    una misma serie y fechas que no coincidan exactamente entre series."""

    def _to_mapping(name: str, series: Sequence[tuple[date, float | int]]) -> dict:
        mapping: dict = {}
        for day, value in series:
            if day in mapping:
                raise ValueError(f"{name} contiene la fecha {day} duplicada.")
            mapping[day] = value
        return mapping

    return BaselineComparisonInputs(
        horizon=horizon,
        seed=seed,
        period_id=period_id,
        outcomes_by_date=_to_mapping("outcomes", outcomes),
        calibrated_by_date=_to_mapping("calibrated_probabilities", calibrated_probabilities),
        raw_by_date=_to_mapping("raw_probabilities", raw_probabilities),
        persistence_by_date=_to_mapping("persistence_probabilities", persistence_probabilities),
        climatology_probability=climatology_probability,
    )


@dataclass(frozen=True)
class BaselineComparisonResult:
    horizon: int
    seed: int
    period_id: str
    n: int
    brier_calibrated: float
    brier_raw: float
    brier_climatology: float
    brier_persistence: float
    log_loss_calibrated: float
    log_loss_raw: float
    log_loss_climatology: float
    log_loss_persistence: float
    ok: bool
    reasons: tuple[str, ...]


def compare_against_baselines(
    inputs: BaselineComparisonInputs, *, clipping_epsilon: float
) -> BaselineComparisonResult:
    """Controles adicionales de utilidad (design.md, "Regla de
    presentacion", punto 3): Brier calibrado < climatologia, Brier
    calibrado <= raw, log-loss calibrado <= raw. Persistencia se calcula y
    se reporta siempre, pero NUNCA participa de `ok`/`reasons`: no se
    inventa un cuarto requisito de aprobacion a partir de ella.
    """
    outcomes = inputs.aligned_outcomes()
    n = len(outcomes)
    calibrated = inputs.aligned(inputs.calibrated_by_date)
    raw = inputs.aligned(inputs.raw_by_date)
    persistence = inputs.aligned(inputs.persistence_by_date)
    climatology_series = (inputs.climatology_probability,) * n

    brier_calibrated = brier_score(calibrated, outcomes)
    brier_raw = brier_score(raw, outcomes)
    brier_climatology = brier_score(climatology_series, outcomes)
    brier_persistence = brier_score(persistence, outcomes)
    log_loss_calibrated = log_loss_score(calibrated, outcomes, clipping_epsilon=clipping_epsilon)
    log_loss_raw = log_loss_score(raw, outcomes, clipping_epsilon=clipping_epsilon)
    log_loss_climatology = log_loss_score(
        climatology_series, outcomes, clipping_epsilon=clipping_epsilon
    )
    log_loss_persistence = log_loss_score(persistence, outcomes, clipping_epsilon=clipping_epsilon)

    reasons: list[str] = []
    if not (brier_calibrated < brier_climatology):
        reasons.append("brier_not_better_than_climatology")
    if not (brier_calibrated <= brier_raw):
        reasons.append("brier_not_better_than_raw")
    if not (log_loss_calibrated <= log_loss_raw):
        reasons.append("log_loss_not_better_than_raw")

    return BaselineComparisonResult(
        horizon=inputs.horizon,
        seed=inputs.seed,
        period_id=inputs.period_id,
        n=n,
        brier_calibrated=brier_calibrated,
        brier_raw=brier_raw,
        brier_climatology=brier_climatology,
        brier_persistence=brier_persistence,
        log_loss_calibrated=log_loss_calibrated,
        log_loss_raw=log_loss_raw,
        log_loss_climatology=log_loss_climatology,
        log_loss_persistence=log_loss_persistence,
        ok=not reasons,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# Decision final: diagnostico parcial de calibracion vs. aprobacion completa
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HorizonFinalDecision:
    """Diferencia explicitamente el diagnostico PARCIAL de calibracion
    (`calibration_diagnostic`, de `classify_horizon`: soporte + limite
    simultaneo de ECE/error por bin) de la APROBACION final
    (`final_result`), que ademas exige los controles de Brier/log-loss de
    `baseline_comparisons` para cada alcance requerido."""

    horizon: int
    calibration_diagnostic: HorizonAssessment
    baseline_comparisons: tuple[BaselineComparisonResult, ...]
    final_result: str
    reasons: tuple[str, ...]


def make_final_decision(
    horizon: int,
    calibration_diagnostic: HorizonAssessment,
    baseline_comparisons: Sequence[BaselineComparisonResult],
    *,
    required_scope_keys: Sequence[tuple[int, str]],
) -> HorizonFinalDecision:
    """`final_result` solo es `ASSESSMENT_PASSED` si TODOS los controles se
    verificaron para TODOS los `required_scope_keys` (semilla, periodo):
    ningun control ausente, alcance incompleto o incumplimiento puede
    producir `passed` por omision.
    """
    baseline_comparisons = tuple(baseline_comparisons)

    if calibration_diagnostic.assessment_result != ASSESSMENT_PASSED:
        return HorizonFinalDecision(
            horizon,
            calibration_diagnostic,
            baseline_comparisons,
            calibration_diagnostic.assessment_result,
            calibration_diagnostic.reasons or ("calibration_diagnostic_not_passed",),
        )

    present_keys = {(comparison.seed, comparison.period_id) for comparison in baseline_comparisons}
    missing_keys = [key for key in required_scope_keys if key not in present_keys]
    if missing_keys:
        return HorizonFinalDecision(
            horizon,
            calibration_diagnostic,
            baseline_comparisons,
            ASSESSMENT_INSUFFICIENT_EVIDENCE,
            ("missing_baseline_comparison_for_required_scope",),
        )

    required_set = set(required_scope_keys)
    failing = [
        comparison
        for comparison in baseline_comparisons
        if (comparison.seed, comparison.period_id) in required_set and not comparison.ok
    ]
    if failing:
        combined_reasons = tuple(
            sorted({reason for comparison in failing for reason in comparison.reasons})
        )
        return HorizonFinalDecision(
            horizon,
            calibration_diagnostic,
            baseline_comparisons,
            ASSESSMENT_FAILED,
            combined_reasons,
        )

    return HorizonFinalDecision(
        horizon, calibration_diagnostic, baseline_comparisons, ASSESSMENT_PASSED, ()
    )
