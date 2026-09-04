"""Router de ingesta de lecturas de sensores (spec alerting-ui,
requirement "Ingesta de lecturas de sensores desde la interfaz de
datos, aislada por sensor"). Genérico: no distingue si el llamador es
un sensor real o un generador sintético (ADR-0007); aislado por
`sensor_id` (ADR-0008) — nunca puede escribir sobre el dataset
histórico, por construcción del esquema de nombres.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends

from data_ingestion.schema import PROVENANCE_COLUMN
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import append_reading

from ..config import get_dataset_data_dir
from ..dependencies import get_valid_sensor_id
from ..schemas import SensorReadingRequest, SensorReadingResponse

router = APIRouter()


def _normalize_to_day(timestamp: datetime) -> pd.Timestamp:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


@router.post("/sensors/{sensor_id}/readings", response_model=SensorReadingResponse)
def ingest_reading(
    reading: SensorReadingRequest,
    sensor_id: str = Depends(get_valid_sensor_id),
    data_dir: Path = Depends(get_dataset_data_dir),
) -> SensorReadingResponse:
    normalized_timestamp = _normalize_to_day(reading.timestamp)

    row = reading.model_dump(exclude={"procedencia"})
    row["timestamp"] = normalized_timestamp
    row[PROVENANCE_COLUMN] = reading.procedencia

    updated = append_reading(dataset_name_for(sensor_id), row, data_dir=data_dir)

    return SensorReadingResponse(timestamp=normalized_timestamp, filas_totales=len(updated))
