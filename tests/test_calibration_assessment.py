"""Pruebas del motor de evaluacion operacional (predictive_modeling.calibration_assessment).

Todas las pruebas usan fixtures sinteticos, nunca datos reales ni el dataset
`data/melchor_romero_2024_consolidado.parquet`. Los valores esperados de las
pruebas "manuales" estan derivados a mano en los comentarios; las pruebas de
"calculo" ejercitan las funciones reales del motor (nunca una formula
duplicada solo dentro del test), y las pruebas de "texto" (en
`test_calibration_manifest.py`) permanecen separadas de estas.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from predictive_modeling.calibration_assessment import (
    ASSESSMENT_FAILED,
    ASSESSMENT_INSUFFICIENT_EVIDENCE,
    ASSESSMENT_PASSED,
    EvaluationConfig,
    ScopeFullStats,
    ScopeObservations,
    SupportCheckResult,
    TemporalBlocks,
    assign_bin_index,
    backed_bin_indices,
    build_scope_full_stats,
    build_temporal_blocks,
    check_full_sample_support,
    classify_horizon,
    compute_bin_stats,
    compute_ece,
    compute_replicate_components,
    draw_block_replicate,
    ece_bin_inclusion_indices,
    run_joint_multiplicity_bootstrap,
    select_pairs_for_blocks,
)
from predictive_modeling.calibration_manifest import verify_frozen_calibration_manifest

# ---------------------------------------------------------------------------
# assign_bin_index: limites, incluidas probabilidades 0 y 1
# ---------------------------------------------------------------------------


def test_bin_boundaries_including_zero_and_one():
    assert assign_bin_index(0.0) == 0
    assert assign_bin_index(1.0, include_one_in_last=True) == 9
    with pytest.raises(ValueError):
        assign_bin_index(1.0, include_one_in_last=False)
    with pytest.raises(ValueError):
        assign_bin_index(-0.0001)
    with pytest.raises(ValueError):
        assign_bin_index(1.0001)


def test_bin_boundaries_at_exact_tenths_are_not_pushed_down_by_float_error():
    # 0.3 * 10 == 2.9999999999999996 en coma flotante binaria: sin la
    # correccion por epsilon, truncaria al bin 2 en vez del bin 3.
    assert assign_bin_index(0.1) == 1
    assert assign_bin_index(0.2) == 2
    assert assign_bin_index(0.3) == 3
    assert assign_bin_index(0.7) == 7
    assert assign_bin_index(0.9) == 9
    # Justo por debajo de un borde permanece en el bin anterior.
    assert assign_bin_index(0.2999999) == 2


# ---------------------------------------------------------------------------
# ECE: caso calculable a mano + inclusion de bins de poco soporte
# ---------------------------------------------------------------------------


def test_ece_manual_case_over_three_nonempty_bins():
    pairs = [(0.05, 1), (0.05, 0), (0.15, 1), (0.95, 1)]
    bin_stats = compute_bin_stats(pairs, bin_count=10, include_one_in_last=True)

    assert bin_stats[0].count == 2
    assert bin_stats[0].frequency == pytest.approx(0.5)
    assert bin_stats[0].mean_probability == pytest.approx(0.05)
    assert bin_stats[1].count == 1
    assert bin_stats[9].count == 1
    assert bin_stats[2].count == 0
    assert bin_stats[2].frequency is None

    ece_indices = ece_bin_inclusion_indices(bin_stats)
    assert ece_indices == frozenset({0, 1, 9})

    # A mano: 0.5*|0.5-0.05| + 0.25*|1.0-0.15| + 0.25*|1.0-0.95|
    #       = 0.5*0.45 + 0.25*0.85 + 0.25*0.05 = 0.225 + 0.2125 + 0.0125 = 0.45
    assert compute_ece(bin_stats, ece_indices, total_n=4) == pytest.approx(0.45)


def test_ece_includes_a_low_support_bin_that_backed_bin_family_excludes():
    """design.md: 'No omitir intervalos de poco soporte del calculo para
    mejorar la cifra.' Un bin no vacio pero sin soporte (3 casos, por debajo
    de minimum_bin_count=10) debe seguir sumando al ECE."""
    well_calibrated = [(0.30, 1 if i < 12 else 0) for i in range(40)]  # 12/40 = 0.30
    poorly_calibrated_low_support = [(0.75, 1)] * 3  # no vacio, sin soporte
    pairs = well_calibrated + poorly_calibrated_low_support
    bin_stats = compute_bin_stats(pairs, bin_count=10, include_one_in_last=True)

    ece_indices = ece_bin_inclusion_indices(bin_stats)
    backed_indices = backed_bin_indices(bin_stats, minimum_bin_count=10)

    assert ece_indices == frozenset({3, 7})
    assert backed_indices == frozenset({3})  # el bin de 3 casos queda fuera del respaldo

    ece_over_all_nonempty_bins = compute_ece(bin_stats, ece_indices, total_n=43)
    ece_incorrectly_filtered_by_support = compute_ece(bin_stats, backed_indices, total_n=43)

    # A mano: (40/43)*|0.30-0.30| + (3/43)*|1.0-0.75| = 0 + (3/43)*0.25
    assert ece_over_all_nonempty_bins == pytest.approx((3 / 43) * 0.25)
    assert ece_incorrectly_filtered_by_support == pytest.approx(0.0)
    assert ece_over_all_nonempty_bins > ece_incorrectly_filtered_by_support


# ---------------------------------------------------------------------------
# Bloques temporales
# ---------------------------------------------------------------------------


def test_temporal_blocks_partition_and_block_index_ceiling():
    blocks = build_temporal_blocks(date(2024, 1, 1), date(2024, 1, 8), block_length_days=3)
    assert blocks.num_blocks == 3  # ceil(8 / 3)
    assert blocks.block_index_for(date(2024, 1, 1)) == 0
    assert blocks.block_index_for(date(2024, 1, 3)) == 0
    assert blocks.block_index_for(date(2024, 1, 4)) == 1
    assert blocks.block_index_for(date(2024, 1, 8)) == 2  # ultimo bloque, solo 2 dias
    with pytest.raises(ValueError):
        blocks.block_index_for(date(2024, 1, 9))


def test_select_pairs_for_blocks_reconstructs_the_drawn_order():
    blocks = build_temporal_blocks(date(2024, 1, 1), date(2024, 1, 4), block_length_days=2)
    pairs = (
        (date(2024, 1, 1), 0.1, 0),
        (date(2024, 1, 2), 0.2, 1),
        (date(2024, 1, 3), 0.3, 0),
        (date(2024, 1, 4), 0.4, 1),
    )
    resampled = select_pairs_for_blocks(pairs, blocks, drawn_block_indices=(1, 0, 1))
    assert resampled == ((0.3, 0), (0.4, 1), (0.1, 0), (0.2, 1), (0.3, 0), (0.4, 1))


def test_draw_block_replicate_is_reproducible_given_the_same_rng_seed():
    import random

    blocks = build_temporal_blocks(date(2024, 1, 1), date(2024, 1, 20), block_length_days=2)
    first = draw_block_replicate(blocks, random.Random(7))
    second = draw_block_replicate(blocks, random.Random(7))
    third = draw_block_replicate(blocks, random.Random(8))

    assert first == second
    assert len(first) == blocks.num_blocks
    assert first != third


# ---------------------------------------------------------------------------
# Componentes faltantes -> replica completa no evaluable (sin maximo parcial)
# ---------------------------------------------------------------------------


def _two_block_scope(*, minimum_bin_count: int) -> tuple[ScopeFullStats, TemporalBlocks]:
    blocks = build_temporal_blocks(date(2024, 1, 1), date(2024, 1, 6), block_length_days=3)
    pairs = tuple(
        [(date(2024, 1, 1 + i), 0.05, 0) for i in range(3)]
        + [(date(2024, 1, 4 + i), 0.95, 1) for i in range(3)]
    )
    scope = ScopeObservations(horizon=1, seed=0, period_id="full", pairs=pairs)
    stats = build_scope_full_stats(
        scope, bin_count=10, include_one_in_last=True, minimum_bin_count=minimum_bin_count
    )
    return stats, blocks


def test_missing_component_makes_the_whole_replicate_not_evaluable_no_partial_max():
    scope_stats, blocks = _two_block_scope(minimum_bin_count=2)
    assert scope_stats.ece_indices == frozenset({0, 9})
    assert scope_stats.backed_indices == frozenset({0, 9})

    scope_stats_by_period = {"full": [scope_stats]}
    blocks_by_period = {"full": blocks}

    # Sortea (a mano, sin rng) solo el bloque 0 (tres dias, clase 0): la
    # replica pierde la clase 1 por completo.
    only_class_zero = compute_replicate_components(
        scope_stats_by_period,
        blocks_by_period,
        {"full": (0, 0)},
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=1,
        minimum_bin_count=2,
    )
    assert only_class_zero.ece_by_scope[(1, 0, "full")] is None
    assert only_class_zero.bin_error_by_component[(1, 0, "full", 0)] is None
    assert only_class_zero.bin_error_by_component[(1, 0, "full", 9)] is None
    assert not only_class_zero.is_evaluable
    assert only_class_zero.joint_maximum() is None

    # Sortea ambos bloques: la replica es evaluable (calculo manual abajo).
    balanced = compute_replicate_components(
        scope_stats_by_period,
        blocks_by_period,
        {"full": (0, 1)},
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=1,
        minimum_bin_count=2,
    )
    assert balanced.is_evaluable
    # A mano: bin0 (3 casos, prob 0.05, freq 0) y bin9 (3 casos, prob 0.95,
    # freq 1) sobre N=6: ECE = 0.5*|0-0.05| + 0.5*|1-0.95| = 0.05.
    # Error por bin respaldado: bin0 = |0-0.05| = 0.05; bin9 = |1-0.95| = 0.05.
    assert balanced.ece_by_scope[(1, 0, "full")] == pytest.approx(0.05)
    assert balanced.bin_error_by_component[(1, 0, "full", 0)] == pytest.approx(0.05)
    assert balanced.bin_error_by_component[(1, 0, "full", 9)] == pytest.approx(0.05)
    assert balanced.joint_maximum() == pytest.approx(0.05)


def test_a_buggy_partial_maximum_would_differ_from_the_correct_none():
    """Ilustra por que 'excluir solo el componente faltante' (el bug
    corregido en la revision anterior del manifiesto) es incorrecto: un
    maximo parcial sobre los componentes presentes da un numero, mientras
    que la regla correcta exige 'no evaluable' para toda la replica."""
    scope_stats, blocks = _two_block_scope(minimum_bin_count=2)
    scope_stats_by_period = {"full": [scope_stats]}
    blocks_by_period = {"full": blocks}

    components = compute_replicate_components(
        scope_stats_by_period,
        blocks_by_period,
        {"full": (0, 0)},  # solo clase 0: bin9 (clase 1) no es estimable
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=1,
        minimum_bin_count=2,
    )
    present_values = [v for v in components.ece_by_scope.values() if v is not None] + [
        v for v in components.bin_error_by_component.values() if v is not None
    ]
    assert present_values == []  # ece_by_scope tambien queda None en el bug corregido
    assert components.joint_maximum() is None  # nunca un maximo parcial


# ---------------------------------------------------------------------------
# Maximo conjunto: ECE + error por bin juntos, deterministico
# ---------------------------------------------------------------------------


def _identical_content_blocks(
    num_blocks: int, block_length_days: int
) -> tuple[ScopeFullStats, TemporalBlocks]:
    """Cada bloque contiene exactamente un par (0.2, clase 0) y un par
    (0.8, clase 1): cualquier remuestreo con reemplazo de estos bloques
    produce EXACTAMENTE los mismos bin_stats (los bloques son
    intercambiables), lo que vuelve el resultado de cada replica
    deterministico sin depender de la semilla."""
    start = date(2024, 1, 1)
    end = start + timedelta(days=num_blocks * block_length_days - 1)
    blocks = build_temporal_blocks(start, end, block_length_days=block_length_days)
    pairs = []
    for block_index in range(num_blocks):
        block_start = start + timedelta(days=block_index * block_length_days)
        pairs.append((block_start, 0.2, 0))
        pairs.append((block_start, 0.8, 1))
    scope = ScopeObservations(horizon=1, seed=0, period_id="full", pairs=tuple(pairs))
    stats = build_scope_full_stats(
        scope, bin_count=10, include_one_in_last=True, minimum_bin_count=2
    )
    return stats, blocks


def test_joint_maximum_combines_ece_and_bin_error_terms():
    scope_stats, blocks = _identical_content_blocks(num_blocks=4, block_length_days=2)
    assert scope_stats.ece_indices == frozenset({2, 8})
    assert scope_stats.backed_indices == frozenset(
        {2, 8}
    )  # 4 casos cada uno >= minimum_bin_count=2

    components = compute_replicate_components(
        {"full": [scope_stats]},
        {"full": blocks},
        {"full": (0, 1, 2, 3)},  # cada bloque es identico: el sorteo no importa
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=1,
        minimum_bin_count=2,
    )
    # A mano: ECE = 0.5*|0-0.2| + 0.5*|1-0.8| = 0.2; error bin2 = 0.2; error bin8 = 0.2.
    ece_value = components.ece_by_scope[(1, 0, "full")]
    bin2_error = components.bin_error_by_component[(1, 0, "full", 2)]
    bin8_error = components.bin_error_by_component[(1, 0, "full", 8)]
    assert ece_value == pytest.approx(0.2)
    assert bin2_error == pytest.approx(0.2)
    assert bin8_error == pytest.approx(0.2)

    joint_max = components.joint_maximum()
    assert joint_max == pytest.approx(0.2)
    assert joint_max == pytest.approx(max(ece_value, bin2_error, bin8_error))
    # Separar las familias (como hacia la revision v2, ya corregida) daria
    # el mismo numero en este ejemplo simetrico; la prueba de no-regresion
    # real vive en test_calibration_manifest.py (texto/manifiesto). Aqui
    # confirmamos que el motor realmente une ambos tipos de termino en una
    # sola coleccion antes de tomar el maximo.
    all_terms = list(components.ece_by_scope.values()) + list(
        components.bin_error_by_component.values()
    )
    assert len(all_terms) == 3
    assert joint_max == max(all_terms)


# ---------------------------------------------------------------------------
# Bootstrap conjunto: reproducibilidad de semilla, insufficient_evidence
# ---------------------------------------------------------------------------


def test_bootstrap_joint_upper_bound_is_deterministic_when_every_block_is_identical():
    """Con bloques de contenido identico, el maximo conjunto de CADA
    replica es la misma constante (0.2, ver test anterior): el percentil
    0.95 de una lista constante es esa misma constante, sin importar la
    semilla ni el numero de replicas."""
    scope_stats, blocks = _identical_content_blocks(num_blocks=4, block_length_days=2)

    result = run_joint_multiplicity_bootstrap(
        {"full": [scope_stats]},
        {"full": blocks},
        replicates=50,
        resampling_seed=2026,
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=1,
        minimum_bin_count=2,
    )
    assert not result.insufficient_evidence
    assert result.evaluable_replicates == 50
    assert result.joint_upper_bound == pytest.approx(0.2)


def test_bootstrap_declares_insufficient_evidence_when_a_threshold_is_structurally_impossible():
    """minimum_temporal_blocks=5 sobre un escenario con solo 4 bloques en
    total vuelve la condicion estructural imposible de satisfacer en
    CUALQUIER replica: 0 replicas evaluables, deterministico."""
    scope_stats, blocks = _identical_content_blocks(num_blocks=4, block_length_days=2)

    result = run_joint_multiplicity_bootstrap(
        {"full": [scope_stats]},
        {"full": blocks},
        replicates=20,
        resampling_seed=1,
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=5,  # imposible: solo hay 4 bloques
        minimum_bin_count=2,
    )
    assert result.insufficient_evidence
    assert result.evaluable_replicates == 0
    assert result.joint_upper_bound is None


def test_bootstrap_is_reproducible_for_the_same_seed_and_differs_across_seeds():
    """Cada bloque aporta 4 pares al MISMO bin (index 4), asi que cualquier
    remuestreo (con al menos 1 bloque, siempre cierto) deja ese bin
    respaldado: la evaluabilidad queda garantizada y aislada de la
    aleatoriedad, mientras que la frecuencia observada SI varia segun que
    bloques se sortean (bloques pares vs. impares tienen distinta mezcla de
    clases), dandole a la semilla un resultado no trivial que reproducir."""
    start = date(2024, 1, 1)
    block_length_days = 2
    num_blocks = 6
    end = start + timedelta(days=num_blocks * block_length_days - 1)
    blocks = build_temporal_blocks(start, end, block_length_days=block_length_days)
    pairs = []
    for i in range(num_blocks):
        block_start = start + timedelta(days=i * block_length_days)
        outcomes = (1, 1, 0, 0) if i % 2 == 0 else (1, 1, 1, 0)
        for offset, outcome in enumerate(outcomes):
            day = block_start if offset < block_length_days else block_start + timedelta(days=1)
            pairs.append((day, 0.45, outcome))
    scope = ScopeObservations(horizon=2, seed=1, period_id="full", pairs=tuple(pairs))
    scope_stats = build_scope_full_stats(
        scope, bin_count=10, include_one_in_last=True, minimum_bin_count=2
    )
    assert scope_stats.backed_indices == frozenset({4})

    kwargs = dict(
        scope_stats_by_period={"full": [scope_stats]},
        blocks_by_period={"full": blocks},
        replicates=40,
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=1,
        minimum_bin_count=2,
    )
    first = run_joint_multiplicity_bootstrap(resampling_seed=123, **kwargs)
    second = run_joint_multiplicity_bootstrap(resampling_seed=123, **kwargs)
    third = run_joint_multiplicity_bootstrap(resampling_seed=456, **kwargs)

    assert not first.insufficient_evidence
    assert first.evaluable_replicates == 40  # siempre evaluable por construccion
    assert first.joint_upper_bound is not None
    assert first.joint_upper_bound == second.joint_upper_bound
    assert first.evaluable_replicates == second.evaluable_replicates
    assert first.joint_upper_bound != third.joint_upper_bound


# ---------------------------------------------------------------------------
# check_full_sample_support
# ---------------------------------------------------------------------------


def test_full_sample_support_ok_and_violating_cases():
    scope_stats, blocks = _two_block_scope(minimum_bin_count=2)  # 3 clase 0, 3 clase 1, 2 bloques

    ok_result = check_full_sample_support(
        scope_stats,
        blocks,
        minimum_class_count=3,
        minimum_temporal_blocks=2,
        coverage_minimum=1.0,
    )
    assert ok_result.ok
    assert ok_result.reasons == ()

    violating_result = check_full_sample_support(
        scope_stats,
        blocks,
        minimum_class_count=4,  # solo hay 3 de cada clase
        minimum_temporal_blocks=3,  # solo hay 2 bloques
        coverage_minimum=1.0,
    )
    assert not violating_result.ok
    assert "insufficient_class_support" in violating_result.reasons
    assert "insufficient_temporal_blocks" in violating_result.reasons


# ---------------------------------------------------------------------------
# classify_horizon: passed / failed / insufficient_evidence
# ---------------------------------------------------------------------------


def _deterministic_bootstrap_result(replicates: int = 30):
    scope_stats, blocks = _identical_content_blocks(num_blocks=4, block_length_days=2)
    return run_joint_multiplicity_bootstrap(
        {"full": [scope_stats]},
        {"full": blocks},
        replicates=replicates,
        resampling_seed=99,
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=1,
        minimum_bin_count=2,
    )  # joint_upper_bound == 0.2 (deterministico, ver pruebas anteriores)


def test_classify_horizon_passed_when_bound_is_within_both_tolerances():
    bootstrap_result = _deterministic_bootstrap_result()
    assessment = classify_horizon(
        horizon=1,
        support_results=[SupportCheckResult(ok=True, reasons=())],
        bootstrap_result=bootstrap_result,
        epsilon_ece=0.25,
        epsilon_bin=0.25,
    )
    assert assessment.assessment_result == ASSESSMENT_PASSED
    assert assessment.joint_upper_bound == pytest.approx(0.2)
    assert assessment.reasons == ()


def test_classify_horizon_failed_when_bound_exceeds_a_tolerance():
    bootstrap_result = _deterministic_bootstrap_result()
    assessment = classify_horizon(
        horizon=1,
        support_results=[SupportCheckResult(ok=True, reasons=())],
        bootstrap_result=bootstrap_result,
        epsilon_ece=0.10,  # 0.2 > 0.10
        epsilon_bin=0.25,
    )
    assert assessment.assessment_result == ASSESSMENT_FAILED
    assert assessment.joint_upper_bound == pytest.approx(0.2)


def test_classify_horizon_insufficient_evidence_from_full_sample_support():
    bootstrap_result = _deterministic_bootstrap_result()
    assessment = classify_horizon(
        horizon=1,
        support_results=[SupportCheckResult(ok=False, reasons=("insufficient_coverage",))],
        bootstrap_result=bootstrap_result,
        epsilon_ece=0.25,
        epsilon_bin=0.25,
    )
    assert assessment.assessment_result == ASSESSMENT_INSUFFICIENT_EVIDENCE
    assert assessment.reasons == ("insufficient_coverage",)
    assert assessment.joint_upper_bound is None


def test_classify_horizon_insufficient_evidence_from_bootstrap_majority_invalid():
    scope_stats, blocks = _identical_content_blocks(num_blocks=4, block_length_days=2)
    bootstrap_result = run_joint_multiplicity_bootstrap(
        {"full": [scope_stats]},
        {"full": blocks},
        replicates=20,
        resampling_seed=1,
        bin_count=10,
        include_one_in_last=True,
        minimum_class_count=1,
        minimum_temporal_blocks=5,  # imposible: fuerza insufficient_evidence
        minimum_bin_count=2,
    )
    assessment = classify_horizon(
        horizon=1,
        support_results=[SupportCheckResult(ok=True, reasons=())],
        bootstrap_result=bootstrap_result,
        epsilon_ece=0.25,
        epsilon_bin=0.25,
    )
    assert assessment.assessment_result == ASSESSMENT_INSUFFICIENT_EVIDENCE
    assert assessment.reasons == ("insufficient_evidence_bootstrap",)


# ---------------------------------------------------------------------------
# Integracion con el manifiesto congelado v3 real (parametros sin reducir)
# ---------------------------------------------------------------------------


def test_evaluation_config_from_the_real_frozen_v3_manifest_matches_its_fields():
    repo_root = Path(__file__).resolve().parents[1]
    manifest = verify_frozen_calibration_manifest(
        repo_root / "config" / "producer-calibration-plan.frozen.v3.json"
    )
    config = EvaluationConfig.from_manifest(manifest)

    assert config.bin_count == 10
    assert config.include_one_in_last is True
    assert config.minimum_bin_count == 10
    assert config.minimum_class_count == 10
    assert config.minimum_temporal_blocks == 4
    assert config.coverage_minimum == pytest.approx(0.8)
    assert config.block_length_days == 7
    assert config.replicates == 5000
    assert config.resampling_seed == 20260919
    assert config.nominal_level == pytest.approx(0.95)
    assert config.epsilon_ece == pytest.approx(0.10)
    assert config.epsilon_bin == pytest.approx(0.15)


def test_engine_runs_end_to_end_with_the_real_manifest_parameters_unreduced():
    """No se reduce ningun parametro NUMERICO del manifiesto real
    (replicates=5000, block_length_days=7, minimum_bin_count=10,
    minimum_class_count=10, minimum_temporal_blocks=4, coverage_minimum=0.8,
    epsilon_ece=0.10, epsilon_bin=0.15): se toman tal cual de
    EvaluationConfig.from_manifest sobre el manifiesto congelado real.

    Lo que SI se reduce, de forma explicita y documentada, es la cantidad de
    alcances (1 horizonte x 2 semillas x 1 periodo, en vez de los 3x5x3 = 45
    reales) y el largo del periodo sintetico, unicamente para mantener el
    tiempo de esta prueba razonable; eso es estructura de datos del
    llamador, no un parametro del manifiesto, y se declara aqui en vez de
    aplicarse en silencio.
    """
    repo_root = Path(__file__).resolve().parents[1]
    manifest = verify_frozen_calibration_manifest(
        repo_root / "config" / "producer-calibration-plan.frozen.v3.json"
    )
    config = EvaluationConfig.from_manifest(manifest)
    assert config.replicates == 5000  # el numero real, no reducido

    start = date(2024, 10, 19)  # coincide con partitions.evaluation.start del manifiesto
    num_blocks = 6
    end = start + timedelta(days=num_blocks * config.block_length_days - 1)
    blocks = build_temporal_blocks(start, end, block_length_days=config.block_length_days)

    scopes = []
    for seed in (0, 1):
        pairs = []
        for i in range(num_blocks):
            block_start = start + timedelta(days=i * config.block_length_days)
            for offset in range(config.block_length_days):
                day = block_start + timedelta(days=offset)
                if day > end:
                    break
                probability = 0.05 + 0.03 * ((i + offset + seed) % 20)
                outcome = 1 if (i + offset + seed) % 3 == 0 else 0
                pairs.append((day, min(probability, 0.98), outcome))
        scope = ScopeObservations(
            horizon=1, seed=seed, period_id="full_evaluation", pairs=tuple(pairs)
        )
        scopes.append(
            build_scope_full_stats(
                scope,
                bin_count=config.bin_count,
                include_one_in_last=config.include_one_in_last,
                minimum_bin_count=config.minimum_bin_count,
            )
        )

    support_results = [
        check_full_sample_support(
            scope_stats,
            blocks,
            minimum_class_count=config.minimum_class_count,
            minimum_temporal_blocks=config.minimum_temporal_blocks,
            coverage_minimum=config.coverage_minimum,
        )
        for scope_stats in scopes
    ]

    bootstrap_result = run_joint_multiplicity_bootstrap(
        {"full_evaluation": scopes},
        {"full_evaluation": blocks},
        replicates=config.replicates,
        resampling_seed=config.resampling_seed,
        bin_count=config.bin_count,
        include_one_in_last=config.include_one_in_last,
        minimum_class_count=config.minimum_class_count,
        minimum_temporal_blocks=config.minimum_temporal_blocks,
        minimum_bin_count=config.minimum_bin_count,
        nominal_level=config.nominal_level,
    )
    assert bootstrap_result.replicates_requested == 5000

    assessment = classify_horizon(
        horizon=1,
        support_results=support_results,
        bootstrap_result=bootstrap_result,
        epsilon_ece=config.epsilon_ece,
        epsilon_bin=config.epsilon_bin,
    )
    assert assessment.assessment_result in {
        ASSESSMENT_PASSED,
        ASSESSMENT_FAILED,
        ASSESSMENT_INSUFFICIENT_EVIDENCE,
    }
    assert "no ofrece una garantia" in assessment.coverage_guarantee_caveat.lower()
