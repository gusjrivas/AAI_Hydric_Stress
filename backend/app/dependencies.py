"""Dependencia compartida de FastAPI para validar `sensor_id` en los
cuatro routers de `alerting-ui` (ADR-0008): un único punto de
validación, reusando `data_ingestion.sensor_naming.validate_sensor_id`.
"""

from __future__ import annotations

from fastapi import HTTPException

from data_ingestion.sensor_naming import validate_sensor_id


def get_valid_sensor_id(sensor_id: str) -> str:
    try:
        return validate_sensor_id(sensor_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
