"""Read-only retrospective evaluation of the fixed Pergamino demo bundles.

This module deliberately contains no training or recalibration path. Mixed raw
files are restricted by streaming structural dates before the existing pandas
loaders see them. Results are exploratory and non-independent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shutil
import sys
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from data_ingestion.schema import TIMESTAMP_COLUMN
from experiment_runner.controlled_daily_v4.ingestion import (
    aggregate_era5_daily,
    build_daily_joined_series,
    load_era5_hourly_raw,
    load_nasa_power_daily_raw,
    replace_missing_sentinel,
)
from experiment_runner.pergamino_ensemble_demo_runner import (
    CURRENT_ONLY_COLUMNS,
    EVENT_VARIABLE,
    RAW_TO_CANONICAL,
    _invalidate_incomplete_soil_moisture_days,
)
from predictive_modeling.ensemble_bundle import (
    compute_ensemble_identity,
    load_ensemble_bundle,
    predict_ensemble_bundle,
)
from predictive_modeling.operational_inference import (
    BundleUnavailable,
    predict_operational_bundle,
)
from predictive_modeling.operational_preparation import validate_utc_calendar
from predictive_modeling.operational_run_artifacts import capture_code_identity, capture_environment

LABEL = (
    "Evaluacion retrospectiva exploratoria, no independiente: "
    "2023 ya fue utilizado en analisis anteriores del proyecto"
)
SENSOR_ID = "pergamino-ensemble-demo"
FAMILIES = ("hist_gradient_boosting_classifier", "logistic_regression", "random_forest")
HORIZONS = (1, 2, 3)
FILTER_START = date(2022, 12, 26)
FILTER_END = date(2023, 12, 31)
EVALUATION_START = date(2023, 1, 1)
EVALUATION_END = date(2023, 12, 31)
BLOCK_LENGTH = 30
BOOTSTRAP_SEED = 20250109
BOOTSTRAP_REPLICATES = 5000
RELIABILITY_EDGES = tuple(i / 10 for i in range(11))
PROTOCOL_RELATIVE = Path("docs/research/ensemble-retrospective-evaluation-protocol.md")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class EvaluationError(RuntimeError):
    """Fail-closed precondition or evaluation error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_clean(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    return value


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(_json_clean(payload), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )


def _prepare_empty_directory(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise EvaluationError(f"El directorio debe ser nuevo o vacio: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _parse_iso_date_prefix(raw: bytes) -> date:
    field = raw.split(b",", 1)[0].strip().strip(b'"')
    return date.fromisoformat(field[:10].decode("ascii"))


def _parse_nasa_year_doy(raw: bytes) -> date:
    first, second, *_ = raw.split(b",", 2)
    return date(int(first.strip()), 1, 1) + timedelta(days=int(second.strip()) - 1)


def stream_filter_era5(source: Path, destination: Path) -> dict[str, Any]:
    """Copy ERA5 rows in the permitted window, parsing only the time field."""
    kept = excluded_before = excluded_after = 0
    bytes_read = 0
    header_seen = False
    with source.open("rb") as incoming, destination.open("wb") as outgoing:
        for raw in incoming:
            bytes_read += len(raw)
            if not header_seen:
                outgoing.write(raw)
                if raw.lstrip().lower().startswith(b"time,"):
                    header_seen = True
                continue
            if not raw.strip():
                continue
            day = _parse_iso_date_prefix(raw)
            if FILTER_START <= day <= FILTER_END:
                outgoing.write(raw)
                kept += 1
            elif day < FILTER_START:
                excluded_before += 1
            else:
                excluded_after += 1
    if not header_seen or kept == 0:
        raise EvaluationError("ERA5 filtrado sin encabezado o sin filas permitidas")
    return {
        "source_sha256": sha256_file(source),
        "restricted_sha256": sha256_file(destination),
        "bytes_read_sequentially": bytes_read,
        "rows_kept": kept,
        "rows_excluded_before": excluded_before,
        "rows_excluded_after_2023": excluded_after,
        "future_bytes_traversed_values_not_parsed_or_aggregated": excluded_after > 0,
    }


def stream_filter_nasa(source: Path, destination: Path) -> dict[str, Any]:
    """Copy NASA rows in the permitted window, parsing only YEAR and DOY."""
    kept = excluded_before = excluded_after = 0
    bytes_read = 0
    end_header = False
    csv_header = False
    with source.open("rb") as incoming, destination.open("wb") as outgoing:
        for raw in incoming:
            bytes_read += len(raw)
            if not end_header:
                outgoing.write(raw)
                if b"-END HEADER-" in raw:
                    end_header = True
                continue
            if not csv_header:
                outgoing.write(raw)
                csv_header = True
                continue
            if not raw.strip():
                continue
            day = _parse_nasa_year_doy(raw)
            if FILTER_START <= day <= FILTER_END:
                outgoing.write(raw)
                kept += 1
            elif day < FILTER_START:
                excluded_before += 1
            else:
                excluded_after += 1
    if not end_header or not csv_header or kept == 0:
        raise EvaluationError("NASA POWER filtrado sin encabezado o sin filas permitidas")
    return {
        "source_sha256": sha256_file(source),
        "restricted_sha256": sha256_file(destination),
        "bytes_read_sequentially": bytes_read,
        "rows_kept": kept,
        "rows_excluded_before": excluded_before,
        "rows_excluded_after_2023": excluded_after,
        "future_bytes_traversed_values_not_parsed_or_aggregated": excluded_after > 0,
    }


def build_restricted_daily_frame(era5: Path, nasa: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reuse production ingestion after the files have already been restricted."""
    _, era5_raw = load_era5_hourly_raw(era5)
    era5_daily = _invalidate_incomplete_soil_moisture_days(aggregate_era5_daily(era5_raw))
    _, nasa_raw = load_nasa_power_daily_raw(nasa)
    nasa_raw = replace_missing_sentinel(nasa_raw)
    joined = build_daily_joined_series(era5_daily, nasa_raw)
    frame = joined.reset_index().rename(
        columns={"soil_moisture_0_to_7cm": EVENT_VARIABLE, **RAW_TO_CANONICAL}
    )
    frame = frame[["date", EVENT_VARIABLE, *CURRENT_ONLY_COLUMNS]].rename(
        columns={"date": TIMESTAMP_COLUMN}
    )
    frame = validate_utc_calendar(frame)
    if (
        frame[TIMESTAMP_COLUMN].dt.date.min() < FILTER_START
        or frame[TIMESTAMP_COLUMN].dt.date.max() > FILTER_END
    ):
        raise EvaluationError("La ingesta restringida produjo fechas fuera del rango permitido")
    details = {
        "daily_rows": len(frame),
        "first_day": frame[TIMESTAMP_COLUMN].min(),
        "last_day": frame[TIMESTAMP_COLUMN].max(),
        "missing_by_column": {
            column: int(frame[column].isna().sum())
            for column in (EVENT_VARIABLE, *CURRENT_ONLY_COLUMNS)
        },
        "duplicate_timestamps": int(frame[TIMESTAMP_COLUMN].duplicated().sum()),
        "daily_frame_sha256": hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest(),
    }
    return frame, details


def load_verified_bundles(bundle_root: Path) -> tuple[dict[int, Any], dict[str, Any]]:
    run_path = bundle_root / "run_manifest.json"
    run_manifest = json.loads(run_path.read_text(encoding="utf-8"))
    if run_manifest.get("status") != "completado":
        raise EvaluationError("run_manifest no esta en estado completado")
    expected_partitions = {
        "train": {"start": "2015-01-01", "end": "2021-12-31"},
        "calibration": {"start": "2022-01-01", "end": "2022-12-31"},
        "evaluation": {"start": "2023-01-01", "end": "2023-12-31"},
        "allowed_data": {"start": "2015-01-01", "end": "2023-12-31"},
        "first_admissible_inference_date": "2022-12-31",
    }
    config = run_manifest.get("effective_config", {})
    if (
        run_manifest.get("sensor_id") != SENSOR_ID
        or run_manifest.get("horizons_requested") != list(HORIZONS)
        or run_manifest.get("partitions") != expected_partitions
        or config.get("decision_threshold") != 0.5
        or config.get("event_variable") != EVENT_VARIABLE
        or config.get("feature_columns") != [EVENT_VARIABLE, *CURRENT_ONLY_COLUMNS]
        or config.get("lags") != [1, 2, 3]
        or config.get("rolling_windows") != [3, 7]
    ):
        raise EvaluationError("run_manifest incompatible con el protocolo congelado")
    expected_input_hashes = run_manifest.get("input_hashes")
    if not isinstance(expected_input_hashes, dict) or set(expected_input_hashes) != {
        "era5_csv",
        "nasa_power_csv",
    }:
        raise EvaluationError("run_manifest sin hashes completos de entradas")
    physical_threshold = run_manifest.get("physical_threshold")
    if not isinstance(physical_threshold, (int, float)) or not math.isfinite(physical_threshold):
        raise EvaluationError("run_manifest sin P20 fisico finito")
    before = tree_hashes(bundle_root)
    ensembles: dict[int, Any] = {}
    identities: dict[str, Any] = {}
    for horizon in HORIZONS:
        ensemble = load_ensemble_bundle(bundle_root, sensor_id=SENSOR_ID, horizon=horizon)
        ensembles[horizon] = ensemble
        family_meta = {}
        for family, component in sorted(ensemble.components.items()):
            if family not in FAMILIES:
                raise EvaluationError(f"Familia no preespecificada: {family}")
            metadata = component.metadata
            contract = metadata["contract"]
            if contract["event"]["threshold"] != physical_threshold:
                raise EvaluationError("P20 del contrato no coincide con run_manifest")
            family_meta[family] = {
                "files": metadata["files"],
                "feature_columns": metadata["feature_columns"],
                "feature_names": metadata["feature_names"],
                "lags": metadata["lags"],
                "rolling_windows": metadata["rolling_windows"],
                "decision_threshold": metadata["decision_threshold"],
                "event": contract["event"],
                "trained_through": contract["trained_through"],
                "calibrated_through": contract["calibrated_through"],
                "data_snapshot_sha256": contract["data_snapshot_sha256"],
                "contract_version": contract["contract_version"],
            }
        identities[str(horizon)] = {
            "ensemble_identity_sha256": compute_ensemble_identity(
                ensemble.manifest, ensemble.components
            ),
            "manifest": ensemble.manifest,
            "components": family_meta,
        }
    return ensembles, {
        "run_manifest_sha256": sha256_file(run_path),
        "run_status": run_manifest["status"],
        "expected_input_hashes": expected_input_hashes,
        "physical_threshold_p20": physical_threshold,
        "partitions": expected_partitions,
        "tree_before": before,
        "identities": identities,
    }


def _defined(value: float | None, reason: str | None = None) -> dict[str, Any]:
    return {
        "status": "defined" if value is not None else "undefined",
        "value": value,
        "reason": None if value is not None else reason,
    }


def mcc_value(tn: int, fp: int, fn: int, tp: int) -> float | None:
    denominator = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    if denominator == 0:
        return None
    return (tp * tn - fp * fn) / math.sqrt(denominator)


def confusion(y: np.ndarray, prediction: np.ndarray) -> tuple[int, int, int, int]:
    tn = int(np.sum((y == 0) & (prediction == 0)))
    fp = int(np.sum((y == 0) & (prediction == 1)))
    fn = int(np.sum((y == 1) & (prediction == 0)))
    tp = int(np.sum((y == 1) & (prediction == 1)))
    return tn, fp, fn, tp


def reliability_bins(y: np.ndarray, scores: np.ndarray) -> list[dict[str, Any]]:
    bins = []
    for index in range(10):
        lower, upper = RELIABILITY_EDGES[index], RELIABILITY_EDGES[index + 1]
        mask = (scores >= lower) & ((scores < upper) if index < 9 else (scores <= upper))
        count = int(mask.sum())
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "right_inclusive": index == 9,
                "n": count,
                "positives": int(y[mask].sum()) if count else 0,
                "mean_score": float(scores[mask].mean()) if count else None,
                "observed_fraction": float(y[mask].mean()) if count else None,
            }
        )
    return bins


def method_metrics(
    y: Iterable[int], decisions: Iterable[int], scores: Iterable[float] | None = None
) -> dict[str, Any]:
    y_array = np.asarray(list(y), dtype=int)
    pred = np.asarray(list(decisions), dtype=int)
    if len(y_array) != len(pred):
        raise EvaluationError("Metricas con longitudes incompatibles")
    n = len(y_array)
    if n == 0:
        return {"n": 0, "status": "undefined", "reason": "no_cases"}
    tn, fp, fn, tp = confusion(y_array, pred)
    precision_den = tp + fp
    recall_den = tp + fn
    f1_den = 2 * tp + fp + fn
    result: dict[str, Any] = {
        "n": n,
        "positives": int(y_array.sum()),
        "negatives": int(n - y_array.sum()),
        "prevalence": float(y_array.mean()),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "precision": _defined(
            tp / precision_den if precision_den else None,
            "no_predicted_positives" if not precision_den else None,
        ),
        "recall": _defined(
            tp / recall_den if recall_den else None,
            "no_observed_positives" if not recall_den else None,
        ),
        "f1": _defined(
            2 * tp / f1_den if f1_den else None,
            "no_positive_prediction_or_observation" if not f1_den else None,
        ),
        "mcc": _defined(mcc_value(tn, fp, fn, tp), "zero_mcc_denominator"),
        "false_alerts": fp,
        "missed_positive_days": fn,
    }
    if scores is not None:
        score_array = np.asarray(list(scores), dtype=float)
        if len(score_array) != n or not np.isfinite(score_array).all():
            raise EvaluationError("Scores invalidos para metricas probabilisticas")
        two_classes = 0 < int(y_array.sum()) < n
        result["average_precision"] = _defined(
            float(average_precision_score(y_array, score_array)) if two_classes else None,
            None if two_classes else "requires_both_classes",
        )
        result["brier"] = _defined(float(np.mean((score_array - y_array) ** 2)))
        result["reliability_bins"] = reliability_bins(y_array, score_array)
    return result


def _continuous_segments(days: list[date]) -> list[list[int]]:
    if not days:
        return []
    segments: list[list[int]] = [[0]]
    for index in range(1, len(days)):
        if days[index] == days[index - 1] + timedelta(days=1):
            segments[-1].append(index)
        else:
            segments.append([index])
    return segments


def paired_block_bootstrap(
    rows: list[dict[str, Any]], comparisons: Mapping[str, tuple[str, str]]
) -> dict[str, Any]:
    days = [date.fromisoformat(row["emission_date"]) for row in rows]
    candidates: list[list[int]] = []
    for segment in _continuous_segments(days):
        for offset in range(0, len(segment) - BLOCK_LENGTH + 1):
            candidates.append(segment[offset : offset + BLOCK_LENGTH])
    result: dict[str, Any] = {
        "method": "paired_non_circular_moving_block_bootstrap",
        "block_length_days": BLOCK_LENGTH,
        "seed": BOOTSTRAP_SEED,
        "replicates_requested": BOOTSTRAP_REPLICATES,
        "candidate_blocks": len(candidates),
        "comparisons": {},
    }
    if not candidates:
        result["status"] = "undefined"
        result["reason"] = "no_continuous_30_day_block"
        return result
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    y = np.asarray([row["target"] for row in rows], dtype=int)
    predictions = {
        method: np.asarray([row[f"{method}_alert"] for row in rows], dtype=int)
        for pair in comparisons.values()
        for method in pair
    }
    deltas = {name: [] for name in comparisons}
    undefined = Counter()
    blocks_needed = math.ceil(len(rows) / BLOCK_LENGTH)
    for _ in range(BOOTSTRAP_REPLICATES):
        selection: list[int] = []
        for block_index in rng.integers(0, len(candidates), size=blocks_needed):
            selection.extend(candidates[int(block_index)])
        indices = np.asarray(selection[: len(rows)], dtype=int)
        sample_y = y[indices]
        for name, (left, right) in comparisons.items():
            left_cm = confusion(sample_y, predictions[left][indices])
            right_cm = confusion(sample_y, predictions[right][indices])
            left_mcc = mcc_value(*left_cm)
            right_mcc = mcc_value(*right_cm)
            if left_mcc is None or right_mcc is None:
                undefined[name] += 1
            else:
                deltas[name].append(left_mcc - right_mcc)
    result["status"] = "defined"
    for name, values in deltas.items():
        result["comparisons"][name] = {
            "status": "defined" if values else "undefined",
            "replicates_defined": len(values),
            "replicates_discarded_undefined": int(undefined[name]),
            "delta_mcc_ci95": (
                [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]
                if values
                else None
            ),
        }
    return result


def observed_episodes(frame: pd.DataFrame, threshold: float) -> list[dict[str, Any]]:
    by_day = {
        timestamp.date(): (float(value) if pd.notna(value) and np.isfinite(value) else None)
        for timestamp, value in zip(frame[TIMESTAMP_COLUMN], frame[EVENT_VARIABLE])
        if EVALUATION_START <= timestamp.date() <= EVALUATION_END
    }
    episodes: list[dict[str, Any]] = []
    active: list[date] = []
    for day in (EVALUATION_START + timedelta(days=i) for i in range(365)):
        value = by_day.get(day)
        dry = value is not None and value < threshold
        if dry:
            active.append(day)
        elif active:
            episodes.append(_finish_episode(active, by_day, threshold))
            active = []
    if active:
        episodes.append(_finish_episode(active, by_day, threshold))
    return episodes


def _finish_episode(
    days: list[date], by_day: Mapping[date, float | None], threshold: float
) -> dict[str, Any]:
    previous = days[0] - timedelta(days=1)
    following = days[-1] + timedelta(days=1)
    previous_value = by_day.get(previous)
    following_value = by_day.get(following)
    start_determinable = previous_value is not None and previous_value >= threshold
    return {
        "start": days[0].isoformat(),
        "end": days[-1].isoformat(),
        "duration_days": len(days),
        "start_determinable": start_determinable,
        "left_censored": not start_determinable,
        "right_censored": following_value is None,
    }


def episode_assessment(
    episodes: list[dict[str, Any]], rows: list[dict[str, Any]], horizon: int, methods: Iterable[str]
) -> dict[str, Any]:
    by_emission = {row["emission_date"]: row for row in rows}
    evaluable = []
    for episode in episodes:
        start = date.fromisoformat(episode["start"])
        emission = start - timedelta(days=horizon)
        row = by_emission.get(emission.isoformat())
        if episode["start_determinable"] and EVALUATION_START <= emission <= EVALUATION_END and row:
            evaluable.append((episode, row))
    per_method = {}
    for method in methods:
        detected = sum(int(row[f"{method}_alert"]) for _, row in evaluable)
        per_method[method] = {
            "evaluable_episodes": len(evaluable),
            "detected_episodes": detected,
            "missed_episodes": len(evaluable) - detected,
            "recall": _defined(
                detected / len(evaluable) if evaluable else None,
                "no_evaluable_episodes" if not evaluable else None,
            ),
        }
    return {
        "definition": "consecutive_valid_days_below_p20; gaps_break_and_censor",
        "episodes_total": len(episodes),
        "starts_determinable": sum(int(ep["start_determinable"]) for ep in episodes),
        "left_censored": sum(int(ep["left_censored"]) for ep in episodes),
        "right_censored": sum(int(ep["right_censored"]) for ep in episodes),
        "evaluable_for_horizon": len(evaluable),
        "methods": per_method,
        "confidence_intervals": None,
        "limitation": "descriptive_only_no_episode_bootstrap",
    }


def evaluate_horizon(
    frame: pd.DataFrame, ensemble: Any, horizon: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reference = ensemble.components[FAMILIES[0]].metadata
    threshold = float(reference["contract"]["event"]["threshold"])
    decision_threshold = float(reference["decision_threshold"])
    if decision_threshold != 0.5:
        raise EvaluationError("El umbral contractual no es 0.5")
    units = {item["name"]: item["unit"] for item in reference["contract"]["variables"]}
    indexed = frame.set_index(frame[TIMESTAMP_COLUMN].dt.date)
    candidate_count = 0
    exclusions = Counter()
    availability = {family: Counter() for family in FAMILIES}
    all_rows: list[dict[str, Any]] = []
    end = EVALUATION_END - timedelta(days=horizon)
    day = EVALUATION_START
    while day <= end:
        candidate_count += 1
        target_day = day + timedelta(days=horizon)
        row: dict[str, Any] = {
            "horizon": horizon,
            "emission_date": day.isoformat(),
            "target_date": target_day.isoformat(),
        }
        current = indexed.at[day, EVENT_VARIABLE] if day in indexed.index else np.nan
        target = indexed.at[target_day, EVENT_VARIABLE] if target_day in indexed.index else np.nan
        current_valid = np.isscalar(current) and pd.notna(current) and np.isfinite(float(current))
        target_valid = np.isscalar(target) and pd.notna(target) and np.isfinite(float(target))
        row["current_observed"] = float(current) if current_valid else None
        row["target_observed"] = float(target) if target_valid else None
        row["target"] = int(float(target) < threshold) if target_valid else None
        row["persistence_alert"] = int(float(current) < threshold) if current_valid else None
        component_results: dict[str, Any] = {}
        for family in FAMILIES:
            try:
                result = predict_operational_bundle(
                    ensemble.components[family],
                    frame,
                    sensor_id=SENSOR_ID,
                    units=units,
                    as_of_date=day,
                )
                component_results[family] = result
                availability[family]["available"] += 1
                row[f"{family}_score"] = result["score"]
                row[f"{family}_alert"] = int(result["alert"])
            except BundleUnavailable as error:
                availability[family][error.reason] += 1
                row[f"{family}_score"] = None
                row[f"{family}_alert"] = None
        reasons = []
        if not current_valid:
            reasons.append("invalid_current_observation")
        if not target_valid:
            reasons.append("invalid_target_observation")
        if len(component_results) != len(FAMILIES):
            reasons.append("component_unavailable")
        if reasons:
            for reason in reasons:
                exclusions[reason] += 1
            row["common_case"] = False
            row["exclusion_reasons"] = ";".join(reasons)
            all_rows.append(row)
            day += timedelta(days=1)
            continue
        production = predict_ensemble_bundle(
            ensemble, frame, sensor_id=SENSOR_ID, units=units, as_of_date=day
        )
        ordered_scores = [
            component_results[family]["score"] for family in sorted(component_results)
        ]
        arithmetic_mean = sum(ordered_scores) / len(ordered_scores)
        if production["combined_probability"] != arithmetic_mean:
            raise EvaluationError("El promedio no coincide exactamente con produccion")
        row["average_score"] = arithmetic_mean
        row["average_alert"] = int(production["combined_alert"])
        votes = sum(int(component_results[family]["alert"]) for family in FAMILIES)
        row["positive_votes"] = votes
        row["majority_alert"] = int(votes >= 2)
        row["common_case"] = True
        row["exclusion_reasons"] = ""
        row["case_b_nondry_to_dry"] = bool(
            float(current) >= threshold and float(target) < threshold
        )
        all_rows.append(row)
        day += timedelta(days=1)
    common = [row for row in all_rows if row["common_case"]]
    methods = (*FAMILIES, "average", "persistence", "majority")
    metrics = {}
    for method in methods:
        scores = (
            [row[f"{method}_score"] for row in common] if method in (*FAMILIES, "average") else None
        )
        metrics[method] = method_metrics(
            [row["target"] for row in common],
            [row[f"{method}_alert"] for row in common],
            scores,
        )
    persistence_mcc = metrics["persistence"].get("mcc", {}).get("value")
    for method in (*FAMILIES, "average", "majority"):
        own = metrics[method].get("mcc", {}).get("value")
        metrics[method]["delta_mcc_vs_persistence"] = _defined(
            own - persistence_mcc if own is not None and persistence_mcc is not None else None,
            "mcc_undefined" if own is None or persistence_mcc is None else None,
        )
    comparisons = {
        **{
            f"{method}_minus_persistence": (method, "persistence")
            for method in (*FAMILIES, "average", "majority")
        },
        "average_minus_majority": ("average", "majority"),
    }
    case_b = [row for row in common if row["case_b_nondry_to_dry"]]
    case_b_results = {
        "n": len(case_b),
        "detected": {method: sum(row[f"{method}_alert"] for row in case_b) for method in methods},
    }
    episodes = observed_episodes(frame, threshold)
    summary = {
        "horizon": horizon,
        "physical_threshold_p20": threshold,
        "decision_threshold": decision_threshold,
        "candidate_emissions": candidate_count,
        "common_cases": len(common),
        "coverage_fraction": len(common) / candidate_count if candidate_count else None,
        "exclusions": dict(exclusions),
        "individual_availability": {
            family: dict(counts) for family, counts in availability.items()
        },
        "metrics": metrics,
        "case_b_nondry_at_t_dry_at_target": case_b_results,
        "episodes": episode_assessment(episodes, common, horizon, methods),
        "uncertainty": paired_block_bootstrap(common, comparisons),
    }
    return all_rows, summary


def _write_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def _render_report(metrics: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    lines = [
        "# Evaluacion retrospectiva exploratoria del ensamble Pergamino 2023",
        "",
        f"> **{LABEL}.**",
        "",
        "No es validacion confirmatoria ni acredita utilidad agronomica "
        "o probabilidades operativas.",
        "",
        "## Identidad",
        "",
        f"- SHA ejecutable: `{manifest['code_identity'].get('commit')}`.",
        f"- Protocolo SHA-256: `{manifest['protocol_sha256']}`.",
        f"- Bundles: `{manifest['bundle_root']}`.",
        "- Entradas restringidas antes de pandas: "
        f"{FILTER_START.isoformat()}..{FILTER_END.isoformat()}.",
        "",
        "## Resultados diarios sobre casos comunes",
        "",
        "| Horizonte | Metodo | N | Pos | Prec. | Recall | F1 | MCC | AP | Brier |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for horizon, result in metrics["horizons"].items():
        for method, item in result["metrics"].items():

            def val(name: str) -> str:
                value = (
                    item.get(name, {}).get("value")
                    if isinstance(item.get(name), dict)
                    else item.get(name)
                )
                return (
                    "ND"
                    if value is None
                    else f"{value:.4f}" if isinstance(value, float) else str(value)
                )

            lines.append(
                f"| +{horizon} | {method} | {item.get('n', 0)} | {item.get('positives', 0)} | "
                f"{val('precision')} | {val('recall')} | {val('f1')} | {val('mcc')} | "
                f"{val('average_precision')} | {val('brier')} |"
            )
    lines += [
        "",
        "## Interpretacion permitida",
        "",
        "Las tablas describen desempeno historico exploratorio, calidad "
        "probabilistica y cobertura de estos artefactos fijos sobre 2023. "
        "Los intervalos son pareados por bloques temporales y no convierten "
        "comparaciones multiples en confirmacion. Episodios se informan "
        "descriptivamente.",
        "",
        "El intercambio entre deteccion y falsas alertas no determina por si "
        "solo una politica de producto: falta un criterio externo de costos/uso. "
        "La mayoria es comparacion secundaria, no politica implementada; la "
        "fraccion de votos no es probabilidad. `display_probability` permanece "
        "deshabilitada.",
    ]
    return "\n".join(lines) + "\n"


def run_evaluation(
    *,
    bundle_root: Path,
    era5_csv: Path,
    nasa_csv: Path,
    output_dir: Path,
    preserve_filtered_inputs: bool = True,
) -> dict[str, Any]:
    _prepare_empty_directory(output_dir)
    manifest_path = output_dir / "execution_manifest.json"
    protocol_path = _REPO_ROOT / PROTOCOL_RELATIVE
    manifest: dict[str, Any] = {
        "schema_version": "ensemble-retrospective-evaluation-manifest.v1",
        "status": "iniciado",
        "label": LABEL,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_identity": capture_code_identity(_REPO_ROOT),
        "protocol_path": PROTOCOL_RELATIVE.as_posix(),
        "protocol_sha256": sha256_file(protocol_path),
        "environment": capture_environment(),
        "python_runtime": {"version": sys.version, "platform": platform.platform()},
        "bundle_root": str(bundle_root.resolve()),
        "arguments": {
            "era5_csv": str(era5_csv.resolve()),
            "nasa_csv": str(nasa_csv.resolve()),
            "output_dir": str(output_dir.resolve()),
            "preserve_filtered_inputs": preserve_filtered_inputs,
        },
        "predeclared": {
            "evaluation_emissions": "2023-01-01..2023-12-31-h",
            "target_year": 2023,
            "filter_window": [FILTER_START.isoformat(), FILTER_END.isoformat()],
            "methods": [*FAMILIES, "average", "persistence", "majority"],
            "reliability_edges": RELIABILITY_EDGES,
            "bootstrap": {
                "block_length_days": BLOCK_LENGTH,
                "seed": BOOTSTRAP_SEED,
                "replicates": BOOTSTRAP_REPLICATES,
            },
        },
    }
    write_json(manifest_path, manifest)
    temporary: tempfile.TemporaryDirectory[str] | None = None
    try:
        ensembles, bundle_record = load_verified_bundles(bundle_root)
        manifest["bundles"] = bundle_record
        if preserve_filtered_inputs:
            restricted_root = output_dir / "restricted_inputs"
            restricted_root.mkdir()
        else:
            temporary = tempfile.TemporaryDirectory(prefix="ensemble-eval-filtered-")
            restricted_root = Path(temporary.name)
        filtered_era5 = restricted_root / "era5_2022-12-26_2023-12-31.csv"
        filtered_nasa = restricted_root / "nasa_power_2022-12-26_2023-12-31.csv"
        manifest["inputs"] = {
            "era5": stream_filter_era5(era5_csv, filtered_era5),
            "nasa_power": stream_filter_nasa(nasa_csv, filtered_nasa),
        }
        expected_hashes = bundle_record["expected_input_hashes"]
        if (
            manifest["inputs"]["era5"]["source_sha256"] != expected_hashes["era5_csv"]
            or manifest["inputs"]["nasa_power"]["source_sha256"]
            != expected_hashes["nasa_power_csv"]
        ):
            raise EvaluationError(
                "Los CSV fuente no coinciden con los hashes usados para construir los bundles"
            )
        frame, frame_details = build_restricted_daily_frame(filtered_era5, filtered_nasa)
        manifest["restricted_daily_frame"] = frame_details
        all_predictions: list[dict[str, Any]] = []
        horizon_results: dict[str, Any] = {}
        for horizon in HORIZONS:
            rows, result = evaluate_horizon(frame, ensembles[horizon], horizon)
            all_predictions.extend(rows)
            horizon_results[str(horizon)] = result
        metrics = {
            "schema_version": "ensemble-retrospective-evaluation-metrics.v1",
            "label": LABEL,
            "horizons": horizon_results,
            "limitations": [
                "retrospective_non_independent_2023_previously_used",
                "single_site_single_period",
                "scores_not_operationally_qualified_probabilities",
                "episode_metrics_descriptive_without_intervals",
                "no_agronomic_cost_function",
            ],
        }
        predictions_path = output_dir / "predictions.csv"
        metrics_path = output_dir / "metrics.json"
        ui_path = output_dir / "ui_summary.json"
        report_path = output_dir / "report.md"
        _write_predictions(predictions_path, all_predictions)
        write_json(metrics_path, metrics)
        ui_summary = {
            "schema_version": "forecast-evidence-ui-summary.v1",
            "label": LABEL,
            "artifact_identity": bundle_record["identities"],
            "period": {"emissions": "2023-01-01..2023-12-31-h", "targets": "2023"},
            "horizons": {
                horizon: {
                    "support": {
                        "candidate_emissions": result["candidate_emissions"],
                        "common_cases": result["common_cases"],
                        "coverage_fraction": result["coverage_fraction"],
                    },
                    "metrics": result["metrics"],
                    "episodes": result["episodes"],
                }
                for horizon, result in horizon_results.items()
            },
            "probability_status": "not_qualified",
            "display_probability": False,
            "limitations": metrics["limitations"],
        }
        write_json(ui_path, ui_summary)
        report_path.write_text(_render_report(metrics, manifest), encoding="utf-8")
        bundle_after = tree_hashes(bundle_root)
        manifest["bundles"]["tree_after"] = bundle_after
        manifest["bundles"]["unchanged"] = bundle_after == bundle_record["tree_before"]
        if not manifest["bundles"]["unchanged"]:
            raise EvaluationError("Los hashes de bundles cambiaron durante la evaluacion")
        manifest["outputs"] = {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in (predictions_path, metrics_path, ui_path, report_path)
        }
        manifest["status"] = "completado"
        manifest["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(manifest_path, manifest)
        return manifest
    except Exception as error:
        manifest["status"] = "fallido"
        manifest["failed_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["failure"] = {"type": type(error).__name__, "message": str(error)}
        write_json(manifest_path, manifest)
        raise
    finally:
        if temporary is not None:
            temporary.cleanup()


def create_verified_backup(output_dir: Path, backup_dir: Path) -> dict[str, Any]:
    _prepare_empty_directory(backup_dir)
    for item in output_dir.iterdir():
        target = backup_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    source_hashes = tree_hashes(output_dir)
    backup_hashes = tree_hashes(backup_dir)
    if source_hashes != backup_hashes:
        raise EvaluationError("El respaldo no coincide byte a byte")
    verification = {
        "schema_version": "ensemble-retrospective-evaluation-backup.v1",
        "verified": True,
        "source": str(output_dir.resolve()),
        "backup": str(backup_dir.resolve()),
        "files": source_hashes,
    }
    write_json(output_dir / "backup_verification.json", verification)
    shutil.copy2(output_dir / "backup_verification.json", backup_dir / "backup_verification.json")
    return verification


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=LABEL)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--era5-csv", type=Path, required=True)
    parser.add_argument("--nasa-power-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--discard-filtered-inputs", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_evaluation(
        bundle_root=args.bundle_root,
        era5_csv=args.era5_csv,
        nasa_csv=args.nasa_power_csv,
        output_dir=args.output_dir,
        preserve_filtered_inputs=not args.discard_filtered_inputs,
    )
    create_verified_backup(args.output_dir, args.backup_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
