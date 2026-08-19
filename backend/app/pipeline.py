"""Helper compartido de ejecución del pipeline de pronóstico (spec
alerting-ui, requirement "Uso del modelo recalibrado en el próximo
pronóstico"). Usado por `/forecast/run` y `/recalibrate` para no
duplicar la lógica de elección de modelo y llamada al pipeline.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.storage import load_dataset
from human_feedback.model_registry import load_latest_recalibrated_model
from predictive_modeling.models import build_candidate_models

from .config import DATASET_NAME, FEATURE_COLUMNS, LABEL_COLUMN, RANDOM_STATE


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
    usa sin reentrenar (`skip_fit=True`); si no, entrena un Random
    Forest nuevo, igual que antes de que existiera la recalibración.
    """
    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    recalibrated_model = load_latest_recalibrated_model()
    if recalibrated_model is not None:
        model = recalibrated_model
        skip_fit = True
    else:
        model = build_candidate_models(random_state=RANDOM_STATE)["random_forest"]
        skip_fit = False

    return run_end_to_end_pipeline(
        df,
        label_column=LABEL_COLUMN,
        feature_columns=FEATURE_COLUMNS,
        split_date=split_date,
        model=model,
        include_anomaly_detection=False,
        random_state=RANDOM_STATE,
        skip_fit=skip_fit,
    )
