"""Helper compartido de ejecución del pipeline de pronóstico (spec
alerting-ui, requirements "Uso del modelo recalibrado en el próximo
pronóstico" y "Reutilización del modelo auto-seleccionado mientras el
dataset no cambie"). Usado por `/forecast/run` y `/recalibrate` para no
duplicar la lógica de elección de modelo y llamada al pipeline.
"""

from __future__ import annotations

import threading
from typing import Any

import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.storage import get_dataset_fingerprint, load_dataset
from human_feedback.model_registry import load_latest_recalibrated_model

from .config import DATASET_NAME, FEATURE_COLUMNS, LABEL_COLUMN, RANDOM_STATE

_selection_cache_lock = threading.Lock()
_selection_cache: dict[str, Any] | None = None


def load_dataset_or_raise() -> pd.DataFrame:
    """Carga el dataset consolidado configurado, o levanta
    `FileNotFoundError` con un mensaje explícito si no existe.
    """
    try:
        return load_dataset(DATASET_NAME)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"No existe el dataset '{DATASET_NAME}'.") from error


def execute_configured_pipeline(df: pd.DataFrame) -> dict[str, Any]:
    """Ejecuta el pipeline completo sobre `df` usando la configuración
    del backend: si hay un modelo recalibrado registrado en MLflow, lo
    usa sin reentrenar (`skip_fit=True`), ignorando el caché de
    selección. Si no, reutiliza el último modelo auto-seleccionado
    mientras el dataset configurado no haya cambiado (comparando su
    fingerprint); si cambió o todavía no hay ninguno cacheado, deja que
    `run_end_to_end_pipeline` seleccione automáticamente el mejor
    modelo candidato (`predictive_modeling.model_selection`) y guarda
    el resultado en el caché.
    """
    global _selection_cache

    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    recalibrated_model = load_latest_recalibrated_model()
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

    fingerprint = get_dataset_fingerprint(DATASET_NAME)
    with _selection_cache_lock:
        cached = _selection_cache
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
            _selection_cache = {
                "model": result["model"],
                "model_name": result["model_name"],
                "fingerprint": fingerprint,
            }
    else:
        # run_end_to_end_pipeline deja model_name en None cuando skip_fit=True
        # (no hubo selección en esta corrida) — se repone desde el caché para
        # que /recalibrate siga pudiendo loguear qué modelo generó el
        # pronóstico anterior, y para que el resultado sea igual de
        # informativo que el de una corrida que sí seleccionó.
        result["model_name"] = cached_model_name

    return result
