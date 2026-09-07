"""Router de observabilidad del predictor activo (solo lectura; nunca
carga ni entrena un modelo distinto del que usaría
`execute_configured_pipeline` en el próximo pronóstico).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from human_feedback.model_registry import (
    ModelContractMismatch,
    get_latest_recalibrated_version,
    load_latest_issued_predictor_metadata,
    load_latest_recalibrated_model,
)

from ..dependencies import get_valid_sensor_id
from ..pipeline import configured_contract
from ..schemas import ActivePredictorResponse

router = APIRouter()


@router.get("/models/{sensor_id}/active", response_model=ActivePredictorResponse)
def get_active_predictor(
    sensor_id: str = Depends(get_valid_sensor_id),
) -> ActivePredictorResponse:
    contract = configured_contract()
    base_fields = {
        "sensor_id": sensor_id,
        "horizon_days": contract["horizon_days"],
        "contract_version": contract["contract_version"],
        "pipeline_version": contract["pipeline_version"],
        "feature_columns": contract["raw_input_features"],
        "lags": contract["lags"],
        "rolling_windows": contract["rolling_windows"],
    }

    try:
        recalibrated = load_latest_recalibrated_model(sensor_id, expected_contract=contract)
    except ModelContractMismatch as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    if recalibrated is not None:
        applied = sorted(str(key) for key in (recalibrated.applied_feedback or {}))
        return ActivePredictorResponse(
            **base_fields,
            origin="recalibrado",
            model_id=recalibrated.model_id,
            version=get_latest_recalibrated_version(sensor_id),
            trained_through=recalibrated.trained_through,
            calibration_end=recalibrated.calibration_end,
            applied_feedback_count=len(applied),
            applied_feedback_dates=applied,
        )

    metadata = load_latest_issued_predictor_metadata(sensor_id)
    if metadata is not None:
        applied = sorted(str(key) for key in (metadata.get("applied_feedback") or {}))
        return ActivePredictorResponse(
            **base_fields,
            origin="base_configurado",
            model_id=metadata.get("model_id"),
            version=metadata.get("issued_model_version"),
            trained_through=metadata.get("trained_through"),
            calibration_end=metadata.get("calibration_end"),
            applied_feedback_count=len(applied),
            applied_feedback_dates=applied,
        )

    # Todavía no se corrió ningún pronóstico ni recalibración para este
    # sensor: no hay ningún predictor identificable — campos explícitos,
    # nunca inventados.
    return ActivePredictorResponse(
        **base_fields,
        origin=None,
        model_id=None,
        version=None,
        trained_through=None,
        calibration_end=None,
        applied_feedback_count=0,
        applied_feedback_dates=[],
    )
