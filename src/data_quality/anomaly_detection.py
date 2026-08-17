"""Detección de anomalías no supervisada (spec data-quality, requirement
"Detección de anomalías no supervisada"). Método base: Isolation Forest
(scikit-learn), elegido por no requerir etiquetas previas de anomalía —
ninguna está disponible en este dominio (ver
docs/research/hu1-variables-y-antecedentes.md, sección 3).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def detect_anomalies(
    df: pd.DataFrame,
    columns: list[str],
    contamination: float = 0.05,
    random_state: int = 42,
) -> pd.DataFrame:
    """Ajusta un Isolation Forest sobre `columns` y devuelve una copia de
    `df` con una columna booleana `is_anomaly`. No requiere etiquetas de
    anomalía previas.
    """
    result = df.copy()

    model = IsolationForest(contamination=contamination, random_state=random_state)
    predictions = model.fit_predict(result[columns])
    result["is_anomaly"] = predictions == -1

    return result


def evaluate_with_injected_anomalies(
    df: pd.DataFrame,
    columns: list[str],
    n_injected: int = 5,
    contamination: float = 0.05,
    random_state: int = 42,
) -> float:
    """Evalúa el detector inyectando `n_injected` anomalías sintéticas
    (valores extremos, muy por fuera de la distribución de cada columna)
    en filas elegidas al azar de una copia de `df`, y devuelve la
    proporción de esas filas inyectadas que el detector marcó como
    anómalas. No requiere anomalías reales etiquetadas.
    """
    rng = np.random.default_rng(random_state)
    injected = df.copy().reset_index(drop=True)

    injected_indices = rng.choice(len(injected), size=n_injected, replace=False)
    for column in columns:
        column_std = injected[column].std()
        extreme_offset = 20 * column_std if column_std else 20.0
        injected.loc[injected_indices, column] = injected[column].mean() + extreme_offset

    detected = detect_anomalies(
        injected, columns=columns, contamination=contamination, random_state=random_state
    )

    flagged = detected.loc[injected_indices, "is_anomaly"]
    return float(flagged.mean())
