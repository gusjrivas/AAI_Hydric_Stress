"""Manual, temporally auditable recalibration through the HU5 core."""

from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from data_ingestion.sensor_naming import feedback_log_name_for
from human_feedback.lineage import (
    CURRENT_LINEAGE_VERSION,
    RecalibrationLineage,
    build_feedback_references,
)
from human_feedback.model_registry import (
    load_latest_recalibrated_model,
    register_recalibrated_model,
)
from human_feedback.recalibration import recalibrate_predictor
from human_feedback.registry import load_feedback_log

from ..config import get_dataset_data_dir, get_feedback_data_dir
from ..dependencies import get_valid_sensor_id
from ..pipeline import (
    configured_contract,
    execute_configured_pipeline,
    load_dataset_snapshot_or_raise,
)
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
        # `snapshot.dataframe` y `snapshot.dataset_sha256` provienen de la
        # MISMA captura de bytes del dataset (ver `DatasetSnapshot`) — nunca
        # de dos lecturas independientes del archivo, que podrían ver
        # contenido distinto entre sí si el archivo cambia entre medio.
        snapshot = load_dataset_snapshot_or_raise(sensor_id, data_dir=dataset_dir)
        df = snapshot.dataframe
        fingerprint = snapshot.cache_fingerprint
        dataset_sha256 = snapshot.dataset_sha256
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        # `load_dataset_snapshot_or_raise` aborta así si no puede garantizar
        # una captura estable (el archivo cambió mientras se leía) — nunca
        # se llega a registrar un sucesor con esa instantánea inconsistente.
        raise HTTPException(status_code=400, detail=str(error)) from error
    try:
        latest = load_latest_recalibrated_model(sensor_id, expected_contract=configured_contract())
        # El predictor vigente es siempre `latest` (si ya se recalibró alguna
        # vez); elegir el primer `model_version` del log sería arbitrario en
        # cuanto el log acumula feedback de más de un ciclo HITL.
        model_id = (
            latest.model_id
            if latest is not None
            else (log["model_version"].dropna().iloc[0] if "model_version" in log else None)
        )
        applied = (
            {str(pd.Timestamp(value)) for value in (latest.applied_feedback or {})}
            if latest is not None
            else set()
        )
        correction_dates = {
            str(pd.Timestamp(value))
            for value in log.loc[
                (log.estado_validacion == "rechazada") & log.etiqueta_corregida.notna(), "fecha"
            ]
        }
        already_applied = latest is not None and correction_dates.issubset(applied)
        predictor_model_id = None if already_applied else model_id
        result = execute_configured_pipeline(
            df, sensor_id, fingerprint, data_dir=dataset_dir, predictor_model_id=predictor_model_id
        )
        source_predictor = result["predictor"]
        predictor, dates, count = recalibrate_predictor(source_predictor, df, log)
        lineage = RecalibrationLineage(
            recalibration_id=uuid4().hex,
            sensor_id=sensor_id,
            source_model_id=source_predictor.model_id,
            successor_model_id=predictor.model_id,
            feedback_references=build_feedback_references(sensor_id, log, dates),
            recalibrated_at=str(pd.Timestamp.now(tz="UTC").tz_localize(None)),
            source_trained_through=source_predictor.trained_through,
            successor_trained_through=predictor.trained_through,
            dataset_fingerprint=str(fingerprint),
            contract_version=predictor.contract["contract_version"],
            pipeline_version=predictor.contract["pipeline_version"],
            lineage_version=CURRENT_LINEAGE_VERSION,
            dataset_sha256=dataset_sha256,
        )
        version = register_recalibrated_model(
            sensor_id,
            predictor,
            params={"n_correcciones": len(dates)},
            metrics={"n_filas_entrenamiento": count},
            lineage=lineage,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return RecalibrationResponse(
        version=version,
        n_correcciones=len(dates),
        fechas_corregidas=[d.date() for d in dates],
        recalibration_id=lineage.recalibration_id,
    )
