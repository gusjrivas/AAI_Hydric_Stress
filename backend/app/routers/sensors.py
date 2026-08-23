"""Router de ingesta de lecturas de sensores (spec alerting-ui,
requirement "Ingesta de lecturas de sensores desde la interfaz de
datos"). Genérico: no distingue si el llamador es un sensor real o un
generador sintético (ADR-0007).
"""

from __future__ import annotations

from pathlib import Path

from data_ingestion.schema import PROVENANCE_COLUMN
from data_ingestion.storage import append_reading
from fastapi import APIRouter, Depends

from ..config import DATASET_NAME, get_dataset_data_dir
from ..schemas import SensorReadingRequest, SensorReadingResponse

router = APIRouter()


@router.post("/sensors/readings", response_model=SensorReadingResponse)
def ingest_reading(
    reading: SensorReadingRequest, data_dir: Path = Depends(get_dataset_data_dir)
) -> SensorReadingResponse:
    row = reading.model_dump(exclude={"procedencia"})
    row[PROVENANCE_COLUMN] = reading.procedencia

    updated = append_reading(DATASET_NAME, row, data_dir=data_dir)

    return SensorReadingResponse(timestamp=reading.timestamp, filas_totales=len(updated))
