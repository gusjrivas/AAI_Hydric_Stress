"""Runner de la Etapa B: reentrenamiento del candidato congelado y compuerta
temporal de validación (protocolo, sección 10).

Orquesta, para el candidato ya leído estructuralmente del contrato de
transferencia A→B (`transfer_contract.load_frozen_config_contract`) y ya
declarado admisible (`admissibility.check_stage_b_admissibility`, que debe
invocarse ANTES de llamar a `run_stage_b`): el reentrenamiento con el mismo
procedimiento de congelamiento de A sobre `target_timestamp <= 2022-12-31`,
la evaluación única sobre `target_timestamp` entre 2023-01-04 y 2023-12-31,
el cálculo de los tres baselines del protocolo (sección 13), el bootstrap
pareado moving-block sobre 2023 tratado como un único segmento continuo
(Decisión 1, adoptada para este encargo -- ver
`docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md`), y el
veredicto `CANDIDATE_VALIDATED`/`CANDIDATE_NOT_VALIDATED` exacto de la
sección 10.

No hace búsqueda de hiperparámetros, ni selección alternativa, ni
calibración, ni ajuste de umbrales: reutiliza exactamente la familia, los
hiperparámetros y los pesos de combinación (Soft Voting) ya congelados por A,
leídos del contrato -- nunca los recalcula ni los ajusta con datos de 2023."""

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
    STAGE_A_BOUNDS,
    STAGE_B_BOUNDS,
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

STAGE_B_BOOTSTRAP_SEGMENT_ID = "stage_b_2023"
"""Decisión 1 (adoptada para este encargo, no atribuida a una aprobación
académica externa): la evaluación continua de 2023 constituye un único
segmento temporal para el moving-block bootstrap pareado -- no circular,
bloques de 30 días, 5000 réplicas normativas, semilla 20250109. Los mismos
índices remuestreados se aplican a candidato, persistencia y etiquetas
(apareamiento exacto, ver `bootstrap.paired_bootstrap_delta`)."""

STAGE_B_VERDICT_VALIDATED = "CANDIDATE_VALIDATED"
STAGE_B_VERDICT_NOT_VALIDATED = "CANDIDATE_NOT_VALIDATED"

REASON_MCC_NOT_POSITIVE = "candidate_mcc_2023_not_positive"
REASON_MCC_UNDEFINED = "candidate_mcc_2023_undefined"
REASON_DELTA_LOWER_BOUND_BELOW_THRESHOLD = "delta_mcc_lower_bound_below_minus_0_05"
REASON_TRAINING_LABELS_MONOCLASS = "training_labels_monoclass_refit_skipped"
REASON_EVALUATION_LABELS_MONOCLASS = "evaluation_labels_2023_monoclass"
REASON_BOOTSTRAP_NO_VALID_REPLICAS = "bootstrap_no_valid_replicas"


class StageBTechnicalError(RuntimeError):
    """Fallo técnico de la Etapa B (evidencia insuficiente, inconsistencia de
    `P20_train`, o cualquier otra condición que impida completar el cálculo
    de forma confiable) -- distinto de un veredicto experimental
    `CANDIDATE_NOT_VALIDATED` (que sí completa el cálculo, pero no aprueba) y
    distinto de un rechazo de admisibilidad (`admissibility.StageBAdmissibilityError`,
    que debe verificarse ANTES de invocar este módulo)."""


def build_stage_b_training_frame(daily_series: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    """Conjunto de entrenamiento autorizado de B: EXACTAMENTE el mismo
    procedimiento que A (`stage_a_runner.build_eligible_frame`), reimplementado
    aquí sobre los mismos primitivos (`restrict_to_stage_window`,
    `build_feature_frame`, `select_eligible_rows`) para no importar el módulo
    de la Etapa A dentro de este runner. Recorta a `STAGE_A_BOUNDS` (protocolo,
    sección 5) ANTES de construir cualquier feature: ninguna etiqueta de
    entrenamiento puede depender de humedad de 2023, porque `target_timestamp`
    nunca excede `2022-12-31` en el conjunto resultante -- el mismo corte
    controla, a la vez, el fin de la historia cruda admitida y el fin de las
    etiquetas admitidas."""
    restricted = restrict_to_stage_window(daily_series, STAGE_A_BOUNDS)
    frame = build_feature_frame(restricted, depth_column)
    return select_eligible_rows(frame, STAGE_A_BOUNDS)


def build_stage_b_evaluation_frame(daily_series: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    """Conjunto de evaluación única de B: `target_timestamp` entre
    `2023-01-04` y `2023-12-31` (protocolo, sección 5/10; `STAGE_B_BOUNDS`).
    `restrict_to_stage_window` recorta ANTES de construir features: ninguna
    fila de 2024-2025 llega jamás al constructor de features ni a la
    selección de filas elegibles de B, sin importar qué fechas traiga
    `daily_series` (aislamiento por período)."""
    restricted = restrict_to_stage_window(daily_series, STAGE_B_BOUNDS)
    frame = build_feature_frame(restricted, depth_column)
    return select_eligible_rows(frame, STAGE_B_BOUNDS)


def _model_config_from_candidate(candidate) -> ModelConfig:
    return ModelConfig(family=candidate.family, params=dict(candidate.params))


def refit_frozen_candidate(
    contract: FrozenConfigContract,
    training_frame: pd.DataFrame,
    warnings_log: list[dict[str, Any]] | None = None,
    *,
    p20_train: float | None = None,
) -> tuple[Any, float]:
    """Reentrena, sobre `training_frame` (el conjunto de entrenamiento
    autorizado de B, EXACTAMENTE el mismo período que A), la familia,
    hiperparámetros y (si corresponde) pesos de combinación de Soft Voting ya
    congelados por A y leídos del contrato -- nunca los recalcula, nunca hace
    búsqueda de hiperparámetros. Devuelve `(estimador_ajustado, p20_train)`.

    Debe invocarse solo después de que `admissibility.check_stage_b_admissibility`
    ya haya aceptado el contrato: esta función no repite esa validación.

    `p20_train`, si se recibe, es el umbral YA calculado y validado (contra
    `contract.final_p20_train`) por quien invoca -- se reutiliza tal cual
    para construir las etiquetas, sin recalcularlo aquí, para que el umbral
    verificado y el efectivamente usado para reentrenar nunca puedan
    divergir. Si no se recibe (por ejemplo, al invocar esta función
    directamente en pruebas), se calcula aquí como antes.

    Si se recibe `warnings_log`, el ajuste queda envuelto en
    `warnings_capture.collect_context_warnings` (hallazgo H-05, evidencia de
    reproducibilidad de B): cualquier advertencia real emitida durante el
    ajuste queda registrada con contexto (`stage='B'`, `phase='refit'`,
    familia), en lugar de perderse en silencio."""
    if p20_train is None:
        p20_train = compute_p20_threshold(training_frame["future_soil_moisture"])
    y = build_target(training_frame["future_soil_moisture"], p20_train).to_numpy()
    X = training_frame[list(FEATURE_COLUMNS)].to_numpy()

    if contract.soft_voting_bases is not None:
        base_configs = {
            family: _model_config_from_candidate(candidate)
            for family, candidate in contract.soft_voting_bases.items()
        }
        if warnings_log is not None:
            with collect_context_warnings(
                warnings_log, stage="B", phase="refit", family="soft_voting"
            ):
                estimator = fit_candidate(SoftVotingSpec(base_configs), X, y)
        else:
            estimator = fit_candidate(SoftVotingSpec(base_configs), X, y)
    else:
        if contract.single_family is None:
            raise StageBTechnicalError(
                "El contrato declara candidate_produced=true pero no expone ni "
                "'single_family' ni 'soft_voting_bases' -- no hay candidato congelado "
                "para reentrenar (esto debería haberse rechazado ya en la lectura "
                "estructural del contrato)"
            )
        model_config = _model_config_from_candidate(contract.single_family)
        if warnings_log is not None:
            with collect_context_warnings(
                warnings_log, stage="B", phase="refit", family=model_config.family
            ):
                estimator = fit_estimator(model_config.family, model_config.params, X, y)
        else:
            estimator = fit_estimator(model_config.family, model_config.params, X, y)

    return estimator, p20_train


@dataclass
class StageBResult:
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
    verdict: str
    verdict_reasons: list[str] = field(default_factory=list)
    # Revisión externa (2026-09-14), hallazgo sobre persistencia del
    # resultado monoclase: `predictions_available=False` cuando el resultado
    # no incluye predicciones del candidato (entrenamiento o evaluación
    # monoclase) -- representación EXPLÍCITA de ausencia, nunca inferida por
    # quien lea `len(y_pred_candidate) == 0`, y nunca predicciones fabricadas
    # ni ceros en lugar de un valor indefinido.
    predictions_available: bool = True
    # Distingue "bootstrap no ejecutado" (monoclase, `False`) de "bootstrap
    # ejecutado sin réplicas válidas" (`True`, con `bootstrap_diagnostics`
    # igual poblado pero `bootstrap_result is None`) -- hallazgo H-05,
    # evidencia de reproducibilidad de B.
    bootstrap_executed: bool = False
    warnings_log: list[dict[str, Any]] = field(default_factory=list)


def _evaluation_labels_are_monoclass(evaluation_frame: pd.DataFrame, p20_train: float) -> bool:
    y_eval = build_target(evaluation_frame["future_soil_moisture"], p20_train).to_numpy()
    return is_monoclass(y_eval)


def decide_stage_b_verdict(
    mcc_candidate: float, bootstrap_result: PairedBootstrapResult | None
) -> tuple[str, list[str]]:
    """Veredicto exacto de la compuerta de la Etapa B (protocolo, sección 10):
    `CANDIDATE_VALIDATED` sii `MCC_candidato_2023 > 0` (estrictamente) Y el
    límite inferior del intervalo pareado bootstrap de `ΔMCC_B` es `>= -0.05`
    (con igualdad incluida en el conjunto de aprobación). Cualquier otro caso
    -- MCC indefinido, MCC no positivo (incluido exactamente 0), límite
    inferior indefinido o por debajo de -0.05, o ausencia de un intervalo
    bootstrap válido -- produce `CANDIDATE_NOT_VALIDATED` con los motivos
    explícitos acumulados (nunca solo el primero). Función pura, sin efectos
    secundarios, para poder ejercitar las igualdades límite de la regla de
    forma aislada."""
    reasons: list[str] = []
    if not math.isfinite(mcc_candidate):
        reasons.append(REASON_MCC_UNDEFINED)
    elif mcc_candidate <= 0:
        reasons.append(REASON_MCC_NOT_POSITIVE)

    if bootstrap_result is None:
        reasons.append(REASON_BOOTSTRAP_NO_VALID_REPLICAS)
    else:
        lower_bound = bootstrap_result.interval[0]
        if not (math.isfinite(lower_bound) and lower_bound >= -0.05):
            reasons.append(REASON_DELTA_LOWER_BOUND_BELOW_THRESHOLD)

    verdict = STAGE_B_VERDICT_VALIDATED if not reasons else STAGE_B_VERDICT_NOT_VALIDATED
    return verdict, reasons


def run_stage_b(
    contract: FrozenConfigContract,
    daily_series: pd.DataFrame,
    *,
    bootstrap_replicas: int = BOOTSTRAP_REPLICAS_DEFAULT,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    bootstrap_block_days: int = BOOTSTRAP_BLOCK_DAYS,
    bootstrap_normative: bool = True,
) -> StageBResult:
    """Ejecuta la Etapa B completa sobre un candidato ya admisible.

    Precondición (verificada por quien invoca, no por esta función):
    `admissibility.check_stage_b_admissibility` ya se ejecutó y no levantó
    excepción para este `contract`, con el contexto explícito de esta
    ejecución concreta -- esta función no repite la lectura estructural, la
    admisibilidad, ni la revalidación de la huella de entrenamiento, aunque
    sí recalcula la huella del conjunto de entrenamiento efectivamente usado
    (para persistirla como evidencia; `run` debe pasarse la misma que ya se
    validó antes de llegar aquí).

    Revisión externa (2026-09-14), hallazgo sobre cobertura y validación
    antes del ajuste: la cobertura/calendario COMPLETOS del período de
    entrenamiento (A) y del período evaluable de B (incluida su historia
    causal) se verifican aquí, ANTES de construir cualquier feature o de
    tocar el estimador -- nunca después de una llamada efectiva a
    `refit_frozen_candidate`. Ambos frames (entrenamiento y evaluación) se
    construyen una única vez y se reutilizan de punta a punta: nunca se
    reconstruyen por separado más abajo, para que no puedan divergir. Todo
    error esperable de cobertura/calendario/valores se convierte en
    `StageBTechnicalError` (fallo técnico controlado por la CLI), nunca en un
    veredicto experimental `CANDIDATE_NOT_VALIDATED`.

    Cierre de pendiente técnico (revisión dirigida sobre PR #193): `P20_train`
    se calcula UNA vez sobre el `training_frame` autorizado y se compara con
    `contract.final_p20_train` ANTES de cualquier llamada efectiva a
    `refit_frozen_candidate` -- una inconsistencia produce `StageBTechnicalError`
    con cero llamadas de ajuste. Ese mismo umbral validado (nunca uno
    recalculado por separado) es el que se reutiliza para construir las
    etiquetas de entrenamiento y para reentrenar."""
    try:
        validate_stage_window_full_coverage(daily_series, STAGE_A_BOUNDS)
        validate_stage_window_full_coverage(daily_series, STAGE_B_BOUNDS)
    except CalendarIntegrityError as exc:
        raise StageBTechnicalError(
            f"Cobertura insuficiente para ejecutar la Etapa B (fallo técnico, no un veredicto "
            f"experimental): {exc}"
        ) from exc

    try:
        training_frame = build_stage_b_training_frame(daily_series, contract.depth_column)
        evaluation_frame = build_stage_b_evaluation_frame(daily_series, contract.depth_column)
    except CalendarIntegrityError as exc:
        raise StageBTechnicalError(
            f"Integridad del calendario diario falló al construir los conjuntos de la Etapa B "
            f"(fallo técnico, no un veredicto experimental; no se ajustó ningún estimador): {exc}"
        ) from exc

    # Cobertura EXACTA del período evaluable exigido por el protocolo
    # (`STAGE_B_BOUNDS.target_start`..`target_end`, diario): una evaluación
    # con menos filas que las esperadas por cobertura insuficiente es un
    # fallo técnico, nunca un veredicto monoclase válido (que sí puede tener
    # las filas completas del período).
    expected_targets = pd.date_range(
        STAGE_B_BOUNDS.target_start, STAGE_B_BOUNDS.target_end, freq="D"
    )
    actual_targets = pd.DatetimeIndex(
        sorted(set(pd.to_datetime(evaluation_frame["target_timestamp"]).dt.normalize()))
    )
    missing_targets = expected_targets.difference(actual_targets)
    if len(missing_targets):
        missing_dates = [str(ts.date()) for ts in missing_targets[:10]]
        raise StageBTechnicalError(
            "Cobertura incompleta del período evaluable de la Etapa B "
            f"({STAGE_B_BOUNDS.target_start}..{STAGE_B_BOUNDS.target_end}): faltan "
            f"{len(missing_targets)} fecha(s) objetivo (fallo técnico, no un veredicto "
            f"experimental), por ejemplo: {missing_dates}"
        )

    training_fingerprint = compute_dataset_fingerprint(training_frame)
    warnings_log: list[dict[str, Any]] = []

    # P20_train se calcula UNA sola vez sobre el training_frame autorizado y
    # validado, y ese mismo valor es el que se reutiliza más abajo para
    # construir las etiquetas de entrenamiento y para reentrenar -- nunca se
    # recalcula por separado, para que no puedan divergir.
    training_p20_train = compute_p20_threshold(training_frame["future_soil_moisture"])
    y_train_for_baselines = build_target(
        training_frame["future_soil_moisture"], training_p20_train
    ).to_numpy()

    if is_monoclass(y_train_for_baselines):
        # Entrenamiento monoclase (protocolo, sección 12): no se intenta
        # reentrenar un estimador que requiere dos clases -- veredicto
        # experimental explícito, no un fallo técnico ni una aprobación.
        # Sin predicciones del candidato (ausencia explícita, nunca
        # fabricada): `predictions_available=False`.
        return StageBResult(
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
            verdict=STAGE_B_VERDICT_NOT_VALIDATED,
            verdict_reasons=[REASON_TRAINING_LABELS_MONOCLASS],
            predictions_available=False,
            bootstrap_executed=False,
            warnings_log=warnings_log,
        )

    # Coherencia de P20_train (pedida explícitamente por el encargo): el
    # mismo conjunto de entrenamiento (misma huella) debe producir el mismo
    # P20_train que A ya registró en el contrato -- una discrepancia es
    # indicio de una inconsistencia entre el conjunto reentrenado aquí y el
    # que A efectivamente usó, un fallo técnico, no un resultado experimental.
    # Se valida ANTES de cualquier llamada efectiva a `refit_frozen_candidate`
    # (hallazgo reproducido: el rechazo ocurría recién después de haber
    # ajustado el estimador).
    if contract.final_p20_train is not None and not math.isclose(
        training_p20_train, contract.final_p20_train, rel_tol=1e-9, abs_tol=1e-12
    ):
        raise StageBTechnicalError(
            f"P20_train calculado en B ({training_p20_train!r}) no coincide con "
            f"final_p20_train del contrato de A ({contract.final_p20_train!r}) pese a que "
            "la huella del conjunto de entrenamiento ya fue verificada como idéntica -- "
            "inconsistencia técnica, no un resultado experimental (verificado ANTES de "
            "reentrenar: cero llamadas de ajuste en este caso)"
        )

    estimator, p20_train = refit_frozen_candidate(
        contract, training_frame, warnings_log, p20_train=training_p20_train
    )

    evaluation_monoclass = _evaluation_labels_are_monoclass(evaluation_frame, p20_train)
    if evaluation_monoclass:
        warnings_log.append(
            {
                "category": "EvaluationMonoclass",
                "message": "Predictions retained; unsupported metrics remain undefined.",
                "n_observations": len(evaluation_frame),
            }
        )

    X_eval = evaluation_frame[list(FEATURE_COLUMNS)].to_numpy()
    y_true = build_target(evaluation_frame["future_soil_moisture"], p20_train).to_numpy()
    y_score_candidate = estimator.predict_proba(X_eval)[:, 1]
    y_pred_candidate = (y_score_candidate >= DECISION_THRESHOLD).astype(int)

    y_pred_persistence = predict_persistence_baseline_v4(
        evaluation_frame["soil_moisture"].to_numpy(), p20_train
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
            "segment_id": STAGE_B_BOOTSTRAP_SEGMENT_ID,
        }
    ).sort_values("feature_timestamp")

    bootstrap_result: PairedBootstrapResult | None = None
    bootstrap_diagnostics: BootstrapDiagnostics | None = None
    if not evaluation_monoclass:
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
            # Bootstrap EJECUTADO pero sin réplicas válidas: los diagnósticos
            # completos (solicitadas/válidas/descartadas, motivos, semilla, largo
            # de bloque y segmentos) viajan adjuntos a la excepción (hallazgo
            # H-05) -- nunca se pierden ni se reejecuta el bootstrap para
            # reconstruirlos. Distinto de `bootstrap_executed=False` (monoclase,
            # bootstrap ni siquiera se intentó).
            bootstrap_result = None
            bootstrap_diagnostics = exc.diagnostics

    verdict, verdict_reasons = decide_stage_b_verdict(mcc_candidate, bootstrap_result)

    if evaluation_monoclass:
        verdict_reasons.append(REASON_EVALUATION_LABELS_MONOCLASS)

    def evaluate_metrics(y_true, y_pred, y_score):
        return metrics_payload(
            y_true,
            y_pred,
            y_score,
            feature_timestamps=evaluation_frame["feature_timestamp"].to_numpy(),
        )

    return StageBResult(
        training_frame_n_rows=len(training_frame),
        training_dataset_fingerprint=training_fingerprint,
        p20_train=p20_train,
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
        metrics_candidate=evaluate_metrics(y_true, y_pred_candidate, y_score_candidate),
        metrics_persistence=evaluate_metrics(
            y_true, y_pred_persistence, y_pred_persistence.astype(float)
        ),
        metrics_majority_class=evaluate_metrics(
            y_true, y_pred_majority_class, y_pred_majority_class.astype(float)
        ),
        metrics_constant_stress=evaluate_metrics(
            y_true, y_pred_constant_stress, y_pred_constant_stress.astype(float)
        ),
        mcc_candidate=mcc_candidate,
        mcc_persistence=mcc_persistence,
        delta_mcc_point_estimate=delta_point_estimate,
        bootstrap_result=bootstrap_result,
        bootstrap_diagnostics=bootstrap_diagnostics,
        verdict=verdict,
        verdict_reasons=verdict_reasons,
        predictions_available=True,
        bootstrap_executed=not evaluation_monoclass,
        warnings_log=warnings_log,
    )


__all__ = [
    "STAGE_B_BOOTSTRAP_SEGMENT_ID",
    "STAGE_B_VERDICT_NOT_VALIDATED",
    "STAGE_B_VERDICT_VALIDATED",
    "StageBResult",
    "StageBTechnicalError",
    "build_stage_b_evaluation_frame",
    "build_stage_b_training_frame",
    "decide_stage_b_verdict",
    "refit_frozen_candidate",
    "run_stage_b",
]
