"""Router de ejecución de pronóstico (spec alerting-ui, requirement
"Ejecución de pronóstico desde la interfaz, por sensor").
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.model_registry import load_predictor_by_id, register_predictor
from human_feedback.registry import load_feedback_log, save_feedback_log
from human_feedback.schema import init_prediction_feedback

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

    try:
        result = execute_configured_pipeline(df, sensor_id, fingerprint, data_dir=dataset_dir)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    forecast = result["forecast"]
    if forecast.empty:
        raise HTTPException(status_code=422, detail="No hay historial suficiente para pronosticar.")
    if load_predictor_by_id(sensor_id, result["predictor"].model_id, result["contract"]) is None:
        register_predictor(sensor_id, result["predictor"])
    fresh = init_prediction_feedback(
        forecast,
        result["predictor"].model_id,
        result["contract"]["horizon_days"],
        result["threshold"],
    )

    feedback_log_name = feedback_log_name_for(sensor_id)
    try:
        existing_feedback = load_feedback_log(feedback_log_name, data_dir=feedback_dir)
        merged_feedback = pd.concat(
            [existing_feedback, fresh[~fresh.fecha.isin(existing_feedback.fecha)]],
            ignore_index=True,
        )
    except FileNotFoundError:
        merged_feedback = fresh
    save_feedback_log(feedback_log_name, merged_feedback, data_dir=feedback_dir)

    # One immutable issued forecast per sensor/day. Re-running does not replace
    # the prediction a human has already reviewed with another model's output.
    issued = merged_feedback[merged_feedback.fecha.isin(fresh.fecha)]
    if issued[["y_proba", "target_timestamp"]].isna().any().any():
        raise HTTPException(
            status_code=409, detail="Existe una alerta histórica sin contrato temporal completo."
        )
    verdicts = [
        Verdict(
            fecha=row.fecha.date(),
            alerta=bool(row.alerta_generada),
            probabilidad=float(row.y_proba),
            fecha_objetivo=row.target_timestamp.date(),
        )
        for row in issued.itertuples()
    ]
    return ForecastRunResponse(
        verdicts=verdicts,
        train_rows=result["predictor"].training_rows,
        test_rows=len(result["test"]),
        selection_warning=result["model_selection_warning"],
    )
