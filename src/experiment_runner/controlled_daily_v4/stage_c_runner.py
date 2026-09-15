"""Runner de la Etapa C: reentrenamiento del candidato congelado y evaluación
única del holdout final (protocolo, sección 11).

Precondición, verificada por quien invoca (nunca por este módulo): la
secuencia completa de apertura del holdout (verificación de antecedentes →
reserva atómica → confirmación durable con `fsync`, ver `holdout_ledger.py`)
ya se completó ANTES de llamar a `run_stage_c` -- este runner nunca reserva
ni confirma el ledger por sí mismo, y nunca decide si el holdout puede
abrirse: solo evalúa, una vez que ya está legítimamente abierto.

Reutiliza exactamente family/hiperparámetros/pesos de combinación del
candidato ya congelado en A y aprobado en B (leído vía el contrato de
transferencia): no hace búsqueda de hiperparámetros, ni selección
alternativa, ni calibración, ni ajuste de umbrales, ni prueba candidatos
alternativos -- ninguna llamada de este módulo puede producir eso.

Distinto de `stage_b_runner.py` en un punto metodológico central: C
reentrena sobre un período EXTENDIDO (`target_timestamp <= 2023-12-31`, que
incorpora 2023) y recalcula `P20_train` exclusivamente sobre ese rango -- por
lo tanto NUNCA compara ese `P20_train` recalculado contra
`contract.final_p20_train` (a diferencia de B, que sí exige esa igualdad
porque reentrena sobre el MISMO período que A). Exigir esa igualdad en C
sería una contradicción con el propio protocolo, no un control de seguridad.

C tampoco produce ningún veredicto de aprobación/rechazo (esa compuerta es
exclusiva de B, protocolo sección 10): un resultado desfavorable de C nunca
autoriza repetir la evaluación. El intervalo pareado de bootstrap se reporta
aquí como diagnóstico adicional (mismo mecanismo ya normativo de A/B), nunca
como una regla de aprobación trasladada automáticamente desde B."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.baselines import (
    predict_constant_stress_baseline,
    predict_majority_class_baseline,
    predict_persistence_baseline_v4,
)
from experiment_runner.controlled_daily_v4.bootstrap import (
    BootstrapDiagnostics,
    NoValidBootstrapReplicasError,
    PairedBootstrapResult,
    paired_bootstrap_delta,
)
from experiment_runner.controlled_daily_v4.config import (
    BOOTSTRAP_BLOCK_DAYS,
    BOOTSTRAP_REPLICAS_DEFAULT,
    BOOTSTRAP_SEED,
    DECISION_THRESHOLD,
    STAGE_C_BOUNDS,
    STAGE_C_TRAINING_BOUNDS,
    CalendarIntegrityError,
)
from experiment_runner.controlled_daily_v4.dataset_fingerprint import compute_dataset_fingerprint
from experiment_runner.controlled_daily_v4.features import (
    FEATURE_COLUMNS,
    build_feature_frame,
    build_target,
    compute_p20_threshold,
    restrict_to_stage_window,
    select_eligible_rows,
    validate_stage_window_full_coverage,
)
from experiment_runner.controlled_daily_v4.metrics import is_monoclass, mcc_strict, metrics_payload
from experiment_runner.controlled_daily_v4.models import (
    ModelConfig,
    SoftVotingSpec,
    fit_candidate,
    fit_estimator,
)
from experiment_runner.controlled_daily_v4.transfer_contract import FrozenConfigContract
from experiment_runner.controlled_daily_v4.warnings_capture import collect_context_warnings

STAGE_C_BOOTSTRAP_SEGMENT_ID = "stage_c_2024_2025"
"""Mismo mecanismo, decisión y justificación que `stage_b_runner.STAGE_B_BOOTSTRAP_SEGMENT_ID`
(Decisión 1, adoptada para este encargo): el período evaluable de C
(2024-01-04..2025-12-31) es un único segmento temporal continuo para el
moving-block bootstrap pareado -- no circular, bloques de 30 días, semilla
20250109. Aquí es exclusivamente DIAGNÓSTICO (ver docstring del módulo):
ningún umbral de aprobación se deriva de este intervalo."""

REASON_TRAINING_LABELS_MONOCLASS = "training_labels_monoclass_refit_skipped"
REASON_EVALUATION_LABELS_MONOCLASS = "evaluation_labels_2024_2025_monoclass"
REASON_BOOTSTRAP_NO_VALID_REPLICAS = "bootstrap_no_valid_replicas"


class StageCTechnicalError(RuntimeError):
    """Fallo técnico de la Etapa C (cobertura insuficiente, integridad de
    calendario, u otra condición que impide completar el cálculo de forma
    confiable) -- nunca un resultado experimental desfavorable, y nunca una
    razón para reintentar el acceso al holdout (eso lo decide el ledger, no
    este módulo)."""


def build_stage_c_training_frame(daily_series: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    """Conjunto de ENTRENAMIENTO autorizado de C: `target_timestamp <=
    2023-12-31` (protocolo, sección 11; `STAGE_C_TRAINING_BOUNDS`) -- la
    extensión exacta de A+B, nunca solo el período de A. Ninguna etiqueta de
    este conjunto depende de humedad de 2024: `restrict_to_stage_window`
    recorta ANTES de construir cualquier feature."""
    restricted = restrict_to_stage_window(daily_series, STAGE_C_TRAINING_BOUNDS)
    frame = build_feature_frame(restricted, depth_column)
    return select_eligible_rows(frame, STAGE_C_TRAINING_BOUNDS)


def build_stage_c_evaluation_frame(daily_series: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    """Conjunto de EVALUACIÓN única del holdout de C: `target_timestamp` entre
    `2024-01-04` y `2025-12-31` (protocolo, sección 5/11; `STAGE_C_BOUNDS`).
    Ninguna fila fuera de este rango llega al constructor de features."""
    restricted = restrict_to_stage_window(daily_series, STAGE_C_BOUNDS)
    frame = build_feature_frame(restricted, depth_column)
    return select_eligible_rows(frame, STAGE_C_BOUNDS)


def _model_config_from_candidate(candidate) -> ModelConfig:
    return ModelConfig(family=candidate.family, params=dict(candidate.params))


def refit_frozen_candidate_for_stage_c(
    contract: FrozenConfigContract,
    training_frame: pd.DataFrame,
    warnings_log: list[dict[str, Any]] | None = None,
    *,
    p20_train: float,
) -> Any:
    """Reentrena, sobre `training_frame` (el conjunto EXTENDIDO de
    entrenamiento autorizado de C), la familia, hiperparámetros y (si
    corresponde) pesos de combinación de Soft Voting ya congelados por A y
    aprobados por B, leídos del contrato -- nunca los recalcula, nunca hace
    búsqueda de hiperparámetros. `p20_train` debe ser el umbral YA calculado
    por quien invoca sobre este mismo `training_frame` (recalculado
    exclusivamente para C, nunca el de A/B) -- se reutiliza tal cual para
    construir las etiquetas de entrenamiento.

    Deliberadamente NO reutiliza `stage_b_runner.refit_frozen_candidate`: esa
    función etiqueta las advertencias de ajuste con `stage='B'` de forma fija,
    lo que mezclaría evidencia de reproducibilidad entre etapas si se
    reutilizara aquí sin cambios. La lógica de ajuste en sí (`models.fit_candidate`/
    `fit_estimator`) es exactamente la misma, sin duplicar su implementación."""
    y = build_target(training_frame["future_soil_moisture"], p20_train).to_numpy()
    X = training_frame[list(FEATURE_COLUMNS)].to_numpy()

    if contract.soft_voting_bases is not None:
        base_configs = {
            family: _model_config_from_candidate(candidate)
            for family, candidate in contract.soft_voting_bases.items()
        }
        if warnings_log is not None:
            with collect_context_warnings(
                warnings_log, stage="C", phase="refit", family="soft_voting"
            ):
                return fit_candidate(SoftVotingSpec(base_configs), X, y)
        return fit_candidate(SoftVotingSpec(base_configs), X, y)

    if contract.single_family is None:
        raise StageCTechnicalError(
            "El contrato declara candidate_produced=true pero no expone ni 'single_family' ni "
            "'soft_voting_bases' -- no hay candidato congelado para reentrenar (esto debería "
            "haberse rechazado ya en la lectura estructural del contrato)"
        )
    model_config = _model_config_from_candidate(contract.single_family)
    if warnings_log is not None:
        with collect_context_warnings(
            warnings_log, stage="C", phase="refit", family=model_config.family
        ):
            return fit_estimator(model_config.family, model_config.params, X, y)
    return fit_estimator(model_config.family, model_config.params, X, y)


@dataclass
class StageCResult:
    training_frame_n_rows: int
    training_dataset_fingerprint: dict[str, Any]
    p20_train: float
    evaluation_frame_n_rows: int
    evaluation_target_timestamp_min: str | None
    evaluation_target_timestamp_max: str | None
    feature_timestamps: np.ndarray
    y_true: np.ndarray
    y_pred_candidate: np.ndarray
    y_score_candidate: np.ndarray
    y_pred_persistence: np.ndarray
    y_pred_majority_class: np.ndarray
    y_pred_constant_stress: np.ndarray
    metrics_candidate: dict[str, Any]
    metrics_persistence: dict[str, Any]
    metrics_majority_class: dict[str, Any]
    metrics_constant_stress: dict[str, Any]
    mcc_candidate: float
    mcc_persistence: float
    delta_mcc_point_estimate: float
    bootstrap_result: PairedBootstrapResult | None
    bootstrap_diagnostics: BootstrapDiagnostics | None
    outcome_reasons: list[str] = field(default_factory=list)
    predictions_available: bool = True
    bootstrap_executed: bool = False
    warnings_log: list[dict[str, Any]] = field(default_factory=list)


def _evaluation_labels_are_monoclass(evaluation_frame: pd.DataFrame, p20_train: float) -> bool:
    y_eval = build_target(evaluation_frame["future_soil_moisture"], p20_train).to_numpy()
    return is_monoclass(y_eval)


def run_stage_c(
    contract: FrozenConfigContract,
    daily_series: pd.DataFrame,
    *,
    bootstrap_replicas: int = BOOTSTRAP_REPLICAS_DEFAULT,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    bootstrap_block_days: int = BOOTSTRAP_BLOCK_DAYS,
    bootstrap_normative: bool = True,
) -> StageCResult:
    """Ejecuta la evaluación completa de la Etapa C sobre un candidato ya
    admisible.

    Precondiciones, verificadas por quien invoca (nunca por esta función):
    (1) `admissibility.check_stage_c_admissibility` ya se ejecutó y no
    levantó excepción; (2) la secuencia completa de apertura del holdout
    (`holdout_ledger.reserve_holdout` + `confirm_holdout_open`) ya se
    completó ANTES de que `daily_series` incluyera ninguna fila de
    2024-2025. Esta función no reserva ni confirma nada -- solo evalúa.

    `daily_series` debe cubrir, sin huecos, tanto la ventana de entrenamiento
    extendida (`STAGE_C_TRAINING_BOUNDS`) como la de evaluación
    (`STAGE_C_BOUNDS`); ambos frames se construyen una única vez y se
    reutilizan de punta a punta."""
    try:
        validate_stage_window_full_coverage(daily_series, STAGE_C_TRAINING_BOUNDS)
        validate_stage_window_full_coverage(daily_series, STAGE_C_BOUNDS)
    except CalendarIntegrityError as exc:
        raise StageCTechnicalError(
            f"Cobertura insuficiente para ejecutar la Etapa C (fallo técnico, no un resultado "
            f"experimental): {exc}"
        ) from exc

    try:
        training_frame = build_stage_c_training_frame(daily_series, contract.depth_column)
        evaluation_frame = build_stage_c_evaluation_frame(daily_series, contract.depth_column)
    except CalendarIntegrityError as exc:
        raise StageCTechnicalError(
            f"Integridad del calendario diario falló al construir los conjuntos de la Etapa C "
            f"(fallo técnico; no se ajustó ningún estimador): {exc}"
        ) from exc

    expected_targets = pd.date_range(
        STAGE_C_BOUNDS.target_start, STAGE_C_BOUNDS.target_end, freq="D"
    )
    actual_targets = pd.DatetimeIndex(
        sorted(set(pd.to_datetime(evaluation_frame["target_timestamp"]).dt.normalize()))
    )
    missing_targets = expected_targets.difference(actual_targets)
    if len(missing_targets):
        missing_dates = [str(ts.date()) for ts in missing_targets[:10]]
        raise StageCTechnicalError(
            "Cobertura incompleta del período evaluable de la Etapa C "
            f"({STAGE_C_BOUNDS.target_start}..{STAGE_C_BOUNDS.target_end}): faltan "
            f"{len(missing_targets)} fecha(s) objetivo (fallo técnico), por ejemplo: "
            f"{missing_dates}"
        )

    training_fingerprint = compute_dataset_fingerprint(training_frame)
    warnings_log: list[dict[str, Any]] = []

    # P20_train recalculado EXCLUSIVAMENTE sobre el entrenamiento extendido de
    # C (protocolo, sección 11) -- deliberadamente NUNCA comparado contra
    # contract.final_p20_train (ese chequeo es específico de B, que reentrena
    # sobre el MISMO período que A; exigirlo aquí contradiría al protocolo).
    training_p20_train = compute_p20_threshold(training_frame["future_soil_moisture"])
    y_train_for_baselines = build_target(
        training_frame["future_soil_moisture"], training_p20_train
    ).to_numpy()

    if is_monoclass(y_train_for_baselines):
        return StageCResult(
            training_frame_n_rows=len(training_frame),
            training_dataset_fingerprint=training_fingerprint,
            p20_train=float("nan"),
            evaluation_frame_n_rows=len(evaluation_frame),
            evaluation_target_timestamp_min=(
                str(evaluation_frame["target_timestamp"].min()) if len(evaluation_frame) else None
            ),
            evaluation_target_timestamp_max=(
                str(evaluation_frame["target_timestamp"].max()) if len(evaluation_frame) else None
            ),
            feature_timestamps=np.array([]),
            y_true=np.array([]),
            y_pred_candidate=np.array([]),
            y_score_candidate=np.array([]),
            y_pred_persistence=np.array([]),
            y_pred_majority_class=np.array([]),
            y_pred_constant_stress=np.array([]),
            metrics_candidate={},
            metrics_persistence={},
            metrics_majority_class={},
            metrics_constant_stress={},
            mcc_candidate=float("nan"),
            mcc_persistence=float("nan"),
            delta_mcc_point_estimate=float("nan"),
            bootstrap_result=None,
            bootstrap_diagnostics=None,
            outcome_reasons=[REASON_TRAINING_LABELS_MONOCLASS],
            predictions_available=False,
            bootstrap_executed=False,
            warnings_log=warnings_log,
        )

    estimator = refit_frozen_candidate_for_stage_c(
        contract, training_frame, warnings_log, p20_train=training_p20_train
    )

    if _evaluation_labels_are_monoclass(evaluation_frame, training_p20_train):
        y_eval = build_target(
            evaluation_frame["future_soil_moisture"], training_p20_train
        ).to_numpy()
        return StageCResult(
            training_frame_n_rows=len(training_frame),
            training_dataset_fingerprint=training_fingerprint,
            p20_train=training_p20_train,
            evaluation_frame_n_rows=len(evaluation_frame),
            evaluation_target_timestamp_min=str(evaluation_frame["target_timestamp"].min()),
            evaluation_target_timestamp_max=str(evaluation_frame["target_timestamp"].max()),
            feature_timestamps=evaluation_frame["feature_timestamp"].to_numpy(),
            y_true=y_eval,
            y_pred_candidate=np.array([]),
            y_score_candidate=np.array([]),
            y_pred_persistence=np.array([]),
            y_pred_majority_class=np.array([]),
            y_pred_constant_stress=np.array([]),
            metrics_candidate={},
            metrics_persistence={},
            metrics_majority_class={},
            metrics_constant_stress={},
            mcc_candidate=float("nan"),
            mcc_persistence=float("nan"),
            delta_mcc_point_estimate=float("nan"),
            bootstrap_result=None,
            bootstrap_diagnostics=None,
            outcome_reasons=[REASON_EVALUATION_LABELS_MONOCLASS],
            predictions_available=False,
            bootstrap_executed=False,
            warnings_log=warnings_log,
        )

    X_eval = evaluation_frame[list(FEATURE_COLUMNS)].to_numpy()
    y_true = build_target(evaluation_frame["future_soil_moisture"], training_p20_train).to_numpy()
    y_score_candidate = estimator.predict_proba(X_eval)[:, 1]
    y_pred_candidate = (y_score_candidate >= DECISION_THRESHOLD).astype(int)

    y_pred_persistence = predict_persistence_baseline_v4(
        evaluation_frame["soil_moisture"].to_numpy(), training_p20_train
    )
    y_pred_majority_class = predict_majority_class_baseline(
        y_train_for_baselines, len(evaluation_frame)
    )
    y_pred_constant_stress = predict_constant_stress_baseline(len(evaluation_frame))

    mcc_candidate = mcc_strict(y_true, y_pred_candidate)
    mcc_persistence = mcc_strict(y_true, y_pred_persistence)
    delta_point_estimate = (
        mcc_candidate - mcc_persistence
        if math.isfinite(mcc_candidate) and math.isfinite(mcc_persistence)
        else float("nan")
    )

    frame_with_segment_id = pd.DataFrame(
        {
            "feature_timestamp": evaluation_frame["feature_timestamp"].to_numpy(),
            "segment_id": STAGE_C_BOOTSTRAP_SEGMENT_ID,
        }
    ).sort_values("feature_timestamp")

    bootstrap_result: PairedBootstrapResult | None = None
    bootstrap_diagnostics: BootstrapDiagnostics | None = None
    outcome_reasons: list[str] = []
    try:
        bootstrap_result = paired_bootstrap_delta(
            y_true=y_true,
            y_pred_a=y_pred_candidate,
            y_pred_b=y_pred_persistence,
            frame_with_segment_id=frame_with_segment_id,
            metric_fn=mcc_strict,
            n_replicas=bootstrap_replicas,
            seed=bootstrap_seed,
            block_length=bootstrap_block_days,
            normative=bootstrap_normative,
        )
        bootstrap_diagnostics = bootstrap_result.diagnostics
    except NoValidBootstrapReplicasError as exc:
        bootstrap_result = None
        bootstrap_diagnostics = exc.diagnostics
        outcome_reasons.append(REASON_BOOTSTRAP_NO_VALID_REPLICAS)

    return StageCResult(
        training_frame_n_rows=len(training_frame),
        training_dataset_fingerprint=training_fingerprint,
        p20_train=training_p20_train,
        evaluation_frame_n_rows=len(evaluation_frame),
        evaluation_target_timestamp_min=str(evaluation_frame["target_timestamp"].min()),
        evaluation_target_timestamp_max=str(evaluation_frame["target_timestamp"].max()),
        feature_timestamps=evaluation_frame["feature_timestamp"].to_numpy(),
        y_true=y_true,
        y_pred_candidate=y_pred_candidate,
        y_score_candidate=y_score_candidate,
        y_pred_persistence=y_pred_persistence,
        y_pred_majority_class=y_pred_majority_class,
        y_pred_constant_stress=y_pred_constant_stress,
        metrics_candidate=metrics_payload(y_true, y_pred_candidate, y_score_candidate),
        metrics_persistence=metrics_payload(
            y_true, y_pred_persistence, y_pred_persistence.astype(float)
        ),
        metrics_majority_class=metrics_payload(
            y_true, y_pred_majority_class, y_pred_majority_class.astype(float)
        ),
        metrics_constant_stress=metrics_payload(
            y_true, y_pred_constant_stress, y_pred_constant_stress.astype(float)
        ),
        mcc_candidate=mcc_candidate,
        mcc_persistence=mcc_persistence,
        delta_mcc_point_estimate=delta_point_estimate,
        bootstrap_result=bootstrap_result,
        bootstrap_diagnostics=bootstrap_diagnostics,
        outcome_reasons=outcome_reasons,
        predictions_available=True,
        bootstrap_executed=True,
        warnings_log=warnings_log,
    )


__all__ = [
    "STAGE_C_BOOTSTRAP_SEGMENT_ID",
    "StageCResult",
    "StageCTechnicalError",
    "build_stage_c_evaluation_frame",
    "build_stage_c_training_frame",
    "refit_frozen_candidate_for_stage_c",
    "run_stage_c",
]
