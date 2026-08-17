"""Persistencia, actualización y unión con predicciones del registro de
retroalimentación (spec human-feedback, requirements "Persistencia del
registro de retroalimentación", "Actualización del registro sin
pérdida de validaciones existentes" e "Integración de la
retroalimentación con los registros de predicción").
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset, save_dataset
from human_feedback.schema import init_feedback_log


def save_feedback_log(name: str, log: pd.DataFrame, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Guarda un registro de retroalimentación reutilizando el contrato
    `save_dataset` de `data-ingestion`.
    """
    return save_dataset(name, log, data_dir=data_dir)


def load_feedback_log(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Recupera un registro de retroalimentación reutilizando el
    contrato `load_dataset` de `data-ingestion`.
    """
    return load_dataset(name, data_dir=data_dir)


def upsert_feedback_log(
    existing: pd.DataFrame, dates: pd.Series, alerts: pd.Series
) -> pd.DataFrame:
    """Combina un registro existente con alertas recién generadas: las
    fechas nuevas se agregan en estado `pendiente`; las fechas ya
    presentes en `existing` conservan su estado de validación,
    corrección y observación, sin importar el nuevo valor de alerta.
    """
    fresh = init_feedback_log(dates, alerts)
    new_dates_mask = ~fresh["fecha"].isin(existing["fecha"])

    return pd.concat([existing, fresh[new_dates_mask]], ignore_index=True)


def integrate_feedback_with_predictions(
    log: pd.DataFrame, predictions: pd.DataFrame
) -> pd.DataFrame:
    """Une, por fecha, el registro de retroalimentación con la
    probabilidad predicha y la etiqueta real de las predicciones.
    """
    return log.merge(predictions, on="fecha", how="inner")
