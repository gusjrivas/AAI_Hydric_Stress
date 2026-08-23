"""Configuración del backend (fachada delgada, ADR-0003). El nombre del
dataset es configurable por variable de entorno para no acoplar las
rutas a un dataset fijo cuando exista una fuente de datos en vivo.
"""

from __future__ import annotations

import os
from pathlib import Path

from data_ingestion.storage import DEFAULT_DATA_DIR

HISTORICAL_DATASET_NAME = "melchor_romero_2024_consolidado"
_DATASET_ENV_VAR = "ALERTING_UI_DATASET"
DATASET_NAME = os.environ.get(_DATASET_ENV_VAR, HISTORICAL_DATASET_NAME)
DATASET_NAME_EXPLICIT = _DATASET_ENV_VAR in os.environ
FEEDBACK_LOG_NAME = os.environ.get("ALERTING_UI_FEEDBACK_LOG", "feedback_ui")

FEATURE_COLUMNS = ["soil_moisture", "solar_radiation", "relative_humidity"]
LABEL_COLUMN = "soil_moisture"
RANDOM_STATE = 42


def get_feedback_data_dir() -> Path:
    """Dependencia de FastAPI: directorio donde persiste el registro de
    retroalimentación. Overrideable en tests (`app.dependency_overrides`)
    para no escribir en el `data/` real del proyecto.
    """
    return DEFAULT_DATA_DIR


def get_dataset_data_dir() -> Path:
    """Dependencia de FastAPI: directorio donde persiste el dataset
    configurado. Overrideable en tests (`app.dependency_overrides`)
    para no escribir en el `data/` real del proyecto.
    """
    return DEFAULT_DATA_DIR
