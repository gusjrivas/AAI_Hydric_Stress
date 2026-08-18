"""Aumento sintético del conjunto de entrenamiento sobre variables ya
construidas (spec experiment-runner, requirement "Aumento sintético del
conjunto de entrenamiento sobre variables ya construidas").

A diferencia de `data_quality.synthetic_data.generate_synthetic` (que
muestrea columnas físicas crudas y no requiere fecha), esta función
muestrea directamente sobre las variables predictoras ya construidas
en HU4 (retardos, ventanas móviles) y la variable objetivo, evitando el
problema de asignarles una fecha o continuidad temporal real.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_synthetic_rows(
    train_df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    n_samples: int,
    random_state: int = 42,
) -> pd.DataFrame:
    """Genera `n_samples` filas sintéticas muestreando una normal
    multivariada ajustada a `feature_columns` + `target_column` de
    `train_df`, redondea y recorta la variable objetivo a {0, 1}, marca
    las filas nuevas con `origen="sintetico"`, y las concatena a
    `train_df`.
    """
    rng = np.random.default_rng(random_state)
    columns = feature_columns + [target_column]

    mean = train_df[columns].mean().to_numpy()
    covariance = train_df[columns].cov().to_numpy()

    samples = rng.multivariate_normal(mean, covariance, size=n_samples)
    synthetic = pd.DataFrame(samples, columns=columns)
    synthetic[target_column] = synthetic[target_column].round().clip(0, 1).astype(int)
    synthetic["origen"] = "sintetico"

    return pd.concat([train_df, synthetic], ignore_index=True)
