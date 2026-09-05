"""Flujo integrado de calidad de datos (spec data-quality, requirement
"Flujo integrado y parametrizable por configuración experimental").

Orquesta, en un único procedimiento reproducible, los tres sub-proyectos
de HU3: calidad/limpieza básica, detección de anomalías (opcional) y
generación de datos sintéticos (opcional). Los parámetros
`include_anomaly_detection` / `include_synthetic` son banderas booleanas
simples, no una herramienta de feature flags: la Épica 4 solo necesita
seleccionar una de 4 configuraciones conocidas de antemano (base,
+sintéticos, +anomalías, completa) al lanzar una corrida de experimento,
no alternar comportamiento en tiempo de ejecución para distintos
usuarios/entornos.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from data_quality.anomaly_detection import detect_anomalies
from data_quality.imputation import interpolate_missing_causal
from data_quality.quality_report import quality_report
from data_quality.scaling import apply_standardization, standardize
from data_quality.splitting import temporal_train_test_split
from data_quality.synthetic_data import generate_synthetic


def run_quality_pipeline(
    df: pd.DataFrame,
    numeric_columns: list[str],
    split_date: date,
    include_anomaly_detection: bool = True,
    include_synthetic: bool = False,
    n_synthetic_samples: int = 0,
    contamination: float = 0.05,
    random_state: int = 42,
) -> dict[str, Any]:
    """Ejecuta el flujo completo de calidad sobre `df` y devuelve un
    dict con: `quality_report` (diagnóstico sobre los datos crudos),
    `train` y `test` (particiones ya imputadas, con anomalías marcadas
    si corresponde, estandarizadas, y con filas sintéticas agregadas a
    `train` si corresponde), y `scaling_params` (ajustados solo sobre el
    conjunto de entrenamiento real, para no filtrar información del
    conjunto de evaluación ni de los datos sintéticos).
    """
    report = quality_report(df)

    train_raw, test_raw = temporal_train_test_split(df, split_date=split_date)

    train = interpolate_missing_causal(train_raw, columns=numeric_columns)
    train = train.dropna(subset=numeric_columns).reset_index(drop=True)

    warm_start = train.iloc[-1] if len(train) else None
    test = interpolate_missing_causal(test_raw, columns=numeric_columns, warm_start=warm_start)

    if include_anomaly_detection:
        train = detect_anomalies(
            train, columns=numeric_columns, contamination=contamination, random_state=random_state
        )
        test = detect_anomalies(
            test, columns=numeric_columns, contamination=contamination, random_state=random_state
        )

    train_scaled, scaling_params = standardize(train, columns=numeric_columns)
    test_scaled = apply_standardization(test, params=scaling_params)

    if include_synthetic and n_synthetic_samples > 0:
        synthetic = generate_synthetic(
            train, columns=numeric_columns, n_samples=n_synthetic_samples, random_state=random_state
        )
        synthetic_scaled = apply_standardization(synthetic, params=scaling_params)
        train_scaled = pd.concat([train_scaled, synthetic_scaled], ignore_index=True)

    return {
        "quality_report": report,
        "train": train_scaled,
        "test": test_scaled,
        "scaling_params": scaling_params,
    }
