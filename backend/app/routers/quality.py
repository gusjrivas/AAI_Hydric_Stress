"""Router de diagnóstico de calidad y anomalías (observabilidad de solo
lectura para la demo académica; no forma parte del pipeline operativo
de pronóstico, que corre con `include_anomaly_detection=False`).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from data_quality.anomaly_detection import detect_anomalies
from data_quality.quality_report import quality_report

from ..config import FEATURE_COLUMNS, get_dataset_data_dir
from ..dependencies import get_valid_sensor_id
from ..pipeline import load_dataset_or_raise
from ..schemas import QualityReportResponse

router = APIRouter()

_ANOMALY_METHOD = "isolation_forest"
_ANOMALY_CONTAMINATION = 0.05


@router.get("/quality/{sensor_id}", response_model=QualityReportResponse)
def get_quality_report(
    sensor_id: str = Depends(get_valid_sensor_id),
    dataset_dir: Path = Depends(get_dataset_data_dir),
) -> QualityReportResponse:
    try:
        df, _ = load_dataset_or_raise(sensor_id, data_dir=dataset_dir)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    if df.empty:
        raise HTTPException(status_code=422, detail="Dataset vacío.")

    report = quality_report(df)
    # Exploratorio bajo demanda: no se persiste ni se reutiliza en
    # `execute_configured_pipeline` (que no ajusta ningún detector).
    anomalies = detect_anomalies(df, columns=FEATURE_COLUMNS, contamination=_ANOMALY_CONTAMINATION)
    timestamps = pd.to_datetime(df["timestamp"]).sort_values()

    return QualityReportResponse(
        sensor_id=sensor_id,
        total_rows=len(df),
        period_start=timestamps.iloc[0].date(),
        period_end=timestamps.iloc[-1].date(),
        missing_pct=report["missing_pct"],
        duplicate_timestamps=[pd.Timestamp(t).date() for t in report["duplicate_timestamps"]],
        out_of_range={
            column: [pd.Timestamp(t).date() for t in dates]
            for column, dates in report["out_of_range"].items()
        },
        anomalies_detected=int(anomalies["is_anomaly"].sum()),
        anomaly_method=_ANOMALY_METHOD,
        anomaly_contamination=_ANOMALY_CONTAMINATION,
        anomaly_columns=list(FEATURE_COLUMNS),
        is_diagnostic_only=True,
        note=(
            "Diagnóstico exploratorio de calidad y anomalías, calculado bajo demanda para "
            "esta consulta. Separado del predictor operativo vigente (que corre con "
            "include_anomaly_detection=False). No modifica el dataset ni entrena el modelo "
            "de pronóstico."
        ),
    )
