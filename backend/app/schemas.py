"""Modelos Pydantic de request/response (spec alerting-ui)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class Verdict(BaseModel):
    fecha: date
    alerta: bool
    probabilidad: float
    fecha_objetivo: date | None = None


class ForecastRunResponse(BaseModel):
    verdicts: list[Verdict]
    train_rows: int
    test_rows: int
    selection_warning: str | None = None


class FeedbackRow(BaseModel):
    fecha: date
    alerta_generada: int
    estado_validacion: str
    etiqueta_corregida: int | None = None
    observacion: str | None = None
    y_proba: float | None = None
    fecha_objetivo: date | None = None


class FeedbackListResponse(BaseModel):
    rows: list[FeedbackRow]


class RejectRequest(BaseModel):
    etiqueta_corregida: Literal[0, 1]
    observacion: str


class RecalibrationResponse(BaseModel):
    version: str
    n_correcciones: int
    fechas_corregidas: list[date]
    recalibration_id: str | None = None


class SensorReadingRequest(BaseModel):
    timestamp: datetime
    soil_moisture: float | None = None
    temperature: float | None = None
    relative_humidity: float | None = None
    precipitation: float | None = None
    solar_radiation: float | None = None
    wind_speed: float | None = None
    et0: float | None = None
    procedencia: Literal["real", "sintetico"] = "real"


class SensorReadingResponse(BaseModel):
    timestamp: datetime
    filas_totales: int


class QualityReportResponse(BaseModel):
    """Diagnóstico exploratorio de calidad y anomalías (solo lectura,
    separado del predictor operativo). Ver
    `openspec/specs/alerting-ui/spec.md`.
    """

    sensor_id: str
    total_rows: int
    period_start: date | None = None
    period_end: date | None = None
    missing_pct: dict[str, float]
    duplicate_timestamps: list[date]
    out_of_range: dict[str, list[date]]
    anomalies_detected: int
    anomaly_method: str
    anomaly_contamination: float
    anomaly_columns: list[str]
    is_diagnostic_only: bool
    note: str


class ActivePredictorResponse(BaseModel):
    """Identidad verificable del predictor que usaría el próximo
    pronóstico de este sensor. Campos no disponibles (sin pronóstico ni
    recalibración previa) se representan explícitamente como `None`/
    listas vacías, nunca inventados.
    """

    sensor_id: str
    origin: Literal["recalibrado", "base_configurado"] | None = None
    model_id: str | None = None
    version: str | None = None
    trained_through: str | None = None
    calibration_end: str | None = None
    horizon_days: int
    contract_version: int
    pipeline_version: str
    feature_columns: list[str]
    lags: list[int]
    rolling_windows: list[int]
    applied_feedback_count: int
    applied_feedback_dates: list[str]


class FeedbackReferenceSchema(BaseModel):
    sensor_id: str
    fecha: str
    model_version: str
    target_timestamp: str


class LineageEntry(BaseModel):
    recalibration_id: str
    source_model_id: str
    successor_model_id: str
    feedback_references: list[FeedbackReferenceSchema]
    recalibrated_at: str
    source_trained_through: str
    successor_trained_through: str
    lineage_version: int
    dataset_sha256: str | None = None
    mlflow_model_version: str | None = None


class LineageResponse(BaseModel):
    """Cadena cronológica completa de recalibraciones (A→B→C). Lista
    vacía si el sensor nunca se recalibró; un linaje corrupto o
    incompleto nunca se representa acá — el router propaga un error
    HTTP explícito en su lugar (ver `routers/lineage.py`).
    """

    sensor_id: str
    chain: list[LineageEntry]
