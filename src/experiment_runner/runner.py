"""Paired experiments with a common observed target and daily input history."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from architecture_integration.pipeline import prepare_daily_features, run_end_to_end_pipeline
from data_quality.temporal import validate_daily_series
from experiment_runner.scenarios import (
    fit_noise_scales,
    inject_gaussian_noise,
    select_training_dates,
)
from experiment_runner.synthetic_augmentation import add_synthetic_rows
from predictive_modeling.contract import make_contract, positive_probability
from predictive_modeling.evaluation import evaluate_classifier
from predictive_modeling.labeling import add_stress_label, fit_stress_threshold
from predictive_modeling.models import (
    build_candidate_models,
    predict_always_stress_baseline,
    predict_majority_class_baseline,
    predict_persistence_baseline,
)


def run_configuration(
    df: pd.DataFrame,
    label_column: str,
    feature_columns: list[str],
    split_date: date,
    model_name: str,
    include_anomaly_detection: bool,
    include_synthetic: bool,
    seeds: list[int],
    n_synthetic_samples: int = 0,
    alert_threshold: float = 0.5,
    train_fraction: float = 1.0,
    noise_std_ratio: float = 0.0,
    horizon_days: int = 3,
    percentile: float = 20.0,
    lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
    contamination: float = 0.05,
    scarcity_mode: str = "coverage",
    noise_mode: str = "both",
    include_current: bool = False,
) -> pd.DataFrame:
    if noise_mode not in {"both", "test_only"}:
        raise ValueError("noise_mode debe ser both o test_only.")
    reference = validate_daily_series(df)
    cutoff = pd.Timestamp(split_date)
    clean_train = reference[reference.timestamp < cutoff]
    threshold = fit_stress_threshold(clean_train, label_column, percentile)
    scales = fit_noise_scales(clean_train, feature_columns)
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
    clean_features = prepare_daily_features(reference, contract)
    clean_labels = add_stress_label(reference, label_column, horizon_days, threshold)
    base_names = [c for c in contract["model_features"] if c != "is_anomaly"]
    eligible = (
        clean_features[base_names + feature_columns].notna().all(axis=1)
        & clean_labels.stress_label.notna()
        & (reference.timestamp + pd.Timedelta(days=horizon_days) < cutoff)
    )
    rows, artifacts = [], []
    for seed in seeds:
        # Independent, named random streams. Paired conditions share each stream.
        selection_seed, noise_train_seed, noise_test_seed, synthetic_seed = [
            int(x) for x in np.random.SeedSequence(seed).generate_state(4)
        ]
        selected_dates = select_training_dates(
            reference.loc[eligible, "timestamp"], train_fraction, scarcity_mode, selection_seed
        )
        observed = reference.copy()
        if noise_std_ratio:
            for is_train, noise_seed in [(True, noise_train_seed), (False, noise_test_seed)]:
                if is_train and noise_mode == "test_only":
                    continue
                mask = reference.timestamp < cutoff if is_train else reference.timestamp >= cutoff
                noisy = inject_gaussian_noise(
                    reference.loc[mask], feature_columns, noise_std_ratio, noise_seed, scales=scales
                )
                observed.loc[mask, feature_columns] = noisy[feature_columns]
        model = build_candidate_models(random_state=seed)[model_name]
        result = run_end_to_end_pipeline(
            observed,
            label_column=label_column,
            feature_columns=feature_columns,
            split_date=split_date,
            model=model,
            horizon_days=horizon_days,
            percentile=percentile,
            lags=lags,
            rolling_windows=rolling_windows,
            alert_threshold=alert_threshold,
            include_anomaly_detection=include_anomaly_detection,
            contamination=contamination,
            random_state=seed,
            reference_df=reference,
            stress_threshold=threshold,
            include_current=include_current,
            training_dates=selected_dates,
        )
        if include_synthetic and n_synthetic_samples > 0:
            augmented = add_synthetic_rows(
                result["train"],
                result["feature_columns"],
                "stress_label",
                n_synthetic_samples,
                synthetic_seed,
            )
            model.fit(augmented[result["feature_columns"]], augmented.stress_label)
            probabilities = positive_probability(model, result["test"][result["feature_columns"]])
        else:
            probabilities = result["y_proba"]
        y_true = result["test"].stress_label.reset_index(drop=True)
        y_pred = (probabilities >= alert_threshold).astype(int)
        metrics = evaluate_classifier(y_true, y_pred, probabilities)
        predictions = result["test"][["timestamp", "target_timestamp", "target_observed"]].copy()
        predictions["y_true"] = y_true
        predictions["y_proba"] = probabilities
        predictions["y_pred"] = y_pred
        baselines = {
            "persistence": predict_persistence_baseline(result["test"], label_column, threshold),
            "majority_class": predict_majority_class_baseline(
                result["train"].stress_label, len(y_true)
            ),
            "always_stress": predict_always_stress_baseline(len(y_true)),
        }
        for name, prediction in baselines.items():
            prediction = prediction.reset_index(drop=True)
            metrics.update(
                {f"{name}_{k}": v for k, v in evaluate_classifier(y_true, prediction).items()}
            )
            predictions[name] = prediction
        rows.append(
            {
                "seed": seed,
                **metrics,
                "threshold": threshold,
                "train_rows": len(result["train"]),
                "test_rows": len(y_true),
                "test_positive_rate": float(y_true.mean()) if len(y_true) else float("nan"),
            }
        )
        artifacts.append(
            {
                "seed": seed,
                "predictions": predictions,
                "training_dates": [str(x) for x in selected_dates],
                "selection_seed": selection_seed,
                "noise_train_seed": noise_train_seed,
                "noise_test_seed": noise_test_seed,
                "synthetic_seed": synthetic_seed,
                "noise_scales": scales,
                "contract": contract,
                "model_parameters": model.get_params(),
            }
        )
    results = pd.DataFrame(rows)
    results.attrs["artifacts"] = artifacts
    return results
