"""Procedimiento automatizado de experimentación con múltiples semillas
(spec experiment-runner, requirement "Ejecución automatizada de una
configuración experimental con múltiples semillas").

Ejecuta el orquestador de punta a punta (`architecture_integration.pipeline`)
una vez por semilla, agregando datos sintéticos sobre el espacio de
variables ya construidas (`experiment_runner.synthetic_augmentation`)
cuando la configuración lo pide.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from experiment_runner.scenarios import inject_gaussian_noise, subsample_training_period
from experiment_runner.synthetic_augmentation import add_synthetic_rows
from predictive_modeling.evaluation import evaluate_classifier
from predictive_modeling.models import build_candidate_models


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
) -> pd.DataFrame:
    """Ejecuta la configuración experimental (`include_anomaly_detection`,
    `include_synthetic`) sobre `df` una vez por cada semilla en `seeds`, y
    devuelve una fila por semilla con sus métricas de desempeño.

    `train_fraction` < 1.0 simula escasez de datos (conserva solo esa
    fracción más reciente del período de entrenamiento). `noise_std_ratio`
    > 0.0 simula ruido de sensor (agrega ruido gaussiano a `feature_columns`,
    con una semilla de ruido distinta por repetición).
    """
    rows = []
    for seed in seeds:
        model = build_candidate_models(random_state=seed)[model_name]

        scenario_df = subsample_training_period(
            df, split_date=split_date, train_fraction=train_fraction
        )
        if noise_std_ratio > 0.0:
            scenario_df = inject_gaussian_noise(
                scenario_df,
                columns=feature_columns,
                noise_std_ratio=noise_std_ratio,
                random_state=seed,
            )

        result = run_end_to_end_pipeline(
            scenario_df,
            label_column=label_column,
            feature_columns=feature_columns,
            split_date=split_date,
            model=model,
            alert_threshold=alert_threshold,
            include_anomaly_detection=include_anomaly_detection,
            random_state=seed,
        )

        if include_synthetic and n_synthetic_samples > 0:
            augmented_train = add_synthetic_rows(
                result["train"],
                feature_columns=result["feature_columns"],
                target_column="stress_label",
                n_samples=n_synthetic_samples,
                random_state=seed,
            )
            model.fit(augmented_train[result["feature_columns"]], augmented_train["stress_label"])
            y_proba = pd.Series(
                model.predict_proba(result["test"][result["feature_columns"]])[:, 1]
            )
        else:
            y_proba = result["y_proba"]

        y_pred = (y_proba >= alert_threshold).astype(int).reset_index(drop=True)
        y_true = result["test"]["stress_label"].reset_index(drop=True)

        metrics = evaluate_classifier(y_true, y_pred, y_proba.reset_index(drop=True))
        rows.append({"seed": seed, **metrics})

    return pd.DataFrame(rows)
