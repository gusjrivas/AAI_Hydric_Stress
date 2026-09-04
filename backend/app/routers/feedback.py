"""Router de consulta y validación humana de alertas (spec alerting-ui,
requirement "Consulta y validación humana de alertas, por sensor").
"""

from __future__ import annotations

from datetime import date as date_type
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.registry import load_feedback_log, save_feedback_log
from human_feedback.schema import update_feedback

from ..config import get_feedback_data_dir
from ..dependencies import get_valid_sensor_id
from ..schemas import FeedbackListResponse, FeedbackRow, RejectRequest

router = APIRouter()


def _load_or_404(sensor_id: str, data_dir: Path) -> pd.DataFrame:
    try:
        return load_feedback_log(feedback_log_name_for(sensor_id), data_dir=data_dir)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Todavía no se corrió ningún pronóstico."
        ) from error


def _find_date_or_404(log: pd.DataFrame, fecha: date_type) -> pd.Timestamp:
    target = pd.Timestamp(fecha)
    if not (log["fecha"] == target).any():
        raise HTTPException(status_code=404, detail=f"No hay una alerta para la fecha {fecha}.")
    return target


def _row_to_schema(row: pd.Series) -> FeedbackRow:
    etiqueta = row["etiqueta_corregida"]
    observacion = row["observacion"]
    return FeedbackRow(
        fecha=row["fecha"].date(),
        alerta_generada=int(row["alerta_generada"]),
        estado_validacion=row["estado_validacion"],
        etiqueta_corregida=None if pd.isna(etiqueta) else int(etiqueta),
        observacion=None if observacion is None else observacion,
    )


@router.get("/feedback/{sensor_id}", response_model=FeedbackListResponse)
def list_feedback(
    sensor_id: str = Depends(get_valid_sensor_id), data_dir: Path = Depends(get_feedback_data_dir)
) -> FeedbackListResponse:
    log = _load_or_404(sensor_id, data_dir)
    return FeedbackListResponse(rows=[_row_to_schema(row) for _, row in log.iterrows()])


@router.post("/feedback/{sensor_id}/{fecha}/confirm", response_model=FeedbackRow)
def confirm_feedback(
    fecha: date_type,
    sensor_id: str = Depends(get_valid_sensor_id),
    data_dir: Path = Depends(get_feedback_data_dir),
) -> FeedbackRow:
    log = _load_or_404(sensor_id, data_dir)
    target = _find_date_or_404(log, fecha)
    updated = update_feedback(log, fecha=target, estado_validacion="confirmada")
    save_feedback_log(feedback_log_name_for(sensor_id), updated, data_dir=data_dir)
    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)


@router.post("/feedback/{sensor_id}/{fecha}/reject", response_model=FeedbackRow)
def reject_feedback(
    fecha: date_type,
    body: RejectRequest,
    sensor_id: str = Depends(get_valid_sensor_id),
    data_dir: Path = Depends(get_feedback_data_dir),
) -> FeedbackRow:
    log = _load_or_404(sensor_id, data_dir)
    target = _find_date_or_404(log, fecha)
    updated = update_feedback(
        log,
        fecha=target,
        estado_validacion="rechazada",
        etiqueta_corregida=body.etiqueta_corregida,
        observacion=body.observacion,
    )
    save_feedback_log(feedback_log_name_for(sensor_id), updated, data_dir=data_dir)
    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)
