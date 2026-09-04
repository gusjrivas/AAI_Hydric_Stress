"""Helper compartido de ejecución del pipeline de pronóstico, por
sensor (spec alerting-ui, requirements "Uso del modelo recalibrado en
el próximo pronóstico, por sensor" y "Reutilización del modelo
auto-seleccionado mientras el dataset de un sensor no cambie"). Usado
por `/forecast/{sensor_id}/run` y `/recalibrate/{sensor_id}` para no
duplicar la lógica de elección de modelo y llamada al pipeline.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, get_dataset_fingerprint, load_dataset
from human_feedback.model_registry import load_latest_recalibrated_model

from .config import FEATURE_COLUMNS, LABEL_COLUMN, RANDOM_STATE

_selection_cache_lock = threading.Lock()
_selection_cache: dict[str, dict[str, Any]] = {}


def load_dataset_or_raise(
    sensor_id: str, data_dir: Path = DEFAULT_DATA_DIR
) -> tuple[pd.DataFrame, tuple[float, int]]:
    """Carga el dataset propio de `sensor_id` junto con su fingerprint
    (capturado inmediatamente después de la lectura), o levanta
    `FileNotFoundError` con un mensaje explícito si no existe.
    """
    dataset_name = dataset_name_for(sensor_id)
    try:
        df = load_dataset(dataset_name, data_dir=data_dir)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"No existe el dataset '{dataset_name}'.") from error
    return df, get_dataset_fingerprint(dataset_name, data_dir=data_dir)


def execute_configured_pipeline(
    df: pd.DataFrame,
    sensor_id: str,
    fingerprint: tuple[float, int] | None = None,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, Any]:
    """Ejecuta el pipeline completo sobre `df` para `sensor_id`: si hay
    un modelo recalibrado registrado para ese sensor en MLflow, lo usa
    sin reentrenar (`skip_fit=True`), ignorando el caché de selección
    de ese sensor. Si no, reutiliza el último modelo auto-seleccionado
    de ese sensor mientras su dataset no haya cambiado (comparando su
    fingerprint); si cambió o todavía no hay ninguno cacheado para ese
    sensor, deja que `run_end_to_end_pipeline` seleccione
    automáticamente el mejor modelo candidato y guarda el resultado en
    el caché, bajo la clave de ese sensor. El caché de selección
    (`_selection_cache`) es un dict por `sensor_id` — nunca se
    comparte entre sensores.
    """
    global _selection_cache

    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    recalibrated_model = load_latest_recalibrated_model(sensor_id)
    if recalibrated_model is not None:
        return run_end_to_end_pipeline(
            df,
            label_column=LABEL_COLUMN,
            feature_columns=FEATURE_COLUMNS,
            split_date=split_date,
            model=recalibrated_model,
            include_anomaly_detection=False,
            random_state=RANDOM_STATE,
            skip_fit=True,
        )

    if fingerprint is None:
        fingerprint = get_dataset_fingerprint(dataset_name_for(sensor_id), data_dir=data_dir)
    with _selection_cache_lock:
        cached = _selection_cache.get(sensor_id)
    if cached is not None and cached["fingerprint"] == fingerprint:
        model, skip_fit, cached_model_name = cached["model"], True, cached["model_name"]
    else:
        model, skip_fit, cached_model_name = None, False, None

    result = run_end_to_end_pipeline(
        df,
        label_column=LABEL_COLUMN,
        feature_columns=FEATURE_COLUMNS,
        split_date=split_date,
        model=model,
        include_anomaly_detection=False,
        random_state=RANDOM_STATE,
        skip_fit=skip_fit,
    )

    if model is None:
        with _selection_cache_lock:
            _selection_cache[sensor_id] = {
                "model": result["model"],
                "model_name": result["model_name"],
                "fingerprint": fingerprint,
            }
    else:
        result["model_name"] = cached_model_name

    return result
