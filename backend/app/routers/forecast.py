"""Router de ejecución de pronóstico (spec alerting-ui, requirement
"Ejecución de pronóstico desde la interfaz").
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.storage import load_dataset
from human_feedback.registry import load_feedback_log, save_feedback_log, upsert_feedback_log
from human_feedback.schema import init_feedback_log
from predictive_modeling.models import build_candidate_models

from ..config import (
    DATASET_NAME,
    FEATURE_COLUMNS,
    FEEDBACK_LOG_NAME,
    LABEL_COLUMN,
    RANDOM_STATE,
    get_feedback_data_dir,
)
from ..schemas import ForecastRunResponse, Verdict

router = APIRouter()


@router.post("/forecast/run", response_model=ForecastRunResponse)
def run_forecast(data_dir: Path = Depends(get_feedback_data_dir)) -> ForecastRunResponse:
    df = load_dataset(DATASET_NAME)
    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    model = build_candidate_models(random_state=RANDOM_STATE)["random_forest"]
    result = run_end_to_end_pipeline(
        df,
        label_column=LABEL_COLUMN,
        feature_columns=FEATURE_COLUMNS,
        split_date=split_date,
        model=model,
        include_anomaly_detection=False,
        random_state=RANDOM_STATE,
    )

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
