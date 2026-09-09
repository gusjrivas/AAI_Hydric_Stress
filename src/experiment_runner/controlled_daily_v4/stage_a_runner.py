"""Runner de la Etapa A completa: nested CV, OOF, selección y congelamiento.

Orquesta, para una única profundidad, las secciones 6 a 9 del protocolo.
Nunca procesa ni requiere datos de 2023-2025 — únicamente recibe la serie
diaria continua completa y filtra internamente por `STAGE_A_BOUNDS`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.config import (
    DECISION_THRESHOLD,
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    FAMILY_SOFT_VOTING,
    STAGE_A_BOUNDS,
    ProtocolConfig,
)
from experiment_runner.controlled_daily_v4.features import (
    FEATURE_COLUMNS,
    build_feature_frame,
    build_target,
    compute_p20_threshold,
    restrict_to_stage_window,
    select_eligible_rows,
)
from experiment_runner.controlled_daily_v4.freezing import (
    FrozenConfig,
    fit_final_estimator,
    freeze_family,
)
from experiment_runner.controlled_daily_v4.metrics import mcc_strict
from experiment_runner.controlled_daily_v4.models import (
    ModelConfig,
    ScaledLogisticRegression,
    SoftVotingClassifier,
    SoftVotingSpec,
    effective_logistic_regularization,
    fit_candidate,
    fit_estimator,
    iter_hist_gradient_boosting_configs,
    iter_logistic_regression_configs,
    iter_random_forest_configs,
)
from experiment_runner.controlled_daily_v4.selection import (
    CandidateOOF,
    SelectionResult,
    select_family,
)
from experiment_runner.controlled_daily_v4.splits import (
    Fold,
    generate_inner_folds,
    generate_outer_folds,
)
from experiment_runner.controlled_daily_v4.tuning import select_best_config

SINGLE_MODEL_FAMILIES = (
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    FAMILY_HIST_GRADIENT_BOOSTING,
)


def build_family_config_map(protocol_config: ProtocolConfig) -> dict[str, list[ModelConfig]]:
    return {
        FAMILY_LOGISTIC_REGRESSION: iter_logistic_regression_configs(
            protocol_config.logistic_regression_grid
        ),
        FAMILY_RANDOM_FOREST: iter_random_forest_configs(protocol_config.random_forest_grid),
        FAMILY_HIST_GRADIENT_BOOSTING: iter_hist_gradient_boosting_configs(
            protocol_config.hist_gradient_boosting_grid
        ),
    }


@dataclass
class OuterFoldFamilyResult:
    outer_fold_index: int
    family: str
    inner_best_config: ModelConfig
    inner_median_mcc: float
    inner_fold_mcc: list[float]
    p20_train: float
    y_true: np.ndarray
    y_pred: np.ndarray
    y_score: np.ndarray
    feature_timestamps: np.ndarray
    # Solo para Soft Voting: las configuraciones base con las que se compuso
    # este outer fold y el modo de balanceo independiente de cada una.
    soft_voting_base_config_ids: dict[str, str] = field(default_factory=dict)
    soft_voting_base_weighting_modes: dict[str, str] = field(default_factory=dict)


def build_eligible_frame(daily_series: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    """Recorta primero a la ventana autorizada de la Etapa A y solo después
    construye features y target: ninguna observación posterior a
    `2022-12-31` llega al constructor (protocolo, sección 5)."""
    restricted = restrict_to_stage_window(daily_series, STAGE_A_BOUNDS)
    frame = build_feature_frame(restricted, depth_column)
    return select_eligible_rows(frame, STAGE_A_BOUNDS)


def _run_single_family_outer_fold(
    family: str,
    configs: list[ModelConfig],
    outer_fold: Fold,
    inner_n_splits: int,
    gap: int,
    p20_train: float,
    y_train: np.ndarray,
    y_val: np.ndarray,
) -> OuterFoldFamilyResult:
    inner_folds = generate_inner_folds(outer_fold.train, n_splits=inner_n_splits, gap=gap)
    best_config, median, fold_scores = select_best_config(configs, inner_folds)

    X_train = outer_fold.train[list(FEATURE_COLUMNS)].to_numpy()
    X_val = outer_fold.validation[list(FEATURE_COLUMNS)].to_numpy()
    estimator = fit_estimator(family, best_config.params, X_train, y_train)
    y_score = estimator.predict_proba(X_val)[:, 1]
    y_pred = (y_score >= DECISION_THRESHOLD).astype(int)

    return OuterFoldFamilyResult(
        outer_fold_index=outer_fold.index,
        family=family,
        inner_best_config=best_config,
        inner_median_mcc=median,
        inner_fold_mcc=fold_scores,
        p20_train=p20_train,
        y_true=y_val,
        y_pred=y_pred,
        y_score=y_score,
        feature_timestamps=outer_fold.validation["feature_timestamp"].to_numpy(),
    )


def _run_soft_voting_outer_fold(
    outer_fold: Fold,
    base_results: dict[str, OuterFoldFamilyResult],
    p20_train: float,
    y_train: np.ndarray,
    y_val: np.ndarray,
) -> OuterFoldFamilyResult:
    base_configs = {family: r.inner_best_config for family, r in base_results.items()}
    X_train = outer_fold.train[list(FEATURE_COLUMNS)].to_numpy()
    X_val = outer_fold.validation[list(FEATURE_COLUMNS)].to_numpy()
    estimator = fit_candidate(SoftVotingSpec(base_configs), X_train, y_train)
    y_score = estimator.predict_proba(X_val)[:, 1]
    y_pred = (y_score >= DECISION_THRESHOLD).astype(int)

    return OuterFoldFamilyResult(
        outer_fold_index=outer_fold.index,
        family=FAMILY_SOFT_VOTING,
        # El Soft Voting no tiene grilla propia (protocolo, sección 7.5): se
        # compone con las configuraciones ya seleccionadas de LR/RF/HGB.
        inner_best_config=ModelConfig(FAMILY_SOFT_VOTING, {}),
        inner_median_mcc=float("nan"),
        inner_fold_mcc=[],
        p20_train=p20_train,
        y_true=y_val,
        y_pred=y_pred,
        y_score=y_score,
        feature_timestamps=outer_fold.validation["feature_timestamp"].to_numpy(),
        soft_voting_base_config_ids=estimator.base_config_ids(),
        soft_voting_base_weighting_modes=estimator.base_weighting_modes(),
    )


@dataclass
class StageAResults:
    depth_column: str
    outer_folds: list[Fold]
    per_family_outer_results: dict[str, list[OuterFoldFamilyResult]] = field(default_factory=dict)
    oof_by_family: dict[str, CandidateOOF] = field(default_factory=dict)
    selection: SelectionResult | None = None
    frozen_single_family: FrozenConfig | None = None
    frozen_soft_voting_bases: dict[str, FrozenConfig] | None = None
    final_estimator: object = None
    final_p20_train: float | None = None
    final_estimator_details: dict[str, dict] | None = None


def _concatenate_oof(
    family: str, results: list[OuterFoldFamilyResult], depth_column: str
) -> CandidateOOF:
    y_true = np.concatenate([r.y_true for r in results])
    y_pred = np.concatenate([r.y_pred for r in results])
    y_score = np.concatenate([r.y_score for r in results])
    timestamps = np.concatenate([r.feature_timestamps for r in results])
    segment_ids = np.concatenate(
        [np.full(len(r.y_true), f"outer_fold_{r.outer_fold_index}") for r in results]
    )
    frame = pd.DataFrame({"feature_timestamp": timestamps, "segment_id": segment_ids}).sort_values(
        "feature_timestamp"
    )
    order = frame.index.to_numpy()
    frame = frame.reset_index(drop=True)
    return CandidateOOF(
        family=family,
        y_true=y_true[order],
        y_pred=y_pred[order],
        y_score=y_score[order],
        frame_with_segment_id=frame,
        # Diagnóstico por outer fold (protocolo, sección 8.4). No interviene
        # en la decisión: el MCC global se recalcula desde el OOF completo.
        per_fold_mcc=[mcc_strict(r.y_true, r.y_pred) for r in results],
    )


def run_stage_a(
    daily_series: pd.DataFrame,
    depth_column: str,
    protocol_config: ProtocolConfig | None = None,
) -> StageAResults:
    """Ejecuta la Etapa A completa (nested CV, OOF, selección, congelamiento)
    para una única profundidad. `daily_series` debe ser la serie diaria
    continua completa (sin filtrar); el filtrado por etapa ocurre aquí."""
    protocol_config = protocol_config or ProtocolConfig()

    eligible = build_eligible_frame(daily_series, depth_column)
    outer_folds = generate_outer_folds(
        eligible, n_splits=protocol_config.outer_n_splits, gap=protocol_config.gap
    )
    family_configs = build_family_config_map(protocol_config)

    per_family_outer_results: dict[str, list[OuterFoldFamilyResult]] = {
        f: [] for f in (*SINGLE_MODEL_FAMILIES, FAMILY_SOFT_VOTING)
    }

    for outer_fold in outer_folds:
        p20_train = compute_p20_threshold(outer_fold.train["future_soil_moisture"])
        y_train = build_target(outer_fold.train["future_soil_moisture"], p20_train).to_numpy()
        y_val = build_target(outer_fold.validation["future_soil_moisture"], p20_train).to_numpy()

        base_results: dict[str, OuterFoldFamilyResult] = {}
        for family in SINGLE_MODEL_FAMILIES:
            result = _run_single_family_outer_fold(
                family,
                family_configs[family],
                outer_fold,
                protocol_config.inner_n_splits,
                protocol_config.gap,
                p20_train,
                y_train,
                y_val,
            )
            base_results[family] = result
            per_family_outer_results[family].append(result)

        soft_voting_result = _run_soft_voting_outer_fold(
            outer_fold, base_results, p20_train, y_train, y_val
        )
        per_family_outer_results[FAMILY_SOFT_VOTING].append(soft_voting_result)

    oof_by_family = {
        family: _concatenate_oof(family, results, depth_column)
        for family, results in per_family_outer_results.items()
    }

    selection = select_family(
        oof_by_family,
        delta=protocol_config.practical_margin_delta_mcc,
        n_replicas=protocol_config.bootstrap_replicas,
        seed=protocol_config.bootstrap_seed,
    )

    results = StageAResults(
        depth_column=depth_column,
        outer_folds=outer_folds,
        per_family_outer_results=per_family_outer_results,
        oof_by_family=oof_by_family,
        selection=selection,
    )

    if selection.selected_family is None:
        return results

    if selection.selected_family == FAMILY_SOFT_VOTING:
        frozen_bases = {
            family: freeze_family(
                family,
                family_configs[family],
                eligible,
                protocol_config.outer_n_splits,
                protocol_config.gap,
            )
            for family in SINGLE_MODEL_FAMILIES
        }
        results.frozen_soft_voting_bases = frozen_bases
        p20_train = compute_p20_threshold(eligible["future_soil_moisture"])
        y = build_target(eligible["future_soil_moisture"], p20_train).to_numpy()
        X = eligible[list(FEATURE_COLUMNS)].to_numpy()
        base_configs = {family: fc.config for family, fc in frozen_bases.items()}
        results.final_estimator = fit_candidate(SoftVotingSpec(base_configs), X, y)
        results.final_p20_train = p20_train
    else:
        family = selection.selected_family
        frozen = freeze_family(
            family,
            family_configs[family],
            eligible,
            protocol_config.outer_n_splits,
            protocol_config.gap,
        )
        results.frozen_single_family = frozen
        estimator, p20_train = fit_final_estimator(frozen, eligible)
        results.final_estimator = estimator
        results.final_p20_train = p20_train

    results.final_estimator_details = _describe_final_estimator(
        results.final_estimator, selection.selected_family
    )
    return results


def _describe_estimator(estimator: object) -> dict:
    """Descripción verificada por API de un estimador ya ajustado.

    Para la Logistic Regression incluye la regularización *efectiva* leída del
    estimador, no la declarada en la grilla: en scikit-learn 1.9.0 `penalty`
    está deprecado y el valor real lo fija `l1_ratio` (protocolo, sección
    7.2). Para el resto registra los parámetros efectivos, lo que deja
    constancia de que `class_weight` permanece en `None` (sección 7.1)."""
    if isinstance(estimator, ScaledLogisticRegression):
        return {
            "estimator_class": type(estimator).__name__,
            **effective_logistic_regularization(estimator),
        }
    return {
        "estimator_class": type(estimator).__name__,
        "effective_params": dict(estimator.get_params()),
    }


def _describe_final_estimator(estimator: object, selected_family: str | None) -> dict[str, dict]:
    """Detalles del estimador congelado, por familia. Para Soft Voting
    describe cada una de sus tres bases por separado."""
    if estimator is None or selected_family is None:
        return {}
    if isinstance(estimator, SoftVotingClassifier):
        return {
            family: _describe_estimator(base.estimator_)
            for family, base in estimator.named_estimators_.items()
        }
    return {selected_family: _describe_estimator(estimator)}
