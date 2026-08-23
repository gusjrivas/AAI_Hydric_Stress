"""Router de ejecución de pronóstico (spec alerting-ui, requirement
"Ejecución de pronóstico desde la interfaz").
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from human_feedback.registry import load_feedback_log, save_feedback_log, upsert_feedback_log
from human_feedback.schema import init_feedback_log

from ..config import FEEDBACK_LOG_NAME, get_feedback_data_dir
from ..pipeline import execute_configured_pipeline, load_dataset_or_raise
from ..schemas import ForecastRunResponse, Verdict

router = APIRouter()


@router.post("/forecast/run", response_model=ForecastRunResponse)
def run_forecast(data_dir: Path = Depends(get_feedback_data_dir)) -> ForecastRunResponse:
    try:
        df, fingerprint = load_dataset_or_raise()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    result = execute_configured_pipeline(df, fingerprint)

    dates = result["test"]["timestamp"].reset_index(drop=True)
    alerts = result["alerts"].reset_index(drop=True)
    y_proba = result["y_proba"].reset_index(drop=True)

    try:
        existing_feedback = load_feedback_log(FEEDBACK_LOG_NAME, data_dir=data_dir)
        merged_feedback = upsert_feedback_log(existing_feedback, dates, alerts)
    except FileNotFoundError:
        merged_feedback = init_feedback_log(dates, alerts)
    save_feedback_log(FEEDBACK_LOG_NAME, merged_feedback, data_dir=data_dir)

    verdicts = [
        Verdict(fecha=d.date(), alerta=bool(a), probabilidad=float(p))
        for d, a, p in zip(dates, alerts, y_proba)
    ]
    return ForecastRunResponse(
        verdicts=verdicts,
        train_rows=len(result["train"]),
        test_rows=len(result["test"]),
    )
