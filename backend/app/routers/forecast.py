"""Router de ejecución de pronóstico (spec alerting-ui, requirement
"Ejecución de pronóstico desde la interfaz, por sensor").
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.registry import load_feedback_log, save_feedback_log, upsert_feedback_log
from human_feedback.schema import init_feedback_log

from ..config import get_dataset_data_dir, get_feedback_data_dir
from ..dependencies import get_valid_sensor_id
from ..pipeline import execute_configured_pipeline, load_dataset_or_raise
from ..schemas import ForecastRunResponse, Verdict

router = APIRouter()


@router.post("/forecast/{sensor_id}/run", response_model=ForecastRunResponse)
def run_forecast(
    sensor_id: str = Depends(get_valid_sensor_id),
    dataset_dir: Path = Depends(get_dataset_data_dir),
    feedback_dir: Path = Depends(get_feedback_data_dir),
) -> ForecastRunResponse:
    try:
        df, fingerprint = load_dataset_or_raise(sensor_id, data_dir=dataset_dir)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    result = execute_configured_pipeline(df, sensor_id, fingerprint, data_dir=dataset_dir)

    dates = result["test"]["timestamp"].reset_index(drop=True)
    alerts = result["alerts"].reset_index(drop=True)
    y_proba = result["y_proba"].reset_index(drop=True)

    feedback_log_name = feedback_log_name_for(sensor_id)
    try:
        existing_feedback = load_feedback_log(feedback_log_name, data_dir=feedback_dir)
        merged_feedback = upsert_feedback_log(existing_feedback, dates, alerts)
    except FileNotFoundError:
        merged_feedback = init_feedback_log(dates, alerts)
    save_feedback_log(feedback_log_name, merged_feedback, data_dir=feedback_dir)

    verdicts = [
        Verdict(fecha=d.date(), alerta=bool(a), probabilidad=float(p))
        for d, a, p in zip(dates, alerts, y_proba)
    ]
    return ForecastRunResponse(
        verdicts=verdicts,
        train_rows=len(result["train"]),
        test_rows=len(result["test"]),
    )
