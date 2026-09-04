"""Convención de nombres de recursos por sensor (ADR-0008): deriva, a
partir de un `sensor_id` validado, el dataset, el feedback log y el
modelo registrado propios de ese sensor, de forma que dos sensores
nunca colisionen entre sí ni con el dataset histórico de investigación
(`melchor_romero_2024_consolidado`, que nunca empieza con `sensor__`).
"""

from __future__ import annotations

import re

_SENSOR_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_sensor_id(sensor_id: str) -> str:
    """Devuelve `sensor_id` sin modificar si cumple
    `^[a-zA-Z0-9_-]{1,64}$`; levanta `ValueError` si no.
    """
    if not _SENSOR_ID_PATTERN.match(sensor_id):
        raise ValueError(
            f"sensor_id inválido: '{sensor_id}'. Debe cumplir "
            f"'{_SENSOR_ID_PATTERN.pattern}' (alfanumérico, '-' y '_', 1 a 64 caracteres)."
        )
    return sensor_id


def dataset_name_for(sensor_id: str) -> str:
    """Nombre del dataset propio de `sensor_id`."""
    return f"sensor__{validate_sensor_id(sensor_id)}"


def feedback_log_name_for(sensor_id: str) -> str:
    """Nombre del registro de retroalimentación propio de `sensor_id`."""
    return f"feedback__{validate_sensor_id(sensor_id)}"


def registered_model_name_for(sensor_id: str) -> str:
    """Nombre del modelo registrado en MLflow propio de `sensor_id`."""
    return f"alerting_ui_recalibrated_model__{validate_sensor_id(sensor_id)}"
