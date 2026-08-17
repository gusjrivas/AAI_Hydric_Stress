"""Variable objetivo de estrés hídrico por umbral relativo (spec
predictive-modeling, requirement "Variable objetivo de estrés hídrico
por umbral relativo").

El umbral es un percentil de la distribución histórica observada de la
propia variable en el punto/período evaluado, no un umbral agronómico
absoluto (capacidad de campo/punto de marchitez) — no calibrado
todavía por falta de datos de suelo específicos (ver
openspec/changes/add-feature-engineering/proposal.md).
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import TIMESTAMP_COLUMN


def add_stress_label(
    df: pd.DataFrame,
    column: str,
    horizon_days: int,
    percentile: float,
) -> pd.DataFrame:
    """Agrega `stress_label` (1/0/NaN) a una copia de `df`: 1 si el valor
    de `column` en `horizon_days` días es menor al percentil `percentile`
    de la distribución histórica de `column` en `df`. Los últimos
    `horizon_days` días no tienen horizonte futuro completo y quedan con
    `stress_label` = NaN, no un valor inventado.
    """
    result = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True).copy()

    threshold = result[column].quantile(percentile / 100.0)
    future_value = result[column].shift(-horizon_days)

    result["stress_label"] = (future_value < threshold).astype("Float64")
    result.loc[future_value.isna(), "stress_label"] = pd.NA

    return result
