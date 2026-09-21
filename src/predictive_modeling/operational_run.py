"""Reproducible orchestrator for the frozen +1/+2/+3 operational manifest
(`config/producer-calibration-plan.frozen.v3.json`, spec `predictive-modeling`,
[design.md](../../openspec/changes/add-daily-multihorizon-predictors/design.md)).

Connects, in one place, the pieces that already existed as independent,
tested primitives: `operational_preparation` (calendar/partitions),
`operational_contract` (per-horizon identity), `calibration_manifest`
(fail-closed manifest validation) and `calibration_assessment` (the joint
bootstrap/classification engine). This module is the missing piece: it
fits a Random Forest per horizon/seed, calibrates it with sigmoid on the
manifest's calibration partition, computes raw/persistence/climatology
baselines, and feeds everything into the existing assessment engine.

Design decisions not fixed by the manifest, documented here instead of
decided silently:

- Feature variables are exactly `dataset.variables` entries with
  `role == "feature"` (never the event variable itself), with lags
  [1, 2, 3] and rolling means over [3, 7] days plus the current value —
  the same convention already used by `predictive_modeling.contract`
  ("conservar features actuales y causalidad de lags/ventanas del
  contrato existente", design.md).
- The event threshold is computed once, from `event.threshold_reference`
  (equal to `partitions.train` by manifest validation) and reused
  identically for h=1, h=2 and h=3, matching design.md's "para la
  primera evaluación, usar el mismo período de referencia observada
  para los tres umbrales, de modo que sean numéricamente iguales."
  Purga posterior sigue siendo por horizonte (`partition_labeled_horizon`).
- "target_date" (the date of the observed event, not the emission date)
  is the date used to assign observations to stability windows and to
  temporal bootstrap blocks: stability windows are declared as ranges of
  observed outcomes, and reliability diagrams are conventionally indexed
  by the date being forecast.
- The joint multiplicity bootstrap runs ONCE across every horizon, seed
  and period together (manifest `multiplicity.family_dimensions`
  includes "horizon"): a single `JointBootstrapResult` is shared by the
  three `classify_horizon` calls, one per horizon, each with its own
  `support_results`.
- Calibration uses `sklearn.calibration.CalibratedClassifierCV` wrapping
  a `FrozenEstimator` (the fitted, unmodified Random Forest) with
  `method="sigmoid"` and no internal cross-validation splitting: this is
  the current scikit-learn replacement for the removed `cv="prefit"`
  (manifest `environment.dependencies.scikit-learn` = "1.9.1").
- A horizon whose training data has a single class (or otherwise fails
  to fit) never raises out of this module: it is recorded with
  `status="training_failed"` and a machine-readable reason, and the
  other horizons continue independently (design.md, "Falla de un
  horizonte no inventa su valor ni invalida los otros").
"""

from __future__ import annotations

import hashlib
import pickle
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, FrozenEstimator
from sklearn.ensemble import RandomForestClassifier

from data_ingestion.schema import TIMESTAMP_COLUMN
from predictive_modeling.calibration_assessment import (
    BaselineComparisonResult,
    EvaluationConfig,
    HorizonAssessment,
    HorizonFinalDecision,
    JointBootstrapResult,
    ScopeFullStats,
    ScopeObservations,
    SupportCheckResult,
    TemporalBlocks,
    build_baseline_comparison_inputs,
    build_scope_full_stats,
    build_temporal_blocks,
    check_full_sample_support,
    classify_horizon,
    climatology_probability_from_training,
    compare_against_baselines,
    make_final_decision,
    run_joint_multiplicity_bootstrap,
)
from predictive_modeling.contract import feature_names, positive_probability
from predictive_modeling.feature_engineering import add_lag_features, add_rolling_features
from predictive_modeling.labeling import fit_stress_threshold
from predictive_modeling.models import predict_persistence_baseline
from predictive_modeling.operational_contract import (
    ArtifactIdentity,
    HorizonContract,
    VariableMetadata,
    validate_horizon_contract_family,
)
from predictive_modeling.operational_preparation import (
    SUPPORTED_HORIZONS,
    TARGET_DATE_COLUMN,
    TARGET_LABEL_COLUMN,
    DateRange,
    TemporalCutPlan,
    add_multihorizon_targets,
    partition_labeled_horizon,
    validate_utc_calendar,
)

DEFAULT_LAGS: tuple[int, ...] = (1, 2, 3)
DEFAULT_ROLLING_WINDOWS: tuple[int, ...] = (3, 7)
FULL_PERIOD_ID = "full"
SUPPORTED_MODEL_FAMILIES = ("random_forest",)


class OperationalRunError(ValueError):
    """A precondition of the orchestrator was violated (fail-closed)."""


# ---------------------------------------------------------------------------
# Manifest -> concrete configuration (no defaults invented here)
# ---------------------------------------------------------------------------


def resolve_feature_columns(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    """`dataset.variables` entries with `role == "feature"`, in declared order."""
    variables = manifest["dataset"]["variables"]
    columns = tuple(item["name"] for item in variables if item["role"] == "feature")
    if not columns:
        raise OperationalRunError("El manifiesto no declara ninguna variable role=feature.")
    return columns


def resolve_event_variable(manifest: Mapping[str, Any]) -> str:
    return manifest["event"]["variable"]


def resolve_cut_plan(manifest: Mapping[str, Any]) -> TemporalCutPlan:
    dataset = manifest["dataset"]
    partitions = manifest["partitions"]
    allowed = DateRange(dataset["allowed_dates"]["start"], dataset["allowed_dates"]["end"])
    return TemporalCutPlan(
        allowed_data=allowed,
        train=DateRange(partitions["train"]["start"], partitions["train"]["end"]),
        calibration=DateRange(partitions["calibration"]["start"], partitions["calibration"]["end"]),
        evaluation=DateRange(partitions["evaluation"]["start"], partitions["evaluation"]["end"]),
        inference_as_of=allowed.end,
    )


def resolve_period_ranges(
    manifest: Mapping[str, Any], cuts: TemporalCutPlan
) -> dict[str, DateRange]:
    """`{"full": partitions.evaluation, "window_1": ..., ...}`, in declaration order."""
    periods: dict[str, DateRange] = {FULL_PERIOD_ID: cuts.evaluation}
    for index, window in enumerate(manifest["stability_windows"], start=1):
        periods[f"window_{index}"] = DateRange(window["start"], window["end"])
    return periods


def resolve_frozen_threshold(
    df: pd.DataFrame, manifest: Mapping[str, Any], *, event_variable: str
) -> float:
    """Single threshold, computed once on `event.threshold_reference`
    (validated equal to `partitions.train`) and reused for every horizon.
    """
    reference = manifest["event"]["threshold_reference"]
    window = DateRange(reference["start"], reference["end"])
    frame = validate_utc_calendar(df)
    reference_rows = frame.loc[window.contains(frame[TIMESTAMP_COLUMN])]
    if reference_rows.empty:
        raise OperationalRunError("event.threshold_reference no cubre ninguna fila del dataset.")
    return fit_stress_threshold(reference_rows, event_variable, manifest["event"]["percentile"])


def check_supported_model_family(manifest: Mapping[str, Any]) -> str:
    family = manifest["model_plan"]["family"]
    if family not in SUPPORTED_MODEL_FAMILIES:
        raise OperationalRunError(
            f"model_plan.family={family!r} no soportada por este orquestador "
            f"(soportadas: {SUPPORTED_MODEL_FAMILIES}); documentar antes de extender."
        )
    return family


# ---------------------------------------------------------------------------
# Feature engineering (reuses feature_engineering.py; adds no new leakage)
# ---------------------------------------------------------------------------


def build_feature_frame(
    df: pd.DataFrame,
    feature_columns: Sequence[str],
    *,
    lags: Sequence[int] = DEFAULT_LAGS,
    windows: Sequence[int] = DEFAULT_ROLLING_WINDOWS,
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    frame = validate_utc_calendar(df)
    frame = add_lag_features(frame, list(feature_columns), list(lags))
    frame = add_rolling_features(frame, list(feature_columns), list(windows))
    names = tuple(feature_names(feature_columns, list(lags), list(windows), include_current=True))
    return frame, names


# ---------------------------------------------------------------------------
# Per-seed fit/calibration and per-scope prediction series
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeedFit:
    seed: int
    model: Any
    calibrator: Any
    training_rows: int
    calibration_rows: int
    evaluation_rows: int
    climatology_probability: float
    raw_by_target_date: Mapping[date, float]
    calibrated_by_target_date: Mapping[date, float]
    persistence_by_target_date: Mapping[date, float]
    outcome_by_target_date: Mapping[date, int]


def _target_dates_as_python_date(frame: pd.DataFrame) -> list[date]:
    return list(pd.to_datetime(frame[TARGET_DATE_COLUMN]).dt.date)


def fit_seed(
    *,
    seed: int,
    hyperparameters: Mapping[str, Any],
    feature_columns: tuple[str, ...],
    event_variable: str,
    threshold: float,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    evaluation: pd.DataFrame,
) -> SeedFit:
    X_train = train[list(feature_columns)]
    y_train = train[TARGET_LABEL_COLUMN].astype(int)
    X_calib = calibration[list(feature_columns)]
    y_calib = calibration[TARGET_LABEL_COLUMN].astype(int)
    X_eval = evaluation[list(feature_columns)]

    model = RandomForestClassifier(random_state=seed, **dict(hyperparameters))
    model.fit(X_train, y_train)

    calibrator = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
    calibrator.fit(X_calib, y_calib)

    raw_eval = positive_probability(model, X_eval)
    calibrated_eval = positive_probability(calibrator, X_eval)
    persistence_eval = predict_persistence_baseline(evaluation, event_variable, threshold)
    target_dates = _target_dates_as_python_date(evaluation)
    outcomes = evaluation[TARGET_LABEL_COLUMN].astype(int).tolist()

    def by_date(series: pd.Series) -> dict[date, float]:
        return {day: float(value) for day, value in zip(target_dates, series.tolist())}

    return SeedFit(
        seed=seed,
        model=model,
        calibrator=calibrator,
        training_rows=len(train),
        calibration_rows=len(calibration),
        evaluation_rows=len(evaluation),
        climatology_probability=climatology_probability_from_training(y_train.tolist()),
        raw_by_target_date=by_date(raw_eval),
        calibrated_by_target_date=by_date(calibrated_eval),
        persistence_by_target_date=by_date(persistence_eval),
        outcome_by_target_date=dict(zip(target_dates, outcomes)),
    )


# ---------------------------------------------------------------------------
# Assembly across horizons/seeds/periods: scopes, bootstrap, decisions
# ---------------------------------------------------------------------------


def _filter_by_period(mapping: Mapping[date, float], period: DateRange) -> dict[date, float]:
    return {day: value for day, value in mapping.items() if period.start <= day <= period.end}


def build_scope_stats_by_period(
    seed_fits_by_horizon: Mapping[int, Sequence[SeedFit]],
    periods: Mapping[str, DateRange],
    *,
    config: EvaluationConfig,
) -> tuple[dict[str, list[ScopeFullStats]], dict[tuple[int, int, str], ScopeFullStats]]:
    scope_stats_by_period: dict[str, list[ScopeFullStats]] = {
        period_id: [] for period_id in periods
    }
    index: dict[tuple[int, int, str], ScopeFullStats] = {}
    for horizon, seed_fits in seed_fits_by_horizon.items():
        for seed_fit in seed_fits:
            for period_id, period in periods.items():
                dates_in_period = sorted(_filter_by_period(seed_fit.outcome_by_target_date, period))
                pairs = tuple(
                    (
                        day,
                        seed_fit.calibrated_by_target_date[day],
                        seed_fit.outcome_by_target_date[day],
                    )
                    for day in dates_in_period
                )
                scope = ScopeObservations(
                    horizon=horizon, seed=seed_fit.seed, period_id=period_id, pairs=pairs
                )
                stats = build_scope_full_stats(
                    scope,
                    bin_count=config.bin_count,
                    include_one_in_last=config.include_one_in_last,
                    minimum_bin_count=config.minimum_bin_count,
                )
                scope_stats_by_period[period_id].append(stats)
                index[(horizon, seed_fit.seed, period_id)] = stats
    return scope_stats_by_period, index


def build_blocks_by_period(
    periods: Mapping[str, DateRange], *, block_length_days: int
) -> dict[str, TemporalBlocks]:
    return {
        period_id: build_temporal_blocks(
            period.start, period.end, block_length_days=block_length_days
        )
        for period_id, period in periods.items()
    }


def build_baseline_comparisons_for_horizon(
    horizon: int,
    seed_fits: Sequence[SeedFit],
    periods: Mapping[str, DateRange],
    *,
    clipping_epsilon: float,
) -> tuple[BaselineComparisonResult, ...]:
    results: list[BaselineComparisonResult] = []
    for seed_fit in seed_fits:
        for period_id, period in periods.items():
            dates_in_period = sorted(_filter_by_period(seed_fit.outcome_by_target_date, period))
            if not dates_in_period:
                continue
            inputs = build_baseline_comparison_inputs(
                horizon=horizon,
                seed=seed_fit.seed,
                period_id=period_id,
                outcomes=[(day, seed_fit.outcome_by_target_date[day]) for day in dates_in_period],
                calibrated_probabilities=[
                    (day, seed_fit.calibrated_by_target_date[day]) for day in dates_in_period
                ],
                raw_probabilities=[
                    (day, seed_fit.raw_by_target_date[day]) for day in dates_in_period
                ],
                persistence_probabilities=[
                    (day, seed_fit.persistence_by_target_date[day]) for day in dates_in_period
                ],
                climatology_probability=seed_fit.climatology_probability,
            )
            results.append(compare_against_baselines(inputs, clipping_epsilon=clipping_epsilon))
    return tuple(results)


def _model_bytes_sha256(estimator: Any) -> str:
    return hashlib.sha256(pickle.dumps(estimator, protocol=pickle.HIGHEST_PROTOCOL)).hexdigest()


@dataclass(frozen=True)
class HorizonRunResult:
    horizon: int
    status: str  # "evaluated" | "training_failed"
    reason: str | None
    threshold: float | None
    feature_names: tuple[str, ...]
    cuts: TemporalCutPlan | None
    seed_fits: tuple[SeedFit, ...]
    support_results: tuple[SupportCheckResult, ...]
    assessment: HorizonAssessment | None
    baseline_comparisons: tuple[BaselineComparisonResult, ...]
    final_decision: HorizonFinalDecision | None
    contract: HorizonContract | None


@dataclass(frozen=True)
class OperationalRunResult:
    dataset_sha256: str
    event_variable: str
    threshold: float
    feature_columns: tuple[str, ...]
    periods: dict[str, DateRange]
    bootstrap_result: JointBootstrapResult | None
    horizons: tuple[HorizonRunResult, ...]
    contract_family_valid: bool
    deployment_seed: int


def run_operational_manifest(
    manifest: Mapping[str, Any],
    df: pd.DataFrame,
    *,
    dataset_sha256: str,
) -> OperationalRunResult:
    """Train, calibrate and evaluate the +1/+2/+3 family declared by
    `manifest` against `df` (already loaded and hashed by the caller).

    Never reads a file, never touches `controlled_daily_v3`/`v4`, never
    accesses a holdout. Raises `OperationalRunError` for a manifest-level
    contradiction that no per-horizon status can express (e.g. an
    unsupported `model_plan.family`); a per-horizon training failure is
    recorded, never raised.
    """
    if dataset_sha256 != manifest["dataset"]["sha256"]:
        raise OperationalRunError(
            "dataset_sha256 no coincide con dataset.sha256 del manifiesto congelado."
        )
    check_supported_model_family(manifest)
    config = EvaluationConfig.from_manifest(manifest)
    feature_columns = resolve_feature_columns(manifest)
    event_variable = resolve_event_variable(manifest)
    cuts = resolve_cut_plan(manifest)
    periods = resolve_period_ranges(manifest, cuts)
    threshold = resolve_frozen_threshold(df, manifest, event_variable=event_variable)

    feature_frame, feature_names_tuple = build_feature_frame(df, feature_columns)
    labeled_by_horizon = add_multihorizon_targets(
        feature_frame,
        column=event_variable,
        thresholds={horizon: threshold for horizon in SUPPORTED_HORIZONS},
    )

    seed_fits_by_horizon: dict[int, list[SeedFit]] = {}
    training_failures: dict[int, str] = {}
    hyperparameters = manifest["model_plan"]["hyperparameters"]
    for horizon in manifest["horizons"]:
        prepared = partition_labeled_horizon(
            labeled_by_horizon[horizon],
            cuts=cuts,
            required_inference_columns=feature_names_tuple,
        )
        seed_fits: list[SeedFit] = []
        for seed in manifest["training_seeds"]:
            try:
                seed_fits.append(
                    fit_seed(
                        seed=seed,
                        hyperparameters=hyperparameters,
                        feature_columns=feature_names_tuple,
                        event_variable=event_variable,
                        threshold=threshold,
                        train=prepared.train,
                        calibration=prepared.calibration,
                        evaluation=prepared.evaluation,
                    )
                )
            except ValueError as exc:
                training_failures[horizon] = f"training_failed:{exc}"
                seed_fits = []
                break
        if seed_fits:
            seed_fits_by_horizon[horizon] = seed_fits

    scope_stats_by_period, scope_index = build_scope_stats_by_period(
        seed_fits_by_horizon, periods, config=config
    )
    blocks_by_period = build_blocks_by_period(periods, block_length_days=config.block_length_days)
    bootstrap_result = (
        run_joint_multiplicity_bootstrap(
            scope_stats_by_period,
            blocks_by_period,
            replicates=config.replicates,
            resampling_seed=config.resampling_seed,
            bin_count=config.bin_count,
            include_one_in_last=config.include_one_in_last,
            minimum_class_count=config.minimum_class_count,
            minimum_temporal_blocks=config.minimum_temporal_blocks,
            minimum_bin_count=config.minimum_bin_count,
            nominal_level=config.nominal_level,
        )
        if seed_fits_by_horizon
        else None
    )

    horizon_results: list[HorizonRunResult] = []
    contracts: list[HorizonContract] = []
    for horizon in manifest["horizons"]:
        if horizon not in seed_fits_by_horizon:
            horizon_results.append(
                HorizonRunResult(
                    horizon=horizon,
                    status="training_failed",
                    reason=training_failures.get(horizon, "training_failed:unknown"),
                    threshold=threshold,
                    feature_names=feature_names_tuple,
                    cuts=cuts,
                    seed_fits=(),
                    support_results=(),
                    assessment=None,
                    baseline_comparisons=(),
                    final_decision=None,
                    contract=None,
                )
            )
            continue

        seed_fits = seed_fits_by_horizon[horizon]
        support_results = tuple(
            check_full_sample_support(
                scope_index[(horizon, seed_fit.seed, period_id)],
                blocks_by_period[period_id],
                minimum_class_count=config.minimum_class_count,
                minimum_temporal_blocks=config.minimum_temporal_blocks,
                coverage_minimum=config.coverage_minimum,
            )
            for seed_fit in seed_fits
            for period_id in periods
        )
        assert bootstrap_result is not None
        assessment = classify_horizon(
            horizon,
            support_results=support_results,
            bootstrap_result=bootstrap_result,
            epsilon_ece=config.epsilon_ece,
            epsilon_bin=config.epsilon_bin,
        )
        baseline_comparisons = build_baseline_comparisons_for_horizon(
            horizon, seed_fits, periods, clipping_epsilon=config.log_loss_clipping_epsilon
        )
        required_scope_keys = tuple(
            (seed_fit.seed, period_id) for seed_fit in seed_fits for period_id in periods
        )
        final_decision = make_final_decision(
            horizon, assessment, baseline_comparisons, required_scope_keys=required_scope_keys
        )

        deployment_seed = manifest["deployment_seed"]
        deployment_fit = next(fit for fit in seed_fits if fit.seed == deployment_seed)
        model_identity = ArtifactIdentity(
            version=f"operational_v3_h{horizon}_seed{deployment_seed}_model",
            sha256=_model_bytes_sha256(deployment_fit.model),
            horizon_days=horizon,
        )
        calibrator_identity = ArtifactIdentity(
            version=f"operational_v3_h{horizon}_seed{deployment_seed}_calibrator",
            sha256=_model_bytes_sha256(deployment_fit.calibrator),
            horizon_days=horizon,
        )
        contract = HorizonContract(
            horizon_days=horizon,
            sensor_id=manifest["dataset"]["sensor_id"],
            data_snapshot_sha256=dataset_sha256,
            imputation="none_grid_gaps_preserved",
            variables=tuple(
                VariableMetadata(item["name"], item["unit"])
                for item in manifest["dataset"]["variables"]
            ),
            event_variable=event_variable,
            event_threshold=threshold,
            event_unit=manifest["event"]["unit"],
            temporal_cuts=cuts,
            artifact_state="trained_bundle",
            model_identity=model_identity,
            calibrator_identity=calibrator_identity,
            trained_through=cuts.train.end,
            calibrated_through=cuts.calibration.end,
        )
        contracts.append(contract)

        horizon_results.append(
            HorizonRunResult(
                horizon=horizon,
                status="evaluated",
                reason=None,
                threshold=threshold,
                feature_names=feature_names_tuple,
                cuts=cuts,
                seed_fits=tuple(seed_fits),
                support_results=support_results,
                assessment=assessment,
                baseline_comparisons=baseline_comparisons,
                final_decision=final_decision,
                contract=contract,
            )
        )

    contract_family_valid = False
    if len(contracts) == len(SUPPORTED_HORIZONS):
        validate_horizon_contract_family(tuple(contracts))
        contract_family_valid = True

    return OperationalRunResult(
        dataset_sha256=dataset_sha256,
        event_variable=event_variable,
        threshold=threshold,
        feature_columns=feature_columns,
        periods=dict(periods),
        bootstrap_result=bootstrap_result,
        horizons=tuple(horizon_results),
        contract_family_valid=contract_family_valid,
        deployment_seed=manifest["deployment_seed"],
    )
