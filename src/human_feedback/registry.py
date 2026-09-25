"""Persistencia, actualización y unión con predicciones del registro de
retroalimentación (spec human-feedback, requirements "Persistencia del
registro de retroalimentación", "Actualización del registro sin
pérdida de validaciones existentes" e "Integración de la
retroalimentación con los registros de predicción").
"""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from data_ingestion.storage import (
    DEFAULT_DATA_DIR,
    atomic_write_bytes,
    dataset_lock_path,
    interprocess_lock,
    load_dataset,
    save_dataset,
)
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


def update_feedback_log_atomically(
    name: str,
    update_fn: Callable[[pd.DataFrame | None], pd.DataFrame],
    data_dir: Path = DEFAULT_DATA_DIR,
    *,
    create_if_missing: bool = False,
) -> pd.DataFrame:
    """Ejecuta `load -> update_fn -> save` como una única unidad bajo el
    mismo lock interproceso que ya protege `save_dataset` (F-09): sin
    esto, dos ciclos concurrentes pueden leer la misma versión y el
    segundo en escribir sobreescribe silenciosamente la actualización
    del primero ("lost update"). Escribe directamente con
    `atomic_write_bytes` (no vía `save_dataset`) para no anidar una
    segunda adquisición del mismo lock dentro de esta.

    Por defecto (`create_if_missing=False`, el comportamiento previo,
    usado por `confirm_feedback`/`reject_feedback`), un archivo ausente
    propaga `FileNotFoundError` antes de invocar `update_fn`. Con
    `create_if_missing=True` (usado por `register_forecast_feedback`,
    F-09 completado para `forecast.py`), un archivo ausente pasa `None`
    a `update_fn`, que debe construir el registro inicial — sin eso, dos
    primeras emisiones concurrentes para el mismo sensor competirían
    por crear el archivo fuera de este lock."""
    lock_path = dataset_lock_path(name, data_dir)
    with interprocess_lock(lock_path):
        try:
            log = load_dataset(name, data_dir=data_dir)
        except FileNotFoundError:
            if not create_if_missing:
                raise
            log = None
        updated = update_fn(log)
        buffer = io.BytesIO()
        updated.to_parquet(buffer, index=False)
        atomic_write_bytes(data_dir / f"{name}.parquet", buffer.getvalue())
    return updated


def register_forecast_feedback(
    name: str, fresh: pd.DataFrame, data_dir: Path = DEFAULT_DATA_DIR
) -> pd.DataFrame:
    """Fusiona atómicamente las filas recién emitidas de un pronóstico
    (`fresh`, ya construidas por `human_feedback.schema.init_prediction_feedback`)
    en el registro de retroalimentación de `name`: las filas existentes
    (predicciones, revisiones, correcciones y metadatos ya persistidos)
    nunca se sobreescriben — solo se agregan las fechas de `fresh`
    ausentes del registro vigente. Reutiliza el mismo lock interproceso
    que protege `confirm_feedback`/`reject_feedback` (F-09), incluyendo
    el caso de que el archivo todavía no exista (dos primeras emisiones
    concurrentes para el mismo sensor no compiten por crearlo fuera del
    lock)."""

    def _merge(existing: pd.DataFrame | None) -> pd.DataFrame:
        if existing is None:
            return fresh
        return pd.concat(
            [existing, fresh[~fresh["fecha"].isin(existing["fecha"])]],
            ignore_index=True,
        )

    return update_feedback_log_atomically(name, _merge, data_dir=data_dir, create_if_missing=True)


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
