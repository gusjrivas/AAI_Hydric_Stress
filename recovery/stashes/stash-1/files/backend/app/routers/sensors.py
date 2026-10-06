"""Router de ingesta de lecturas de sensores (spec alerting-ui,
requirement "Ingesta de lecturas de sensores desde la interfaz de
datos, aislada por sensor"). Genérico: no distingue si el llamador es
un sensor real o un generador sintético (ADR-0007); aislado por
`sensor_id` (ADR-0008) — nunca puede escribir sobre el dataset
histórico, por construcción del esquema de nombres.
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from data_ingestion.schema import PROVENANCE_COLUMN
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import append_reading

from ..config import get_dataset_data_dir
from ..dependencies import get_valid_sensor_id
from ..pipeline import load_dataset_snapshot_or_raise
from ..schemas import (
    SensorHistoryResponse,
    SensorHistoryRow,
    SensorReadingRequest,
    SensorReadingResponse,
)

router = APIRouter()


@router.get("/sensors/{sensor_id}/history", response_model=SensorHistoryResponse)
def sensor_history(
    sensor_id: str = Depends(get_valid_sensor_id),
    days: int = Query(default=30, ge=1, le=366),
    data_dir: Path = Depends(get_dataset_data_dir),
) -> SensorHistoryResponse:
    """Lecturas almacenadas, sin imputar, entrenar ni modificar el dataset."""
    try:
        df = load_dataset_snapshot_or_raise(sensor_id, data_dir).dataframe
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Todavía no hay mediciones.") from error
    except ValueError as error:
        raise HTTPException(
            status_code=409, detail="Los datos cambiaron; volvé a consultar."
        ) from error

    if df.empty:
        return SensorHistoryResponse(
            sensor_id=sensor_id, period_start=None, period_end=None, rows=[]
        )

    dates = pd.to_datetime(df["timestamp"])
    end = dates.max().normalize()
    start = end - pd.Timedelta(days=days - 1)
    selected = df.loc[(dates >= start) & (dates <= end)].sort_values("timestamp")

    def finite_or_none(value):
        if pd.isna(value):
            return None
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None

    rows = [
        SensorHistoryRow(
            fecha=pd.Timestamp(row["timestamp"]).date(),
            soil_moisture=finite_or_none(row.get("soil_moisture")),
            temperature=finite_or_none(row.get("temperature")),
            precipitation=finite_or_none(row.get("precipitation")),
            origen=str(row.get("origen", "desconocido")),
        )
        for _, row in selected.iterrows()
    ]
    return SensorHistoryResponse(
        sensor_id=sensor_id, period_start=start.date(), period_end=end.date(), rows=rows
    )


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
