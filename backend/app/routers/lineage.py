"""Router de linaje de recalibraciones HITL (solo lectura; reutiliza
`list_recalibration_lineage` — fail-closed, nunca oculta
`LineageValidationError` ni devuelve una cadena parcial). No crea runs
ni registra modelos.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from human_feedback.lineage import LineageValidationError
from human_feedback.model_registry import list_recalibration_lineage

from ..dependencies import get_valid_sensor_id
from ..schemas import FeedbackReferenceSchema, LineageEntry, LineageResponse

router = APIRouter()


@router.get("/lineage/{sensor_id}", response_model=LineageResponse)
def get_lineage(sensor_id: str = Depends(get_valid_sensor_id)) -> LineageResponse:
    try:
        chain = list_recalibration_lineage(sensor_id)
    except LineageValidationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    entries = [
        LineageEntry(
            recalibration_id=event.recalibration_id,
            source_model_id=event.source_model_id,
            successor_model_id=event.successor_model_id,
            feedback_references=[
                FeedbackReferenceSchema(
                    sensor_id=ref.sensor_id,
                    fecha=ref.fecha,
                    model_version=ref.model_version,
                    target_timestamp=ref.target_timestamp,
                )
                for ref in event.feedback_references
            ],
            recalibrated_at=event.recalibrated_at,
            source_trained_through=event.source_trained_through,
            successor_trained_through=event.successor_trained_through,
            lineage_version=event.lineage_version,
            dataset_sha256=event.dataset_sha256,
            mlflow_model_version=event.mlflow_model_version,
        )
        for event in chain
    ]
    return LineageResponse(sensor_id=sensor_id, chain=entries)
