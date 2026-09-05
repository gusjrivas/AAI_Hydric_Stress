"""Daily causal training, held-out evaluation and label-free future inference."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from sklearn.base import clone
from sklearn.pipeline import Pipeline

from data_quality.anomaly_detection import apply_anomaly_detector, fit_anomaly_detector
from data_quality.imputation import interpolate_missing_causal
from data_quality.quality_report import quality_report
from data_quality.splitting import temporal_train_test_split
from data_quality.temporal import validate_daily_series
from human_feedback.schema import init_feedback_log
from predictive_modeling.alerts import generate_alerts
from predictive_modeling.anomaly_features import AnomalyFeatures
from predictive_modeling.contract import FittedPredictor, make_contract, positive_probability
from predictive_modeling.feature_engineering import add_lag_features, add_rolling_features
from predictive_modeling.labeling import add_stress_label, fit_stress_threshold
from predictive_modeling.model_selection import select_best_candidate
from predictive_modeling.models import DEFAULT_HYPERPARAMETER_GRIDS, build_candidate_models


def prepare_daily_features(df, contract):
    ordered = validate_daily_series(df)
    columns = contract["raw_input_features"]
    ordered[columns] = ordered[columns].astype(float)
    filled = interpolate_missing_causal(ordered, columns)
    featured = add_lag_features(filled, columns, contract["lags"])
    featured = add_rolling_features(featured, columns, contract["rolling_windows"])
    return featured


def predict_available(df, predictor: FittedPredictor):
    """Predict available rows without needing their future targets; never fit."""
    predictor.validate(predictor.contract)
    contract = predictor.contract
    featured = prepare_daily_features(df, contract)
    names = [c for c in contract["model_features"] if c != "is_anomaly"]
    featured = featured.dropna(subset=names + contract["raw_input_features"])
    if predictor.detector is not None and not featured.empty:
        featured = apply_anomaly_detector(
            featured, contract["raw_input_features"], predictor.detector
        )
    elif predictor.detector is not None:
        featured["is_anomaly"] = pd.Series(dtype=bool)
    featured = featured.reset_index(drop=True)
    featured["target_timestamp"] = featured.timestamp + pd.Timedelta(days=contract["horizon_days"])
    probabilities = positive_probability(predictor.model, featured[contract["model_features"]])
    featured["y_proba"] = probabilities
    featured["alert"] = generate_alerts(probabilities, contract["alert_threshold"])
    featured["out_of_sample"] = featured.timestamp > pd.Timestamp(predictor.trained_through)
    return featured


def run_end_to_end_pipeline(
    df: pd.DataFrame,
    label_column: str,
    feature_columns: list[str],
    split_date: date,
    model: object | None = None,
    horizon_days: int = 3,
    percentile: float = 20.0,
    lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
    alert_threshold: float = 0.5,
    include_anomaly_detection: bool = True,
    contamination: float = 0.05,
    random_state: int = 42,
    skip_fit: bool = False,
    reference_df: pd.DataFrame | None = None,
    stress_threshold: float | None = None,
    include_current: bool = False,
    training_dates: list | None = None,
    calibration_end: date | None = None,
) -> dict[str, Any]:
    """Keep the daily calendar intact until features and observed targets exist.

    Automatic selection reserves an initial calibration prefix before ALL folds.
    Fixed-model experiments may supply a common threshold fitted on clean train.
    Reuse requires a FittedPredictor; its threshold and detector remain frozen.
    """
    contract = make_contract(
        feature_columns,
        label_column,
        horizon_days,
        lags,
        rolling_windows,
        include_current,
        include_anomaly_detection,
        contamination,
        alert_threshold,
        percentile,
    )
    ordered = validate_daily_series(df)
    reference = validate_daily_series(reference_df if reference_df is not None else df)
    if not ordered.timestamp.equals(reference.timestamp):
        raise ValueError("Observaciones y referencia deben compartir exactamente el calendario.")
    train_raw, _ = temporal_train_test_split(reference, split_date)
    if train_raw.empty:
        raise ValueError("Entrenamiento vacío antes del corte.")
    cutoff = pd.Timestamp(split_date)
    selection_start = None
    if skip_fit:
        if not isinstance(model, FittedPredictor):
            raise ValueError("skip_fit requiere un FittedPredictor con contrato completo.")
        model.validate(contract)
        threshold = model.threshold
    else:
        calibration = train_raw
        if model is None:
            if stress_threshold is not None and calibration_end is None:
                raise ValueError(
                    "La selección automática exige el período de calibración del umbral."
                )
            end = (
                pd.Timestamp(calibration_end)
                if calibration_end is not None
                else train_raw.timestamp.iloc[max(0, len(train_raw) // 5 - 1)]
            )
            if end >= cutoff:
                raise ValueError("La calibración debe terminar antes del entrenamiento/validación.")
            calibration = train_raw[train_raw.timestamp <= end]
            selection_start = end
            calibration_end = end.date()
        threshold = (
            stress_threshold
            if stress_threshold is not None
            else fit_stress_threshold(calibration, label_column, percentile)
        )
        if pd.isna(threshold):
            raise ValueError("No hay observaciones para calibrar el umbral de estrés.")
    featured = prepare_daily_features(ordered, contract)
    labels = add_stress_label(reference, label_column, horizon_days, threshold)
    featured["stress_label"] = labels["stress_label"]
    featured["target_observed"] = reference[label_column].shift(-horizon_days).notna()
    featured["target_timestamp"] = reference.timestamp + pd.Timedelta(days=horizon_days)
    base_names = [c for c in contract["model_features"] if c != "is_anomaly"]
    eligible = featured.dropna(subset=base_names + feature_columns + ["stress_label"])
    # Purge by target date, not the number of retained rows after missing targets.
    train = eligible[eligible.target_timestamp < cutoff].copy()
    if selection_start is not None:
        train = train[train.timestamp > selection_start]
    if training_dates is not None:
        train = train[train.timestamp.isin(pd.to_datetime(training_dates))]
    test = eligible[eligible.timestamp >= cutoff].copy()
    if skip_fit:
        test = test[test.timestamp > pd.Timestamp(model.trained_through)]
    train = train.reset_index(drop=True)
    test = test.reset_index(drop=True)
    names = contract["model_features"]
    detector = None
    model_name = None
    warning = None
    diagnostics = []
    if skip_fit:
        predictor = model
        fitted = predictor.model
        detector = predictor.detector
        model_name = predictor.model_name
        warning = predictor.selection_warning
        diagnostics = predictor.fold_diagnostics
    else:
        if train.empty or train.stress_label.nunique() < 2:
            raise ValueError("Se requieren ejemplos de ambas clases en entrenamiento.")
        if model is None:
            candidates = None
            grids = None
            selection_columns = base_names
            if include_anomaly_detection:
                candidates = {
                    name: Pipeline(
                        [
                            (
                                "features",
                                AnomalyFeatures(
                                    feature_columns, base_names, contamination, random_state
                                ),
                            ),
                            ("classifier", candidate),
                        ]
                    )
                    for name, candidate in build_candidate_models(random_state).items()
                }
                grids = {
                    name: {f"classifier__{key}": value for key, value in grid.items()}
                    for name, grid in DEFAULT_HYPERPARAMETER_GRIDS.items()
                }
                selection_columns = list(dict.fromkeys(base_names + feature_columns))
            selection = select_best_candidate(
                train[selection_columns],
                train.stress_label,
                candidates=candidates,
                param_grids=grids,
                gap=horizon_days,
                random_state=random_state,
            )
            fitted = selection["model"]
            model_name = selection["model_name"]
            warning = selection["selection_warning"]
            diagnostics = selection["fold_diagnostics"]
            if include_anomaly_detection:
                detector = fitted.named_steps["features"].detector_
                fitted = fitted.named_steps["classifier"]
        else:
            if include_anomaly_detection:
                detector = fit_anomaly_detector(train, feature_columns, contamination, random_state)
                train = apply_anomaly_detector(train, feature_columns, detector)
            fitted = clone(model).fit(train[names], train.stress_label)
        predictor = FittedPredictor(
            fitted,
            contract,
            float(threshold),
            str(
                max(
                    train.target_timestamp.max(),
                    pd.Timestamp(calibration_end or train_raw.timestamp.max()),
                )
            ),
            detector,
            model_name,
            str(calibration_end or train_raw.timestamp.max().date()),
        )
        predictor.selection_warning = warning
        predictor.fold_diagnostics = diagnostics
        predictor.training_rows = len(train)
        predictor.validate(contract)
    if detector is not None:
        train = apply_anomaly_detector(train, feature_columns, detector) if len(train) else train
        if len(test):
            test = apply_anomaly_detector(test, feature_columns, detector)
        else:
            test["is_anomaly"] = pd.Series(dtype=bool)
    probabilities = positive_probability(fitted, test[names])
    alerts = generate_alerts(probabilities, alert_threshold)
    return {
        "quality_report": quality_report(ordered),
        "train": train,
        "test": test,
        "feature_columns": names,
        "raw_input_features": feature_columns,
        "model": fitted,
        "predictor": predictor,
        "contract": contract,
        "model_name": model_name,
        "model_selection_warning": warning,
        "fold_diagnostics": diagnostics,
        "threshold": threshold,
        "y_proba": probabilities,
        "alerts": alerts,
        "feedback_log": init_feedback_log(test.timestamp.reset_index(drop=True), alerts),
    }
