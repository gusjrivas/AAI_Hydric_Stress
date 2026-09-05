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
