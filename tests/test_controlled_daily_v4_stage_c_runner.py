"""Tests sintéticos del runner de la Etapa C (`stage_c_runner.py`).

Construye `FrozenConfigContract` directamente (misma convención que
`test_controlled_daily_v4_stage_b_runner.py`): estos tests ejercitan
reentrenamiento/evaluación/bootstrap de C, no la admisibilidad ni el ledger
(cubiertos por separado). `run_stage_c` no repite la admisibilidad ni la
secuencia de apertura del holdout por diseño: se asume ya verificada por
quien invoca."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.bootstrap import BOOTSTRAP_BLOCK_DAYS
from experiment_runner.controlled_daily_v4.config import (
    DEPTH_ROLE_PRIMARY,
    FAMILY_LOGISTIC_REGRESSION,
    PRIMARY_DEPTH_COLUMN,
    WEIGHTING_NONE,
)
from experiment_runner.controlled_daily_v4.dataset_fingerprint import (
    FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS,
    FINGERPRINT_SCOPE_STAGE_C_EXTENDED_TRAINING,
)
from experiment_runner.controlled_daily_v4.stage_c_runner import (
    REASON_EVALUATION_LABELS_MONOCLASS,
    REASON_TRAINING_LABELS_MONOCLASS,
    STAGE_C_BOOTSTRAP_SEGMENT_ID,
    build_stage_c_evaluation_frame,
    build_stage_c_training_frame,
    run_stage_c,
)
from experiment_runner.controlled_daily_v4.transfer_contract import (
    FrozenCandidate,
    FrozenConfigContract,
)

REDUCED_BOOTSTRAP_REPLICAS = 40

_LOGISTIC_PARAMS = {"C": 1.0, "weighting": WEIGHTING_NONE, "solver": "lbfgs", "max_iter": 200}


def _daily_series(n_days=4018, seed=101):
    """Misma serie estacionaria de `test_controlled_daily_v4_stage_b_runner.py`
    (2015-01-01 en adelante): cubre A, B y C sin pasar por CSV/ingestión."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-01-01", periods=n_days, freq="D")
    seasonal = np.sin(np.linspace(0, 2 * np.pi * (n_days / 365.25), n_days))
    soil_0_7 = np.clip(0.35 + 0.08 * seasonal + rng.normal(0, 0.05, n_days), 0.05, 0.65)
    rh2m = np.clip(70 + 15 * seasonal + rng.normal(0, 5, n_days), 10, 100)
    radiation = np.clip(18 + 8 * np.sin(seasonal + 1) + rng.normal(0, 3, n_days), 0, 35)
    return pd.DataFrame(
        {PRIMARY_DEPTH_COLUMN: soil_0_7, "RH2M": rh2m, "ALLSKY_SFC_SW_DWN": radiation},
        index=dates,
    )


def _contract(*, final_p20_train=None, params=None, family=FAMILY_LOGISTIC_REGRESSION):
    candidate = FrozenCandidate(
        family=family,
        params=params or dict(_LOGISTIC_PARAMS),
        median_mcc={"value": 0.3, "status": "defined"},
        fold_mcc=[],
    )
    return FrozenConfigContract(
        schema_version="controlled_daily_v4_transfer_contract.v1",
        input_mode="scientific",
        scientific_run=True,
        depth_column=PRIMARY_DEPTH_COLUMN,
        depth_role=DEPTH_ROLE_PRIMARY,
        candidate_produced=True,
        selected_family=family,
        single_family=candidate,
        soft_voting_bases=None,
        soft_voting_combination_weights=None,
        final_p20_train=final_p20_train,
        final_estimator_details={},
        producer_code_identity={},
        producer_dataset_fingerprint_ref={},
        raw={},
    )


# --------------------------------------------------------------------------
# Fronteras temporales exactas, cobertura completa, ausencia de fuga
# --------------------------------------------------------------------------


def test_training_frame_never_has_target_timestamp_after_2023_12_31():
    daily_series = _daily_series()
    training_frame = build_stage_c_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    assert len(training_frame) > 0
    max_target = pd.to_datetime(training_frame["target_timestamp"]).max()
    assert max_target.date() <= pd.Timestamp("2023-12-31").date()


def test_training_frame_includes_2023_unlike_stage_a_or_b_training():
    """C entrena sobre un período EXTENDIDO (incluye 2023), a diferencia de A/B."""
    daily_series = _daily_series()
    training_frame = build_stage_c_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    targets = pd.to_datetime(training_frame["target_timestamp"])
    assert targets.max().date() >= pd.Timestamp("2023-12-01").date()


def test_evaluation_frame_target_timestamp_matches_protocol_bounds():
    daily_series = _daily_series()
    evaluation_frame = build_stage_c_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    assert len(evaluation_frame) > 0
    targets = pd.to_datetime(evaluation_frame["target_timestamp"])
    assert targets.min().date() >= pd.Timestamp("2024-01-04").date()
    assert targets.max().date() <= pd.Timestamp("2025-12-31").date()


def test_training_and_evaluation_frames_do_not_overlap_in_target_timestamp():
    daily_series = _daily_series()
    training_frame = build_stage_c_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    evaluation_frame = build_stage_c_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    train_targets = set(pd.to_datetime(training_frame["target_timestamp"]))
    eval_targets = set(pd.to_datetime(evaluation_frame["target_timestamp"]))
    assert not (train_targets & eval_targets)


def test_evaluation_frame_has_full_daily_coverage():
    daily_series = _daily_series()
    evaluation_frame = build_stage_c_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    expected = pd.date_range("2024-01-04", "2025-12-31", freq="D")
    actual = pd.DatetimeIndex(
        sorted(set(pd.to_datetime(evaluation_frame["target_timestamp"]).dt.normalize()))
    )
    assert len(expected.difference(actual)) == 0


def test_training_frame_is_invariant_to_changes_in_2024_2025_values():
    """Ninguna etiqueta de entrenamiento puede depender de humedad de 2024-2025."""
    daily_series = _daily_series()
    training_before = build_stage_c_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)

    mutated = daily_series.copy()
    mask_holdout = mutated.index >= pd.Timestamp("2024-01-01")
    mutated.loc[mask_holdout, PRIMARY_DEPTH_COLUMN] = 0.99

    training_after = build_stage_c_training_frame(mutated, PRIMARY_DEPTH_COLUMN)
    pd.testing.assert_frame_equal(
        training_before.reset_index(drop=True), training_after.reset_index(drop=True)
    )


# --------------------------------------------------------------------------
# P20_train recalculado exclusivamente sobre el entrenamiento EXTENDIDO de C
# --------------------------------------------------------------------------


def test_p20_train_is_recomputed_over_extended_training_never_compared_to_contract():
    """A diferencia de B, C NUNCA exige que el P20_train recalculado coincida
    con `contract.final_p20_train` (ese contrato es de A, con un período
    distinto). Un contrato con un final_p20_train deliberadamente absurdo no
    debe producir ningún `StageCTechnicalError`."""
    daily_series = _daily_series()
    contract = _contract(final_p20_train=-999.0)
    result = run_stage_c(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.predictions_available is True
    assert result.p20_train != -999.0


# --------------------------------------------------------------------------
# Trazabilidad del conjunto de C (revisión dirigida, hallazgo 5)
# --------------------------------------------------------------------------


def test_training_fingerprint_scope_identifies_extended_c_training():
    """El entrenamiento extendido de C (hasta 2023) nunca se etiqueta con el
    `scope` de A/B ('stage_a_eligible_rows_only'): describe un conjunto
    distinto y más amplio, que además nunca se compara por igualdad de
    huella contra A/B."""
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_c(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert (
        result.training_dataset_fingerprint["scope"] == FINGERPRINT_SCOPE_STAGE_C_EXTENDED_TRAINING
    )
    assert result.training_dataset_fingerprint["scope"] != FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS


def test_result_target_timestamps_align_with_evaluation_frame():
    """`target_timestamp` debe persistirse alineado 1:1 con `feature_timestamp`
    y con el horizonte del protocolo (D+3): sin este campo, el conjunto
    evaluado de C no es trazable por fecha objetivo."""
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_c(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    evaluation_frame = build_stage_c_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)

    assert len(result.target_timestamps) == len(result.feature_timestamps)
    assert len(result.target_timestamps) == result.evaluation_frame_n_rows
    np.testing.assert_array_equal(
        pd.to_datetime(result.target_timestamps),
        pd.to_datetime(evaluation_frame["target_timestamp"].to_numpy()),
    )
    horizon = pd.to_datetime(result.target_timestamps) - pd.to_datetime(result.feature_timestamps)
    assert set(horizon.days) == {3}


# --------------------------------------------------------------------------
# Preservación del candidato: sin tuning, sin selección alternativa
# --------------------------------------------------------------------------


def test_run_stage_c_never_calls_hyperparameter_tuning(monkeypatch):
    import experiment_runner.controlled_daily_v4.tuning as tuning_module

    def _spy(*_a, **_k):
        raise AssertionError("La Etapa C nunca debe llamar a selección de hiperparámetros")

    monkeypatch.setattr(tuning_module, "select_best_config", _spy)

    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_c(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.predictions_available is True


def test_run_stage_c_preserves_exact_hyperparameters(monkeypatch):
    """El estimador ajustado usa EXACTAMENTE los hiperparámetros del
    contrato -- se espía `fit_estimator` para verificar los argumentos, sin
    impedir que se ejecute de verdad."""
    import experiment_runner.controlled_daily_v4.stage_c_runner as stage_c_runner_module

    captured = {}
    original = stage_c_runner_module.fit_estimator

    def _spy(family, params, X, y):
        captured["family"] = family
        captured["params"] = dict(params)
        return original(family, params, X, y)

    monkeypatch.setattr(stage_c_runner_module, "fit_estimator", _spy)

    daily_series = _daily_series()
    params = {"C": 5.0, "weighting": WEIGHTING_NONE, "solver": "lbfgs", "max_iter": 300}
    contract = _contract(params=params)
    run_stage_c(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    assert captured["family"] == FAMILY_LOGISTIC_REGRESSION
    assert captured["params"] == params


# --------------------------------------------------------------------------
# Monoclase / métricas indefinidas: nunca fabricar predicciones
# --------------------------------------------------------------------------


def test_monoclass_training_labels_produce_explicit_reason_without_predictions():
    daily_series = _daily_series()
    mask_train = daily_series.index <= pd.Timestamp("2023-12-31")
    mutated = daily_series.copy()
    mutated.loc[mask_train, PRIMARY_DEPTH_COLUMN] = 0.9  # nunca por debajo de ningún P20 posible

    contract = _contract()
    result = run_stage_c(contract, mutated, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.predictions_available is False
    assert REASON_TRAINING_LABELS_MONOCLASS in result.outcome_reasons
    assert len(result.y_pred_candidate) == 0


def test_monoclass_evaluation_labels_produce_explicit_reason_without_predictions():
    daily_series = _daily_series()
    mask_eval = daily_series.index >= pd.Timestamp("2024-01-01")
    mutated = daily_series.copy()
    mutated.loc[mask_eval, PRIMARY_DEPTH_COLUMN] = 0.9

    contract = _contract()
    result = run_stage_c(contract, mutated, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.predictions_available is False
    assert REASON_EVALUATION_LABELS_MONOCLASS in result.outcome_reasons


# --------------------------------------------------------------------------
# Baselines: persistencia nunca toca humedad futura de la fila evaluada
# --------------------------------------------------------------------------


def test_persistence_baseline_never_uses_future_soil_moisture_of_the_same_row():
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_c(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.predictions_available is True

    evaluation_frame = build_stage_c_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    expected_persistence = (evaluation_frame["soil_moisture"].to_numpy() < result.p20_train).astype(
        int
    )
    np.testing.assert_array_equal(result.y_pred_persistence, expected_persistence)


# --------------------------------------------------------------------------
# Bootstrap: diagnóstico exclusivamente, mismo mecanismo que A/B
# --------------------------------------------------------------------------


def test_bootstrap_diagnostics_use_stage_c_segment_and_requested_configuration():
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_c(
        contract,
        daily_series,
        bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS,
        bootstrap_block_days=BOOTSTRAP_BLOCK_DAYS,
    )
    assert result.bootstrap_executed is True
    assert result.bootstrap_diagnostics is not None
    assert result.bootstrap_diagnostics.replicas_requested == REDUCED_BOOTSTRAP_REPLICAS
    assert result.bootstrap_diagnostics.normative is False
    assert list(result.bootstrap_diagnostics.segment_sizes.keys()) == [STAGE_C_BOOTSTRAP_SEGMENT_ID]


def test_no_verdict_field_exists_on_stage_c_result():
    """C nunca produce un veredicto de aprobación/rechazo -- a diferencia de
    `StageBResult`, `StageCResult` no expone ningún campo `verdict`."""
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_c(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert not hasattr(result, "verdict")
