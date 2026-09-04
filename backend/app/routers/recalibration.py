"""Router de recalibración manual del modelo (spec alerting-ui,
requirement "Disparo manual de recalibración desde la interfaz, por
sensor").
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.model_registry import register_recalibrated_model
from human_feedback.recalibration import recalibrate_model, select_recalibration_observations
from human_feedback.registry import integrate_feedback_with_predictions, load_feedback_log

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
        feedback_log = load_feedback_log(feedback_log_name_for(sensor_id), data_dir=feedback_dir)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Todavía no se corrió ningún pronóstico."
        ) from error

    try:
        df, fingerprint = load_dataset_or_raise(sensor_id, data_dir=dataset_dir)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    result = execute_configured_pipeline(df, sensor_id, fingerprint, data_dir=dataset_dir)
    feature_cols = result["feature_columns"]
    train = result["train"]
    test = result["test"]

    predictions = pd.DataFrame(
        {
            "fecha": test["timestamp"].reset_index(drop=True),
            "y_proba": result["y_proba"].reset_index(drop=True),
            "stress_label": test["stress_label"].reset_index(drop=True),
        }
    )
    integrated = integrate_feedback_with_predictions(feedback_log, predictions)
    recalibration_obs = select_recalibration_observations(integrated)

    if recalibration_obs.empty:
        raise HTTPException(status_code=400, detail="No hay correcciones pendientes de aplicar.")

    X_recal = pd.concat([train[feature_cols], test[feature_cols]], ignore_index=True)
    y_recal = pd.concat([train["stress_label"], test["stress_label"]], ignore_index=True)
    dates_recal = pd.concat([train["timestamp"], test["timestamp"]], ignore_index=True)

    recalibrated_model, _ = recalibrate_model(
        result["model"], X_recal, y_recal, dates_recal, recalibration_obs
    )

    version = register_recalibrated_model(
        sensor_id,
        recalibrated_model,
        params={
            "n_correcciones": len(recalibration_obs),
            "model_name_previo": result["model_name"] or "modelo_recalibrado_previo",
        },
        metrics={"n_filas_entrenamiento": len(X_recal)},
    )

    return RecalibrationResponse(
        version=version,
        n_correcciones=len(recalibration_obs),
        fechas_corregidas=[d.date() for d in recalibration_obs["fecha"]],
    )
