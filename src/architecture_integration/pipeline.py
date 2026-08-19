"""Orquestador de punta a punta entre las capacidades del núcleo de IA
(spec architecture-integration, requirements "Orquestación de punta a
punta de las capacidades del núcleo de IA" y "Orden de etapas sin fuga
temporal entre calidad y modelado").

Encadena, en el orden correcto para evitar fuga temporal: imputación
(`data-quality`) → etiquetado y variables predictoras
(`predictive-modeling`, sobre la serie completa) → partición temporal
(`data-quality`) → detección de anomalías opcional (`data-quality`,
después de partir) → entrenamiento y alertas (`predictive-modeling`) →
inicialización del registro de retroalimentación (`human-feedback`).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from sklearn.base import clone

from data_ingestion.schema import TIMESTAMP_COLUMN
from data_quality.anomaly_detection import detect_anomalies
from data_quality.imputation import interpolate_missing
from data_quality.quality_report import quality_report
from data_quality.splitting import temporal_train_test_split
from human_feedback.schema import init_feedback_log
from predictive_modeling.alerts import generate_alerts
from predictive_modeling.feature_engineering import add_lag_features, add_rolling_features
from predictive_modeling.labeling import add_stress_label


def run_end_to_end_pipeline(
    df: pd.DataFrame,
    label_column: str,
    feature_columns: list[str],
    split_date: date,
    model: object,
    horizon_days: int = 3,
    percentile: float = 20.0,
    lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
    alert_threshold: float = 0.5,
    include_anomaly_detection: bool = True,
    contamination: float = 0.05,
    random_state: int = 42,
    skip_fit: bool = False,
) -> dict[str, Any]:
    """Ejecuta el flujo completo sobre `df`: imputación, etiquetado,
    variables predictoras, partición temporal, detección de anomalías
    opcional, entrenamiento del modelo, alertas, y registro de
    retroalimentación inicializado. Si `skip_fit` es `True`, usa `model`
    tal cual, ya entrenado, sin reentrenar.
    """
    lags = lags if lags is not None else [1, 2, 3]
    rolling_windows = rolling_windows if rolling_windows is not None else [3, 7]

    report = quality_report(df)

    imputed = interpolate_missing(df, columns=feature_columns)
    labeled = add_stress_label(
        imputed, column=label_column, horizon_days=horizon_days, percentile=percentile
    )
    featured = add_lag_features(labeled, columns=feature_columns, lags=lags)
    featured = add_rolling_features(featured, columns=feature_columns, windows=rolling_windows)

    feature_cols = [c for c in featured.columns if ("_lag" in c or "_roll_mean" in c)]
    featured = featured.dropna(subset=["stress_label"] + feature_cols).reset_index(drop=True)

    train, test = temporal_train_test_split(featured, split_date=split_date)

    if include_anomaly_detection:
        train = detect_anomalies(
            train, columns=feature_columns, contamination=contamination, random_state=random_state
        )
        test = detect_anomalies(
            test, columns=feature_columns, contamination=contamination, random_state=random_state
        )

    X_train, y_train = train[feature_cols], train["stress_label"]
    X_test = test[feature_cols]

    if skip_fit:
        fitted_model = model
    else:
        fitted_model = clone(model)
        fitted_model.fit(X_train, y_train)

    y_proba = pd.Series(fitted_model.predict_proba(X_test)[:, 1]).reset_index(drop=True)
    alerts = generate_alerts(y_proba, threshold=alert_threshold)
    feedback_log = init_feedback_log(test[TIMESTAMP_COLUMN].reset_index(drop=True), alerts)

    return {
        "quality_report": report,
        "train": train,
        "test": test,
        "feature_columns": feature_cols,
        "model": fitted_model,
        "y_proba": y_proba,
        "alerts": alerts,
        "feedback_log": feedback_log,
    }
