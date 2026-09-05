"""Configuración del backend (fachada delgada, ADR-0003). Los nombres
de dataset, feedback log y modelo registrado ya no son globales por
deployment: se derivan por sensor (ADR-0008,
`data_ingestion.sensor_naming`).
"""

from __future__ import annotations

from pathlib import Path

from data_ingestion.storage import DEFAULT_DATA_DIR

HISTORICAL_DATASET_NAME = "melchor_romero_2024_consolidado"

FEATURE_COLUMNS = ["soil_moisture", "solar_radiation", "relative_humidity"]
LABEL_COLUMN = "soil_moisture"
RANDOM_STATE = 42
HORIZON_DAYS = 3
# Identificador de la versión metodológica del pipeline (auditoría de fuga
# temporal + validación cruzada purgada), usado como parte del contrato de
# compatibilidad de `human_feedback.model_registry` — ver
# docs/research/hu8-analisis-resultados.md, sección 11, y la auditoría de
# validación cruzada purgada posterior.
PIPELINE_VERSION = "purged_cv_v2"


def get_feedback_data_dir() -> Path:
    """Dependencia de FastAPI: directorio donde persisten los registros
    de retroalimentación. Overrideable en tests
    (`app.dependency_overrides`) para no escribir en el `data/` real
    del proyecto.
    """
    return DEFAULT_DATA_DIR


def get_dataset_data_dir() -> Path:
    """Dependencia de FastAPI: directorio donde persisten los datasets
    de sensor. Overrideable en tests (`app.dependency_overrides`) para
    no escribir en el `data/` real del proyecto.
    """
    return DEFAULT_DATA_DIR
