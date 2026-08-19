"""Modelos Pydantic de request/response (spec alerting-ui)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Verdict(BaseModel):
    fecha: date
    alerta: bool
    probabilidad: float


class ForecastRunResponse(BaseModel):
    verdicts: list[Verdict]
    train_rows: int
    test_rows: int


class FeedbackRow(BaseModel):
    fecha: date
    alerta_generada: int
    estado_validacion: str
    etiqueta_corregida: int | None = None
    observacion: str | None = None


class FeedbackListResponse(BaseModel):
    rows: list[FeedbackRow]


class RejectRequest(BaseModel):
    etiqueta_corregida: int
    observacion: str
