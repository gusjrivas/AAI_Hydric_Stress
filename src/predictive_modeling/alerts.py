"""Generación de alertas tempranas y análisis de errores de predicción
(spec predictive-modeling, requirements "Generación de alertas
tempranas por umbral de probabilidad" y "Análisis de errores de
predicción por fecha").
"""

from __future__ import annotations

import pandas as pd


def generate_alerts(y_proba: pd.Series, threshold: float = 0.5) -> pd.Series:
    """Convierte una probabilidad predicha de estrés en una alerta
    binaria: 1 si `y_proba` es mayor o igual a `threshold`, 0 en caso
    contrario.
    """
    return (y_proba >= threshold).astype(int)


def analyze_prediction_errors(
    dates: pd.Series, y_true: pd.Series, alerts: pd.Series
) -> dict[str, pd.Series]:
    """Identifica las fechas de falsos positivos (alerta sin estrés
    real) y falsos negativos (estrés real sin alerta) entre `dates`,
    `y_true` y `alerts`.
    """
    dates = pd.Series(dates).reset_index(drop=True)
    y_true = pd.Series(y_true).reset_index(drop=True)
    alerts = pd.Series(alerts).reset_index(drop=True)

    false_positive_mask = (alerts == 1) & (y_true == 0)
    false_negative_mask = (alerts == 0) & (y_true == 1)

    return {
        "false_positives": dates[false_positive_mask].reset_index(drop=True),
        "false_negatives": dates[false_negative_mask].reset_index(drop=True),
    }
