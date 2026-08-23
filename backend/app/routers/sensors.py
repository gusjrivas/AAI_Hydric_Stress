"""Router de ingesta de lecturas de sensores (spec alerting-ui,
requirement "Ingesta de lecturas de sensores desde la interfaz de
datos"). Genérico: no distingue si el llamador es un sensor real o un
generador sintético (ADR-0007).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.schema import PROVENANCE_COLUMN
from data_ingestion.storage import append_reading

from ..config import (
    DATASET_NAME,
    DATASET_NAME_EXPLICIT,
    HISTORICAL_DATASET_NAME,
    get_dataset_data_dir,
)
from ..schemas import SensorReadingRequest, SensorReadingResponse

router = APIRouter()


def _normalize_to_day(timestamp: datetime) -> pd.Timestamp:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


@router.post("/sensors/readings", response_model=SensorReadingResponse)
def ingest_reading(
    reading: SensorReadingRequest, data_dir: Path = Depends(get_dataset_data_dir)
) -> SensorReadingResponse:
    if DATASET_NAME == HISTORICAL_DATASET_NAME and not DATASET_NAME_EXPLICIT:
        raise HTTPException(
            status_code=409,
            detail=(
                "ALERTING_UI_DATASET no está configurada explícitamente: "
                f"escribir sensor readings sobre el dataset histórico "
                f"'{HISTORICAL_DATASET_NAME}' (evidencia de HU7/HU8) está "
                "bloqueado. Configurá ALERTING_UI_DATASET a un dataset en "
                "vivo separado (ej. 'sensores_en_vivo')."
            ),
        )

    normalized_timestamp = _normalize_to_day(reading.timestamp)

    row = reading.model_dump(exclude={"procedencia"})
    row["timestamp"] = normalized_timestamp
    row[PROVENANCE_COLUMN] = reading.procedencia

    updated = append_reading(DATASET_NAME, row, data_dir=data_dir)

    return SensorReadingResponse(timestamp=normalized_timestamp, filas_totales=len(updated))
