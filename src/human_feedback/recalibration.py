"""Selección de observaciones y recalibración supervisada de un modelo
candidato (spec human-feedback, requirements "Selección de
observaciones para recalibración" y "Recalibración supervisada de un
modelo candidato").
"""

from __future__ import annotations

import pandas as pd
from sklearn.base import clone


def select_recalibration_observations(integrated_log: pd.DataFrame) -> pd.DataFrame:
    """Selecciona, de un registro integrado con predicciones, solo las
    observaciones `rechazada` con `etiqueta_corregida` no nula: las
    únicas que aportan una corrección real y verificable.
    """
    mask = (integrated_log["estado_validacion"] == "rechazada") & (
        integrated_log["etiqueta_corregida"].notna()
    )
    return integrated_log.loc[mask, ["fecha", "etiqueta_corregida"]].reset_index(drop=True)


def recalibrate_model(
    model: object,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    dates_train: pd.Series,
    recalibration_obs: pd.DataFrame,
) -> tuple[object, pd.Series]:
    """Reemplaza, en `y_train`, la etiqueta de cada fecha presente en
    `recalibration_obs` por su `etiqueta_corregida`, y reentrena una
    copia de `model` sobre el conjunto de entrenamiento corregido.
    Devuelve el modelo recalibrado y las etiquetas corregidas usadas.
    """
    dates_train = pd.Series(dates_train).reset_index(drop=True)
    corrected_y_train = y_train.reset_index(drop=True).copy()

    correction_by_date = dict(
        zip(recalibration_obs["fecha"], recalibration_obs["etiqueta_corregida"])
    )
    for fecha, etiqueta_corregida in correction_by_date.items():
        corrected_y_train.loc[dates_train == fecha] = etiqueta_corregida

    fitted = clone(model)
    fitted.fit(X_train, corrected_y_train)

    return fitted, corrected_y_train
