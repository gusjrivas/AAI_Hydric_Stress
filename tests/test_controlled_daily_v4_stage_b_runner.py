"""Tests sintéticos del runner de la Etapa B (`stage_b_runner.py`).

Construye `FrozenConfigContract` directamente (misma convención que
`tests/test_controlled_daily_v4_admissibility.py`): estos tests ejercitan la
lógica de reentrenamiento/evaluación/bootstrap/veredicto de B, no la
admisibilidad (ya cubierta por separado). `run_stage_b` no repite la
admisibilidad por diseño (ver su docstring): se asume ya verificada por quien
invoca, exactamente como hace `cli.py`.

La mayoría de estos tests usa una configuración de bootstrap REDUCIDA
(`REDUCED_BOOTSTRAP_REPLICAS = 40`, no normativa) para mantenerlos rápidos.
Un único test (`test_bootstrap_uses_normative_configuration_when_requested`)
verifica que la configuración normativa completa (5000 réplicas, bloques de
30 días, semilla 20250109) efectivamente funciona de punta a punta."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.bootstrap import BOOTSTRAP_BLOCK_DAYS
from experiment_runner.controlled_daily_v4.config import (
    BOOTSTRAP_REPLICAS_DEFAULT,
    BOOTSTRAP_SEED,
    DEPTH_ROLE_PRIMARY,
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    PRIMARY_DEPTH_COLUMN,
    WEIGHTING_NONE,
)
from experiment_runner.controlled_daily_v4.features import compute_p20_threshold
from experiment_runner.controlled_daily_v4.metrics import mcc_strict
from experiment_runner.controlled_daily_v4.stage_b_runner import (
    REASON_BOOTSTRAP_NO_VALID_REPLICAS,
    REASON_DELTA_LOWER_BOUND_BELOW_THRESHOLD,
    REASON_EVALUATION_LABELS_MONOCLASS,
    REASON_MCC_NOT_POSITIVE,
    REASON_MCC_UNDEFINED,
    REASON_TRAINING_LABELS_MONOCLASS,
    STAGE_B_VERDICT_NOT_VALIDATED,
    STAGE_B_VERDICT_VALIDATED,
    StageBTechnicalError,
    build_stage_b_evaluation_frame,
    build_stage_b_training_frame,
    decide_stage_b_verdict,
    refit_frozen_candidate,
    run_stage_b,
)
from experiment_runner.controlled_daily_v4.transfer_contract import (
    FrozenCandidate,
    FrozenConfigContract,
)

REDUCED_BOOTSTRAP_REPLICAS = 40
"""Configuración reducida (no normativa), usada en la mayoría de estos tests
para mantenerlos rápidos -- ver el módulo docstring."""

_LOGISTIC_PARAMS = {"C": 1.0, "weighting": WEIGHTING_NONE, "solver": "lbfgs", "max_iter": 200}


def _daily_series(n_days=4018, seed=101):
    """~2015-01-01 .. ~2025-12-31: cubre A, B, y (para los tests de
    invariancia) también C, sin necesidad de pasar por CSV/ingestión.

    A diferencia de `tests.controlled_daily_v4_fixtures.make_synthetic_daily_frame`
    (que acumula una caminata aleatoria -- adecuada para ventanas cortas, pero
    que sobre 9 años completos desplaza sistemáticamente la distribución de
    2023 lejos de `P20_train` calculado sobre 2015-2022, produciendo una
    evaluación monoclase no representativa), esta serie es ESTACIONARIA
    (estacionalidad + ruido acotado, sin término acumulativo): mantiene una
    distribución comparable entre el período de entrenamiento y 2023, para
    que los tests de este módulo ejerciten el caso biclase típico."""
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


def _contract(
    *, final_p20_train=None, params=None, family=FAMILY_LOGISTIC_REGRESSION, soft_voting=False
):
    if soft_voting:
        bases = {
            FAMILY_LOGISTIC_REGRESSION: FrozenCandidate(
                family=FAMILY_LOGISTIC_REGRESSION,
                params=dict(_LOGISTIC_PARAMS),
                median_mcc={"value": 0.3, "status": "defined"},
                fold_mcc=[],
            ),
            FAMILY_RANDOM_FOREST: FrozenCandidate(
                family=FAMILY_RANDOM_FOREST,
                params={
                    "n_estimators": 50,
                    "max_depth": 4,
                    "min_samples_leaf": 5,
                    "weighting": WEIGHTING_NONE,
                    "random_state": 42,
                    "n_jobs": 1,
                },
                median_mcc={"value": 0.3, "status": "defined"},
                fold_mcc=[],
            ),
            FAMILY_HIST_GRADIENT_BOOSTING: FrozenCandidate(
                family=FAMILY_HIST_GRADIENT_BOOSTING,
                params={
                    "learning_rate": 0.1,
                    "max_iter": 50,
                    "max_leaf_nodes": 15,
                    "l2_regularization": 0.0,
                    "weighting": WEIGHTING_NONE,
                    "max_depth": None,
                    "early_stopping": False,
                    "random_state": 42,
                },
                median_mcc={"value": 0.3, "status": "defined"},
                fold_mcc=[],
            ),
        }
        return FrozenConfigContract(
            schema_version="controlled_daily_v4_transfer_contract.v1",
            input_mode="scientific",
            scientific_run=True,
            depth_column=PRIMARY_DEPTH_COLUMN,
            depth_role=DEPTH_ROLE_PRIMARY,
            candidate_produced=True,
            selected_family="soft_voting",
            single_family=None,
            soft_voting_bases=bases,
            soft_voting_combination_weights={
                FAMILY_LOGISTIC_REGRESSION: 1 / 3,
                FAMILY_RANDOM_FOREST: 1 / 3,
                FAMILY_HIST_GRADIENT_BOOSTING: 1 / 3,
            },
            final_p20_train=final_p20_train,
            final_estimator_details={},
            producer_code_identity={},
            producer_dataset_fingerprint_ref={},
            raw={},
        )

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
# Fronteras temporales exactas y ausencia de fuga por horizonte
# --------------------------------------------------------------------------


def test_training_frame_never_has_target_timestamp_after_2022_12_31():
    daily_series = _daily_series()
    training_frame = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    assert len(training_frame) > 0
    max_target = pd.to_datetime(training_frame["target_timestamp"]).max()
    assert max_target.date() <= pd.Timestamp("2022-12-31").date()


def test_evaluation_frame_target_timestamp_matches_protocol_bounds():
    daily_series = _daily_series()
    evaluation_frame = build_stage_b_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    assert len(evaluation_frame) > 0
    targets = pd.to_datetime(evaluation_frame["target_timestamp"])
    assert targets.min().date() >= pd.Timestamp("2023-01-04").date()
    assert targets.max().date() <= pd.Timestamp("2023-12-31").date()


def test_training_and_evaluation_frames_do_not_overlap_in_target_timestamp():
    daily_series = _daily_series()
    training_frame = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    evaluation_frame = build_stage_b_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    train_targets = set(pd.to_datetime(training_frame["target_timestamp"]))
    eval_targets = set(pd.to_datetime(evaluation_frame["target_timestamp"]))
    assert not (train_targets & eval_targets)


# --------------------------------------------------------------------------
# Invariancia del entrenamiento ante cambios en 2023; invariancia de B ante
# cambios en 2024-2025
# --------------------------------------------------------------------------


def test_training_frame_is_invariant_to_changes_in_2023_values():
    daily_series = _daily_series()
    training_before = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)

    mutated = daily_series.copy()
    mask_2023 = (mutated.index >= pd.Timestamp("2023-01-01")) & (
        mutated.index <= pd.Timestamp("2023-12-31")
    )
    mutated.loc[mask_2023, PRIMARY_DEPTH_COLUMN] = 999.0

    training_after = build_stage_b_training_frame(mutated, PRIMARY_DEPTH_COLUMN)
    pd.testing.assert_frame_equal(
        training_before.reset_index(drop=True), training_after.reset_index(drop=True)
    )


def test_evaluation_frame_is_invariant_to_changes_in_2024_2025_values():
    daily_series = _daily_series()
    evaluation_before = build_stage_b_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)

    mutated = daily_series.copy()
    mask_2024_2025 = mutated.index >= pd.Timestamp("2024-01-01")
    mutated.loc[mask_2024_2025, PRIMARY_DEPTH_COLUMN] = -999.0

    evaluation_after = build_stage_b_evaluation_frame(mutated, PRIMARY_DEPTH_COLUMN)
    pd.testing.assert_frame_equal(
        evaluation_before.reset_index(drop=True), evaluation_after.reset_index(drop=True)
    )


def test_run_stage_b_result_is_invariant_to_changes_in_2024_2025_values():
    daily_series = _daily_series()
    contract = _contract()

    mutated = daily_series.copy()
    mask_2024_2025 = mutated.index >= pd.Timestamp("2024-01-01")
    mutated.loc[mask_2024_2025, PRIMARY_DEPTH_COLUMN] = -999.0

    result_before = run_stage_b(
        contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS
    )
    result_after = run_stage_b(contract, mutated, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    assert result_before.mcc_candidate == result_after.mcc_candidate
    assert result_before.verdict == result_after.verdict
    np.testing.assert_array_equal(result_before.y_pred_candidate, result_after.y_pred_candidate)


# --------------------------------------------------------------------------
# Ausencia de tuning y respeto del candidato congelado, incluido Soft Voting
# --------------------------------------------------------------------------


def test_refit_never_calls_hyperparameter_selection(monkeypatch):
    import experiment_runner.controlled_daily_v4.tuning as tuning_module

    def _boom(*_a, **_k):
        raise AssertionError("refit_frozen_candidate no debe invocar tuning.select_best_config")

    monkeypatch.setattr(tuning_module, "select_best_config", _boom)

    daily_series = _daily_series()
    training_frame = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    contract = _contract()
    refit_frozen_candidate(contract, training_frame)  # no debe lanzar AssertionError


def test_refit_reuses_frozen_family_and_params_exactly():
    daily_series = _daily_series()
    training_frame = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    contract = _contract(params={**_LOGISTIC_PARAMS, "C": 7.0})

    estimator, _p20 = refit_frozen_candidate(contract, training_frame)
    assert estimator.model_.C == 7.0


def test_refit_soft_voting_respects_congealed_base_configs_and_combination_weights():
    from experiment_runner.controlled_daily_v4.models import SoftVotingClassifier

    daily_series = _daily_series()
    training_frame = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    contract = _contract(soft_voting=True)

    estimator, _p20 = refit_frozen_candidate(contract, training_frame)
    assert isinstance(estimator, SoftVotingClassifier)
    weights = estimator.combination_weights()
    for family, weight in weights.items():
        assert math.isclose(weight, 1 / 3, rel_tol=1e-9)
    assert set(weights) == {
        FAMILY_LOGISTIC_REGRESSION,
        FAMILY_RANDOM_FOREST,
        FAMILY_HIST_GRADIENT_BOOSTING,
    }


def test_run_stage_b_soft_voting_end_to_end_produces_a_verdict():
    daily_series = _daily_series()
    contract = _contract(soft_voting=True)
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.verdict in (STAGE_B_VERDICT_VALIDATED, STAGE_B_VERDICT_NOT_VALIDATED)
    assert len(result.y_pred_candidate) == result.evaluation_frame_n_rows


# --------------------------------------------------------------------------
# P20_train: coherencia entre el recalculado y el del contrato
# --------------------------------------------------------------------------


def test_p20_train_coherence_check_passes_with_matching_value():
    daily_series = _daily_series()
    training_frame = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    exact_p20 = compute_p20_threshold(training_frame["future_soil_moisture"])
    contract = _contract(final_p20_train=exact_p20)

    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert math.isclose(result.p20_train, exact_p20, rel_tol=1e-9)


def test_p20_train_coherence_check_rejects_mismatched_value_as_technical_error():
    daily_series = _daily_series()
    contract = _contract(final_p20_train=999.0)

    with pytest.raises(StageBTechnicalError):
        run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)


def test_p20_train_mismatch_is_rejected_before_any_refit_call(monkeypatch):
    """Reproduce el hallazgo: con `final_p20_train` inconsistente, el rechazo
    debe ocurrir ANTES de cualquier llamada efectiva a
    `refit_frozen_candidate` -- verificado con un espía que aborta si llega a
    invocarse. `P20_train` se calcula sobre el `training_frame` autorizado y
    se compara con el valor congelado del contrato antes de tocar el
    estimador."""
    import experiment_runner.controlled_daily_v4.stage_b_runner as sbr_module

    def _boom(*_a, **_k):
        raise AssertionError(
            "no debía intentarse reentrenar: P20_train ya era inconsistente con el contrato"
        )

    monkeypatch.setattr(sbr_module, "refit_frozen_candidate", _boom)

    daily_series = _daily_series()
    contract = _contract(final_p20_train=999.0)
    with pytest.raises(StageBTechnicalError):
        run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)


def test_p20_train_coherence_check_with_valid_contract_preserves_labels_and_behavior():
    """Con un contrato válido, el umbral P20_train validado antes del ajuste
    debe ser exactamente el mismo que efectivamente se usa para construir las
    etiquetas y reentrenar -- sin cálculos divergentes -- y el resultado debe
    conservar el comportamiento esperado (evaluación completa, veredicto
    definido)."""
    daily_series = _daily_series()
    training_frame = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    exact_p20 = compute_p20_threshold(training_frame["future_soil_moisture"])
    contract = _contract(final_p20_train=exact_p20)

    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    assert math.isclose(result.p20_train, exact_p20, rel_tol=1e-9)
    expected_y_true = (
        (
            build_stage_b_evaluation_frame(daily_series, PRIMARY_DEPTH_COLUMN)[
                "future_soil_moisture"
            ]
            < exact_p20
        )
        .astype(int)
        .to_numpy()
    )
    np.testing.assert_array_equal(result.y_true, expected_y_true)
    assert result.verdict in (STAGE_B_VERDICT_VALIDATED, STAGE_B_VERDICT_NOT_VALIDATED)
    assert len(result.y_pred_candidate) == result.evaluation_frame_n_rows


# --------------------------------------------------------------------------
# Aprobación/rechazo de la regla, incluidas sus igualdades límite
# --------------------------------------------------------------------------


class _FakeBootstrapResult:
    def __init__(self, lower, upper):
        self.interval = (lower, upper)
        self.diagnostics = None
        self.deltas = np.array([])


@pytest.mark.parametrize(
    "mcc_candidate,lower_bound,expected_verdict,expected_reason",
    [
        (0.1, -0.05, STAGE_B_VERDICT_VALIDATED, None),  # igualdad límite exacta: aprueba
        (0.1, -0.0500001, STAGE_B_VERDICT_NOT_VALIDATED, REASON_DELTA_LOWER_BOUND_BELOW_THRESHOLD),
        (0.0, 0.0, STAGE_B_VERDICT_NOT_VALIDATED, REASON_MCC_NOT_POSITIVE),  # mcc==0: no aprueba
        (-0.1, 0.1, STAGE_B_VERDICT_NOT_VALIDATED, REASON_MCC_NOT_POSITIVE),
        (0.2, 0.0, STAGE_B_VERDICT_VALIDATED, None),
        (float("nan"), 0.0, STAGE_B_VERDICT_NOT_VALIDATED, REASON_MCC_UNDEFINED),
    ],
)
def test_decide_stage_b_verdict_quadrants_including_boundary_equalities(
    mcc_candidate, lower_bound, expected_verdict, expected_reason
):
    bootstrap_result = _FakeBootstrapResult(lower_bound, lower_bound + 0.2)
    verdict, reasons = decide_stage_b_verdict(mcc_candidate, bootstrap_result)
    assert verdict == expected_verdict
    if expected_reason is not None:
        assert expected_reason in reasons
    else:
        assert reasons == []


def test_decide_stage_b_verdict_without_bootstrap_result_is_not_validated():
    verdict, reasons = decide_stage_b_verdict(0.3, None)
    assert verdict == STAGE_B_VERDICT_NOT_VALIDATED
    assert REASON_BOOTSTRAP_NO_VALID_REPLICAS in reasons


# --------------------------------------------------------------------------
# Casos monoclase, métricas indefinidas y fallos técnicos
# --------------------------------------------------------------------------


def test_monoclass_training_labels_produce_not_validated_without_refitting(monkeypatch):
    """Inyecta `is_monoclass=True` (spy/fake, no manipulación de datos): el
    train monoclase debe cortar la ejecución ANTES de invocar
    `refit_frozen_candidate` -- se verifica con un espía que aborta si se
    llega a invocar."""
    import experiment_runner.controlled_daily_v4.stage_b_runner as sbr_module

    def _boom(*a, **k):
        raise AssertionError("no debía intentarse reentrenar con train monoclase")

    monkeypatch.setattr(sbr_module, "refit_frozen_candidate", _boom)
    monkeypatch.setattr(sbr_module, "is_monoclass", lambda *_a, **_k: True)

    daily_series = _daily_series()
    contract = _contract()

    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.verdict == STAGE_B_VERDICT_NOT_VALIDATED
    assert REASON_TRAINING_LABELS_MONOCLASS in result.verdict_reasons


def test_monoclass_evaluation_labels_produce_not_validated(monkeypatch):
    """Inyecta `is_monoclass` de forma que el train (primera invocación) siga
    biclase pero la evaluación (segunda invocación, dentro de
    `_evaluation_labels_are_monoclass`) resulte monoclase -- aísla la rama de
    evaluación monoclase de la de entrenamiento sin fabricar un `DataFrame`
    sintético con una distribución específica."""
    import experiment_runner.controlled_daily_v4.stage_b_runner as sbr_module

    calls = {"n": 0}

    def _fake(y):
        calls["n"] += 1
        if calls["n"] == 1:
            return False  # train: biclase
        return True  # evaluación: monoclase

    monkeypatch.setattr(sbr_module, "is_monoclass", _fake)

    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    assert result.verdict == STAGE_B_VERDICT_NOT_VALIDATED
    assert REASON_EVALUATION_LABELS_MONOCLASS in result.verdict_reasons


def test_technical_failure_is_distinct_from_experimental_not_validated():
    """Un fallo técnico (`StageBTechnicalError`) nunca se confunde con un
    veredicto experimental `CANDIDATE_NOT_VALIDATED`: es una excepción, no un
    `StageBResult` con veredicto."""
    daily_series = _daily_series()
    contract = _contract(final_p20_train=-12345.0)
    with pytest.raises(StageBTechnicalError):
        run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)


# --------------------------------------------------------------------------
# Persistencia del resultado monoclase con datos REALMENTE monoclase
# (revisión externa 2026-09-14, hallazgo sobre persistencia del resultado
# monoclase): reproduce la humedad de 2023 fijada, sin monkeypatch de
# `is_monoclass`, y verifica que `run_stage_b` produzca un `StageBResult`
# internamente consistente (arrays sin longitudes divergentes) que
# `write_stage_b_artifacts` pueda serializar sin lanzar `ValueError`.
# --------------------------------------------------------------------------


def _daily_series_with_constant_2023_moisture(value=0.9):
    """Misma serie de `_daily_series()`, con la humedad de suelo de TODO 2023
    fijada a `value` -- reproduce exactamente la humedad sintética de 2023
    fijada en 0.9 de la revisión externa: `future_soil_moisture` queda
    constante para toda fila evaluable de B, por lo que su target binario
    (`build_target`) también resulta constante (monoclase), sin necesidad de
    inyectar ningún fake/monkeypatch sobre `is_monoclass`."""
    daily_series = _daily_series()
    mask_2023 = (daily_series.index >= pd.Timestamp("2023-01-01")) & (
        daily_series.index <= pd.Timestamp("2023-12-31")
    )
    mutated = daily_series.copy()
    mutated.loc[mask_2023, PRIMARY_DEPTH_COLUMN] = value
    return mutated


def test_run_stage_b_with_genuinely_monoclass_evaluation_data_has_no_predictions():
    daily_series = _daily_series_with_constant_2023_moisture(0.9)
    contract = _contract()

    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    assert result.verdict == STAGE_B_VERDICT_NOT_VALIDATED
    assert REASON_EVALUATION_LABELS_MONOCLASS in result.verdict_reasons
    assert result.predictions_available is False
    assert result.bootstrap_executed is False
    assert result.bootstrap_result is None
    assert result.bootstrap_diagnostics is None
    # La evidencia de la evaluación (timestamps y etiquetas verdaderas) sigue
    # completa -- 362 filas del período evaluable de 2023, no una evaluación
    # vacía por cobertura insuficiente (eso es un fallo técnico distinto, ver
    # los tests de cobertura más abajo).
    assert result.evaluation_frame_n_rows > 0
    assert len(result.y_true) == result.evaluation_frame_n_rows
    assert len(result.feature_timestamps) == result.evaluation_frame_n_rows
    assert len(result.y_pred_candidate) == 0


def test_write_stage_b_artifacts_persists_decision_for_genuinely_monoclass_result(tmp_path):
    """Recorre runner -> escritor con datos realmente monoclase: antes de la
    corrección, `write_stage_b_artifacts` fallaba con
    `ValueError: All arrays must be of the same length` y nunca llegaba a
    crear `decision.json`."""
    from experiment_runner.controlled_daily_v4 import artifacts

    daily_series = _daily_series_with_constant_2023_moisture(0.9)
    contract = _contract()
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.verdict == STAGE_B_VERDICT_NOT_VALIDATED  # precondición del test

    output_dir = tmp_path / "stage_b_monoclass"
    written = artifacts.write_stage_b_artifacts(
        output_dir,
        input_mode="scientific",
        scientific_run=False,
        resolved_config={"stage": "B"},
        producer_dir=tmp_path / "producer_unused",
        producer_contract_raw={},
        consumer_code_identity={
            "available": False,
            "source": "unavailable",
            "commit": None,
            "dirty": None,
        },
        consumer_environment_info={},
        consumer_environment_issues=[],
        result=result,
    )

    assert written["decision"].exists()
    decision = json.loads(written["decision"].read_text(encoding="utf-8"))
    assert decision["verdict"] == STAGE_B_VERDICT_NOT_VALIDATED
    assert REASON_EVALUATION_LABELS_MONOCLASS in decision["reasons"]
    assert decision["predictions_available"] is False

    holdout_status = json.loads(written["holdout_status"].read_text(encoding="utf-8"))
    assert holdout_status["stage_c_executed"] is False

    predictions = pd.read_csv(written["predictions"])
    assert len(predictions) == result.evaluation_frame_n_rows
    assert "y_pred_candidate" not in predictions.columns

    bootstrap_payload = json.loads(written["bootstrap"].read_text(encoding="utf-8"))
    assert bootstrap_payload["bootstrap_executed"] is False


def test_write_stage_b_artifacts_persists_decision_for_monoclass_training(tmp_path, monkeypatch):
    """Mismo recorrido runner -> escritor, ahora con entrenamiento monoclase
    (evaluation_frame puede tener filas, pero sin `p20_train` ni predicciones
    de ningún tipo)."""
    import experiment_runner.controlled_daily_v4.stage_b_runner as sbr_module
    from experiment_runner.controlled_daily_v4 import artifacts

    monkeypatch.setattr(sbr_module, "is_monoclass", lambda *_a, **_k: True)
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    assert result.verdict_reasons == [REASON_TRAINING_LABELS_MONOCLASS]
    assert result.predictions_available is False

    output_dir = tmp_path / "stage_b_training_monoclass"
    written = artifacts.write_stage_b_artifacts(
        output_dir,
        input_mode="scientific",
        scientific_run=False,
        resolved_config={"stage": "B"},
        producer_dir=tmp_path / "producer_unused",
        producer_contract_raw={},
        consumer_code_identity={
            "available": False,
            "source": "unavailable",
            "commit": None,
            "dirty": None,
        },
        consumer_environment_info={},
        consumer_environment_issues=[],
        result=result,
    )
    decision = json.loads(written["decision"].read_text(encoding="utf-8"))
    assert decision["verdict"] == STAGE_B_VERDICT_NOT_VALIDATED
    assert decision["predictions_available"] is False


# --------------------------------------------------------------------------
# Bootstrap pareado y no circular, con aislamiento de segmentos (Decisión 1)
# --------------------------------------------------------------------------


def test_bootstrap_treats_2023_as_a_single_continuous_segment():
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert result.bootstrap_diagnostics is not None
    assert result.bootstrap_diagnostics.n_segments == 1


def test_bootstrap_uses_normative_configuration_when_requested():
    """Única verificación de este módulo con la configuración NORMATIVA
    completa (5000 réplicas, bloques de 30 días, semilla 20250109) -- el
    resto de los tests usa `REDUCED_BOOTSTRAP_REPLICAS` para mantenerse
    rápido, según lo pedido explícitamente (no generar 5000 réplicas en cada
    test unitario)."""
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(
        contract,
        daily_series,
        bootstrap_replicas=BOOTSTRAP_REPLICAS_DEFAULT,
        bootstrap_seed=BOOTSTRAP_SEED,
        bootstrap_block_days=BOOTSTRAP_BLOCK_DAYS,
    )
    assert result.bootstrap_diagnostics is not None
    assert result.bootstrap_diagnostics.replicas_requested == BOOTSTRAP_REPLICAS_DEFAULT
    assert result.bootstrap_diagnostics.block_length == BOOTSTRAP_BLOCK_DAYS
    assert result.bootstrap_diagnostics.seed == BOOTSTRAP_SEED
    # Cierre de pendiente técnico (revisión dirigida sobre PR #193): la
    # bandera de evidencia efectivamente persistida, no solo los valores
    # numéricos -- con la configuración normativa completa debe ser True.
    assert result.bootstrap_diagnostics.normative is True


def test_bootstrap_with_reduced_replicas_never_persists_normative_true():
    """Réplicas reducidas (40, no normativas): la bandera de evidencia
    persistida debe ser `False` aunque `run_stage_b` reciba
    `bootstrap_normative=True` (su default) -- ese parámetro controla
    únicamente la validación del largo de bloque, no la etiqueta de
    evidencia."""
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(
        contract,
        daily_series,
        bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS,
        bootstrap_seed=BOOTSTRAP_SEED,
        bootstrap_block_days=BOOTSTRAP_BLOCK_DAYS,
        bootstrap_normative=True,
    )
    assert result.bootstrap_diagnostics is not None
    assert result.bootstrap_diagnostics.replicas_requested == REDUCED_BOOTSTRAP_REPLICAS
    assert result.bootstrap_diagnostics.normative is False


def test_bootstrap_with_non_normative_seed_never_persists_normative_true():
    """Semilla no normativa con el resto de la configuración normativa: la
    bandera de evidencia también debe quedar en `False`."""
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(
        contract,
        daily_series,
        bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS,
        bootstrap_seed=1234,
        bootstrap_block_days=BOOTSTRAP_BLOCK_DAYS,
    )
    assert result.bootstrap_diagnostics is not None
    assert result.bootstrap_diagnostics.seed == 1234
    assert result.bootstrap_diagnostics.normative is False


# --------------------------------------------------------------------------
# Flujo sintético completo produce las tres referencias alineadas
# --------------------------------------------------------------------------


def test_run_stage_b_produces_all_three_baseline_predictions_aligned():
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    n = result.evaluation_frame_n_rows
    assert len(result.y_pred_candidate) == n
    assert len(result.y_pred_persistence) == n
    assert len(result.y_pred_majority_class) == n
    assert len(result.y_pred_constant_stress) == n
    assert (result.y_pred_constant_stress == 1).all()
    assert set(np.unique(result.y_pred_majority_class)).issubset({0, 1})


def test_persistence_baseline_is_the_formal_comparator_of_delta_mcc():
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    expected_mcc_persistence = mcc_strict(result.y_true, result.y_pred_persistence)
    assert math.isclose(result.mcc_persistence, expected_mcc_persistence, rel_tol=1e-9) or (
        math.isnan(result.mcc_persistence) and math.isnan(expected_mcc_persistence)
    )


# --------------------------------------------------------------------------
# Cobertura y validación ANTES del ajuste (revisión externa 2026-09-14):
# ausencia de inicio/final del período evaluable de B, hueco interior,
# historia causal insuficiente, evaluación vacía por cobertura insuficiente y
# valor no finito -- todos como `StageBTechnicalError` (fallo técnico
# controlado), nunca como un veredicto experimental, y siempre ANTES de
# invocar `refit_frozen_candidate` (verificado con un espía). El caso
# completo (sin mutar nada) conserva exactamente las fronteras del protocolo.
# --------------------------------------------------------------------------


def _assert_rejected_before_refitting(monkeypatch, daily_series, contract):
    import experiment_runner.controlled_daily_v4.stage_b_runner as sbr_module

    def _boom(*_a, **_k):
        raise AssertionError("no debía intentarse reentrenar: la cobertura ya era insuficiente")

    monkeypatch.setattr(sbr_module, "refit_frozen_candidate", _boom)
    with pytest.raises(StageBTechnicalError):
        run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)


def test_series_truncated_before_end_of_2023_is_a_technical_failure_not_a_partial_result(
    monkeypatch,
):
    """Una serie que termina el 30/06/2023 (protocolo, sección 5: se exige
    el período evaluable completo hasta el 2023-12-31) debe rechazarse como
    fallo técnico -- nunca producir, en silencio, un resultado de B sobre
    menos filas de las que exige el protocolo."""
    daily_series = _daily_series()
    truncated = daily_series.loc[daily_series.index <= pd.Timestamp("2023-06-30")]
    contract = _contract()
    _assert_rejected_before_refitting(monkeypatch, truncated, contract)


def test_series_starting_after_stage_a_window_start_is_a_technical_failure(monkeypatch):
    """Una serie cuyo inicio es posterior al arranque de la ventana
    autorizada de A (incluida su historia causal) tampoco puede completar B
    en silencio con menos historia de la exigida."""
    daily_series = _daily_series()
    truncated = daily_series.loc[daily_series.index >= pd.Timestamp("2015-06-01")]
    contract = _contract()
    _assert_rejected_before_refitting(monkeypatch, truncated, contract)


def test_interior_gap_in_2023_is_a_technical_failure(monkeypatch):
    """Un hueco interior dentro del período evaluable de B (un día calendario
    completo ausente) debe rechazarse como fallo técnico, sin llegar nunca a
    reentrenar."""
    daily_series = _daily_series()
    with_gap = daily_series.drop(pd.Timestamp("2023-06-15"))
    contract = _contract()
    _assert_rejected_before_refitting(monkeypatch, with_gap, contract)


def test_insufficient_causal_history_for_stage_b_is_a_technical_failure(monkeypatch):
    """Un hueco calendario dentro de la historia causal exclusiva de B (entre
    el fin de la ventana de A y el inicio de las etiquetas evaluables de B,
    2023-01-02, que no forma parte de la ventana de entrenamiento de A) debe
    rechazarse como fallo técnico -- la historia causal de B se verifica de
    forma independiente de la de A."""
    daily_series = _daily_series()
    with_gap = daily_series.drop(pd.Timestamp("2023-01-02"))
    contract = _contract()
    _assert_rejected_before_refitting(monkeypatch, with_gap, contract)


def test_non_finite_value_in_2023_is_a_technical_failure_not_a_crash_after_refit(monkeypatch):
    """Reproduce el hallazgo original: un NaN en una columna requerida
    (`RH2M`) dentro de 2023 debía producir `CalendarIntegrityError` recién
    DESPUÉS de una llamada efectiva a `refit_frozen_candidate`. Tras la
    corrección, la validación de la evaluación ocurre antes: el espía
    confirma que el reentrenamiento nunca se invoca."""
    daily_series = _daily_series()
    with_nan = daily_series.copy()
    with_nan.loc[pd.Timestamp("2023-06-15"), "RH2M"] = float("nan")
    contract = _contract()
    _assert_rejected_before_refitting(monkeypatch, with_nan, contract)


def test_empty_evaluation_by_insufficient_coverage_is_a_technical_failure(monkeypatch):
    """Cobertura insuficiente que deja la evaluación totalmente vacía (serie
    cortada antes de que empiece siquiera el período evaluable de B) es un
    fallo técnico -- nunca un veredicto experimental "monoclase" ni un
    resultado vacío presentado como corrida terminada."""
    daily_series = _daily_series()
    truncated = daily_series.loc[daily_series.index <= pd.Timestamp("2022-12-31")]
    contract = _contract()
    _assert_rejected_before_refitting(monkeypatch, truncated, contract)


def test_complete_case_preserves_exact_protocol_boundaries():
    """El caso completo (sin truncar ni mutar nada) conserva exactamente las
    fronteras del protocolo: entrenamiento hasta 2022-12-31, evaluación
    2023-01-04..2023-12-31, sin que la validación agregada de cobertura
    recorte ni un día de más."""
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    assert result.evaluation_target_timestamp_min == "2023-01-04 00:00:00"
    assert result.evaluation_target_timestamp_max == "2023-12-31 00:00:00"
    # 2023 tiene 362 días evaluables (365 - 3 días de horizonte que exceden
    # el año, protocolo sección 5/10).
    assert result.evaluation_frame_n_rows == 362


# --------------------------------------------------------------------------
# Evidencia de reproducibilidad de B (revisión externa 2026-09-14): la
# excepción de cero réplicas válidas de bootstrap conserva sus diagnósticos
# completos, y `refit_frozen_candidate` captura advertencias reales de ajuste
# con contexto.
# --------------------------------------------------------------------------


def test_zero_valid_bootstrap_replicas_preserves_full_diagnostics(monkeypatch):
    """Si todas las réplicas bootstrap resultan inválidas, el runner no debe
    perder los diagnósticos: distingue `bootstrap_executed=True` (se
    intentó) de `bootstrap_result=None` (sin intervalo por reportar), y
    conserva las cantidades solicitadas/válidas/descartadas, la semilla, el
    largo de bloque y los segmentos -- sin reejecutar el bootstrap."""
    import experiment_runner.controlled_daily_v4.stage_b_runner as sbr_module
    from experiment_runner.controlled_daily_v4.bootstrap import (
        BootstrapDiagnostics,
        NoValidBootstrapReplicasError,
    )

    fake_diagnostics = BootstrapDiagnostics(
        replicas_requested=REDUCED_BOOTSTRAP_REPLICAS,
        replicas_valid=0,
        replicas_discarded=REDUCED_BOOTSTRAP_REPLICAS,
        n_segments=1,
        block_length=30,
        seed=BOOTSTRAP_SEED,
        normative=False,
        segment_sizes={"stage_b_2023": 362},
        discard_reasons={"undefined_metric": REDUCED_BOOTSTRAP_REPLICAS},
        interval_lower=None,
        interval_upper=None,
    )

    def _fake_paired_bootstrap_delta(*_a, **_k):
        raise NoValidBootstrapReplicasError("ninguna réplica válida", diagnostics=fake_diagnostics)

    monkeypatch.setattr(sbr_module, "paired_bootstrap_delta", _fake_paired_bootstrap_delta)

    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)

    assert result.bootstrap_executed is True
    assert result.bootstrap_result is None
    assert result.bootstrap_diagnostics is fake_diagnostics
    assert result.bootstrap_diagnostics.replicas_requested == REDUCED_BOOTSTRAP_REPLICAS
    assert result.bootstrap_diagnostics.replicas_valid == 0
    assert result.bootstrap_diagnostics.replicas_discarded == REDUCED_BOOTSTRAP_REPLICAS
    assert result.bootstrap_diagnostics.segment_sizes == {"stage_b_2023": 362}
    assert REASON_BOOTSTRAP_NO_VALID_REPLICAS in result.verdict_reasons


def test_refit_captures_real_fitting_warnings_with_context():
    """Provoca una advertencia REAL de ajuste (no fabricada): regresión
    logística con `max_iter` insuficiente para converger sobre los datos
    sintéticos de este módulo. `refit_frozen_candidate` debe capturarla en
    `warnings_log` con contexto de etapa/familia, y `run_stage_b` debe
    propagar ese log en el resultado."""
    daily_series = _daily_series()
    training_frame = build_stage_b_training_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    contract = _contract(params={**_LOGISTIC_PARAMS, "max_iter": 1})

    warnings_log: list = []
    refit_frozen_candidate(contract, training_frame, warnings_log)

    assert len(warnings_log) >= 1
    assert all(
        entry.get("stage") == "B" and entry.get("phase") == "refit" for entry in warnings_log
    )


def test_run_stage_b_propagates_warnings_log():
    daily_series = _daily_series()
    contract = _contract(params={**_LOGISTIC_PARAMS, "max_iter": 1})
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert isinstance(result.warnings_log, list)
    assert len(result.warnings_log) >= 1


def test_write_stage_b_artifacts_persists_real_fitting_warnings(tmp_path):
    from experiment_runner.controlled_daily_v4 import artifacts

    daily_series = _daily_series()
    contract = _contract(params={**_LOGISTIC_PARAMS, "max_iter": 1})
    result = run_stage_b(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    assert len(result.warnings_log) >= 1  # precondición del test

    output_dir = tmp_path / "stage_b_warnings"
    written = artifacts.write_stage_b_artifacts(
        output_dir,
        input_mode="scientific",
        scientific_run=False,
        resolved_config={"stage": "B"},
        producer_dir=tmp_path / "producer_unused",
        producer_contract_raw={},
        consumer_code_identity={
            "available": False,
            "source": "unavailable",
            "commit": None,
            "dirty": None,
        },
        consumer_environment_info={},
        consumer_environment_issues=[],
        result=result,
    )

    assert written["warnings"].exists()
    warnings_payload = json.loads(written["warnings"].read_text(encoding="utf-8"))
    assert len(warnings_payload) >= 1
    assert all(
        entry.get("stage") == "B" and entry.get("phase") == "refit" for entry in warnings_payload
    )
