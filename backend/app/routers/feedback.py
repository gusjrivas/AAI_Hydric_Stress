"""Router de consulta y validación humana de alertas (spec alerting-ui,
requirement "Consulta y validación humana de alertas").
"""

from __future__ import annotations

from datetime import date as date_type
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from human_feedback.registry import load_feedback_log, save_feedback_log
from human_feedback.schema import update_feedback

from ..config import FEEDBACK_LOG_NAME, get_feedback_data_dir
from ..schemas import FeedbackListResponse, FeedbackRow, RejectRequest

router = APIRouter()


def _load_or_404(data_dir: Path) -> pd.DataFrame:
    try:
        return load_feedback_log(FEEDBACK_LOG_NAME, data_dir=data_dir)
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


@router.get("/feedback", response_model=FeedbackListResponse)
def list_feedback(data_dir: Path = Depends(get_feedback_data_dir)) -> FeedbackListResponse:
    log = _load_or_404(data_dir)
    return FeedbackListResponse(rows=[_row_to_schema(row) for _, row in log.iterrows()])


@router.post("/feedback/{fecha}/confirm", response_model=FeedbackRow)
def confirm_feedback(
    fecha: date_type, data_dir: Path = Depends(get_feedback_data_dir)
) -> FeedbackRow:
    log = _load_or_404(data_dir)
    target = _find_date_or_404(log, fecha)
    updated = update_feedback(log, fecha=target, estado_validacion="confirmada")
    save_feedback_log(FEEDBACK_LOG_NAME, updated, data_dir=data_dir)
    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)


@router.post("/feedback/{fecha}/reject", response_model=FeedbackRow)
def reject_feedback(
    fecha: date_type,
    body: RejectRequest,
    data_dir: Path = Depends(get_feedback_data_dir),
) -> FeedbackRow:
    log = _load_or_404(data_dir)
    target = _find_date_or_404(log, fecha)
    updated = update_feedback(
        log,
        fecha=target,
        estado_validacion="rechazada",
        etiqueta_corregida=body.etiqueta_corregida,
        observacion=body.observacion,
    )
    save_feedback_log(FEEDBACK_LOG_NAME, updated, data_dir=data_dir)
    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)
