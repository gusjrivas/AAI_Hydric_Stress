"""Generación de datos sintéticos por muestreo estadístico (spec
data-quality, requirements de generación/similitud/utilidad predictiva).

Prototipo base: distribución normal multivariada ajustada a media y
covarianza reales, elegida por preservar correlaciones entre variables
sin requerir aprendizaje profundo — apropiado para el tamaño de dataset
disponible hoy (ver openspec/changes/add-synthetic-data-generation/
proposal.md, "Alternativas consideradas"). Un modelo generativo profundo
(GAN/VAE) queda como candidato para cuando haya más datos reales.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from data_ingestion.schema import normalize_to_schema


def generate_synthetic(
    df: pd.DataFrame,
    columns: list[str],
    n_samples: int,
    random_state: int = 42,
) -> pd.DataFrame:
    """Ajusta una distribución normal multivariada a `columns` de `df` y
    genera `n_samples` filas sintéticas muestreadas de esa distribución,
    marcadas con procedencia `sintetico`. No incluye columna de timestamp:
    los datos sintéticos no representan un momento real.
    """
    rng = np.random.default_rng(random_state)

    mean = df[columns].mean().to_numpy()
    covariance = df[columns].cov().to_numpy()

    samples = rng.multivariate_normal(mean, covariance, size=n_samples)
    synthetic = pd.DataFrame(samples, columns=columns)
    synthetic.insert(0, "timestamp", pd.NaT)

    return normalize_to_schema(synthetic, provenance="sintetico")


def statistical_similarity(
    real_df: pd.DataFrame, synthetic_df: pd.DataFrame, columns: list[str]
) -> dict[str, Any]:
    """Compara `real_df` contra `synthetic_df`: diferencia de media y
    desvío por columna, y diferencia agregada de la matriz de correlación
    entre `columns`.
    """
    mean_diff = {
        column: float(synthetic_df[column].mean() - real_df[column].mean()) for column in columns
    }
    std_diff = {
        column: float(synthetic_df[column].std() - real_df[column].std()) for column in columns
    }

    real_corr = real_df[columns].corr().to_numpy()
    synthetic_corr = synthetic_df[columns].corr().to_numpy()
    correlation_diff = float(np.abs(real_corr - synthetic_corr).mean())

    return {
        "mean_diff": mean_diff,
        "std_diff": std_diff,
        "correlation_diff": correlation_diff,
    }


def evaluate_predictive_utility(
    train_real: pd.DataFrame,
    train_synthetic: pd.DataFrame,
    test_real: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
) -> dict[str, float]:
    """Entrena un modelo de regresión lineal simple sobre `train_real` y,
    por separado, sobre `train_synthetic`, y evalúa ambos contra
    `test_real`. Devuelve el error absoluto medio (MAE) de cada uno, para
    comparar la utilidad predictiva de los datos sintéticos frente a los
    reales. No constituye el modelo de `predictive-modeling` (HU4).
    """
    model_real = LinearRegression().fit(train_real[feature_columns], train_real[target_column])
    model_synthetic = LinearRegression().fit(
        train_synthetic[feature_columns], train_synthetic[target_column]
    )

    predictions_from_real = model_real.predict(test_real[feature_columns])
    predictions_from_synthetic = model_synthetic.predict(test_real[feature_columns])

    return {
        "mae_real": float(mean_absolute_error(test_real[target_column], predictions_from_real)),
        "mae_synthetic": float(
            mean_absolute_error(test_real[target_column], predictions_from_synthetic)
        ),
    }
