"""Manual, temporally auditable recalibration through the HU5 core."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.model_registry import register_recalibrated_model
from human_feedback.recalibration import recalibrate_predictor
from human_feedback.registry import load_feedback_log

from ..config import get_dataset_data_dir, get_feedback_data_dir
from ..dependencies import get_valid_sensor_id
from ..pipeline import execute_configured_pipeline, load_dataset_or_raise
from ..schemas import RecalibrationResponse

router = APIRouter()


@router.post("/recalibrate/{sensor_id}", response_model=RecalibrationResponse)
def recalibrate(
    sensor_id: str = Depends(get_valid_sensor_id),
    dataset_dir: Path = Depends(get_dataset_data_dir),
    feedback_dir: Path = Depends(get_feedback_data_dir),
) -> RecalibrationResponse:
    try:
        log = load_feedback_log(feedback_log_name_for(sensor_id), data_dir=feedback_dir)
        df, fingerprint = load_dataset_or_raise(sensor_id, data_dir=dataset_dir)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        result = execute_configured_pipeline(df, sensor_id, fingerprint, data_dir=dataset_dir)
        predictor, dates, count = recalibrate_predictor(result["predictor"], df, log)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    version = register_recalibrated_model(
        sensor_id,
        predictor,
        params={"n_correcciones": len(dates)},
        metrics={"n_filas_entrenamiento": count},
    )
    return RecalibrationResponse(
        version=version, n_correcciones=len(dates), fechas_corregidas=[d.date() for d in dates]
    )
