"""Linaje explícito de recalibraciones HITL (spec human-feedback,
requirement "Linaje explícito de recalibraciones HITL").

Representación tipada, agnóstica de MLflow, de la relación entre el
feedback que dispara una recalibración, el predictor que lo originó y
el predictor sucesor que produce. La persistencia concreta (artefacto
JSON dentro del run de MLflow que registra al sucesor) vive en
`human_feedback.model_registry`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd


@dataclass(frozen=True)
class FeedbackReference:
    """Clave compuesta que identifica, sin ambigüedad, una fila de
    `feedback_log` bajo el contrato operativo vigente (una alerta
    emitida por sensor y fecha): `sensor_id` + `fecha` ya determinan la
    fila; `model_version` (el `model_id` del predictor que la emitió) y
    `target_timestamp` se preservan como procedencia verificable,
    replicando las mismas columnas que `recalibrate_predictor` exige
    como procedencia temporal completa.
    """

    sensor_id: str
    fecha: str
    model_version: str
    target_timestamp: str


@dataclass(frozen=True)
class RecalibrationLineage:
    """Evento inmutable de recalibración: qué feedback nuevo la disparó,
    qué predictor originó ese feedback (`source_model_id`) y qué
    predictor produjo la recalibración (`successor_model_id`).
    """

    recalibration_id: str
    sensor_id: str
    source_model_id: str
    successor_model_id: str
    feedback_references: list[FeedbackReference]
    recalibrated_at: str
    source_trained_through: str
    successor_trained_through: str
    dataset_fingerprint: str
    contract_version: int
    pipeline_version: str
    mlflow_model_version: str | None = field(default=None)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> RecalibrationLineage:
        refs = [FeedbackReference(**ref) for ref in data.get("feedback_references", [])]
        rest = {k: v for k, v in data.items() if k != "feedback_references"}
        return cls(feedback_references=refs, **rest)


def build_feedback_references(
    sensor_id: str, feedback_log: pd.DataFrame, dates
) -> list[FeedbackReference]:
    """Construye las referencias de procedencia para exactamente las
    fechas en `dates` (las correcciones nuevas/pendientes efectivamente
    incorporadas por `recalibrate_predictor`, no todo el historial).
    """
    references = []
    for fecha in dates:
        row = feedback_log.loc[feedback_log.fecha == pd.Timestamp(fecha)].iloc[0]
        references.append(
            FeedbackReference(
                sensor_id=sensor_id,
                fecha=str(pd.Timestamp(fecha)),
                model_version=str(row.model_version),
                target_timestamp=str(pd.Timestamp(row.target_timestamp)),
            )
        )
    return references
