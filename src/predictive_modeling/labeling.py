"""Variable objetivo de estrés hídrico por umbral relativo, congelado en
entrenamiento (spec predictive-modeling, requirement "Variable objetivo
de estrés hídrico por umbral relativo, sin fuga temporal").

El umbral es un percentil de la distribución histórica observada de la
propia variable en el punto/período evaluado, no un umbral agronómico
absoluto (capacidad de campo/punto de marchitez) — no calibrado
todavía por falta de datos de suelo específicos (ver
openspec/changes/add-feature-engineering/proposal.md).

`fit_stress_threshold` y `add_stress_label` están separadas
deliberadamente: el umbral DEBE calcularse solo sobre el conjunto de
entrenamiento y reutilizarse, congelado, para etiquetar tanto
entrenamiento como evaluación — nunca recalcularse sobre datos que
incluyan el período de evaluación (fuga temporal confirmada en la
auditoría metodológica de la memoria técnica: el umbral anterior se
calculaba sobre el DataFrame completo, antes de la partición).
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import TIMESTAMP_COLUMN


def fit_stress_threshold(df: pd.DataFrame, column: str, percentile: float) -> float:
    """Calcula el umbral de estrés (percentil `percentile` de `column`)
    a partir de `df`. Debe llamarse únicamente con el conjunto de
    entrenamiento — el valor devuelto queda congelado y se reutiliza
    igual para etiquetar el conjunto de evaluación, nunca se vuelve a
    calcular sobre él.
    """
    return float(df[column].quantile(percentile / 100.0))


def add_stress_label(
    df: pd.DataFrame,
    column: str,
    horizon_days: int,
    threshold: float,
) -> pd.DataFrame:
    """Agrega `stress_label` (1/0/NaN) a una copia de `df`: 1 si el valor
    de `column` en `horizon_days` días es menor a `threshold` (calculado
    previamente con `fit_stress_threshold`, típicamente solo sobre el
    conjunto de entrenamiento). Los últimos `horizon_days` días no
    tienen horizonte futuro completo y quedan con `stress_label` = NaN,
    no un valor inventado.
    """
    result = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True).copy()

    future_value = result[column].shift(-horizon_days)

    result["stress_label"] = (future_value < threshold).astype("Float64")
    result.loc[future_value.isna(), "stress_label"] = pd.NA

    return result
