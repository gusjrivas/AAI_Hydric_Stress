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


class LineageValidationError(ValueError):
    """El evento de linaje no cumple la semántica mínima exigida."""


def _require_nonempty(value, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LineageValidationError(f"{field_name} no puede estar vacío.")
    return value


def _require_valid_timestamp(value, field_name: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as error:
        raise LineageValidationError(
            f"{field_name} no es una fecha/hora válida: {value!r}."
        ) from error
    if pd.isna(timestamp):
        raise LineageValidationError(f"{field_name} no puede ser una fecha/hora nula (NaT).")
    return timestamp


@dataclass(frozen=True)
class RecalibrationLineage:
    """Evento inmutable de recalibración: qué feedback nuevo la disparó,
    qué predictor originó ese feedback (`source_model_id`) y qué
    predictor produjo la recalibración (`successor_model_id`).

    La semántica mínima (identificadores no vacíos, `source_model_id !=
    successor_model_id`, al menos una referencia de feedback, todas
    provenientes del mismo sensor y del mismo `source_model_id`, sin
    duplicados, fechas/timestamps válidos, y `successor_trained_through
    >= source_trained_through`) se valida siempre en la construcción —
    tanto al crear el evento como al reconstruirlo con `from_dict` —,
    nunca de forma opcional o diferida.
    """

    recalibration_id: str
    sensor_id: str
    source_model_id: str
    successor_model_id: str
    feedback_references: tuple[FeedbackReference, ...]
    recalibrated_at: str
    source_trained_through: str
    successor_trained_through: str
    dataset_fingerprint: str
    contract_version: int
    pipeline_version: str
    mlflow_model_version: str | None = field(default=None)

    def __post_init__(self) -> None:
        # `feedback_references` se normaliza a tupla antes de validar, de
        # modo que quede efectivamente inmutable sin importar si se
        # construyó con una lista (p. ej. desde `build_feedback_references`
        # o `from_dict`) o ya con una tupla.
        object.__setattr__(self, "feedback_references", tuple(self.feedback_references))
        self._validate()

    def _validate(self) -> None:
        _require_nonempty(self.recalibration_id, "recalibration_id")
        _require_nonempty(self.sensor_id, "sensor_id")
        _require_nonempty(self.source_model_id, "source_model_id")
        _require_nonempty(self.successor_model_id, "successor_model_id")
        _require_nonempty(self.dataset_fingerprint, "dataset_fingerprint")
        _require_nonempty(self.pipeline_version, "pipeline_version")

        if self.source_model_id == self.successor_model_id:
            raise LineageValidationError(
                "El predictor sucesor no puede coincidir con el predictor de origen."
            )

        if not self.feedback_references:
            raise LineageValidationError(
                "El evento de linaje requiere al menos una referencia de feedback."
            )
        if len(set(self.feedback_references)) != len(self.feedback_references):
            raise LineageValidationError("Las referencias de feedback no pueden repetirse.")
        for reference in self.feedback_references:
            if reference.sensor_id != self.sensor_id:
                raise LineageValidationError(
                    "Toda referencia de feedback debe pertenecer al mismo sensor del evento."
                )
            if reference.model_version != self.source_model_id:
                raise LineageValidationError(
                    "Toda referencia de feedback debe provenir del predictor de origen "
                    "(source_model_id); no puede pertenecer a otro predictor."
                )
            _require_valid_timestamp(reference.fecha, "feedback_references[].fecha")
            _require_valid_timestamp(
                reference.target_timestamp, "feedback_references[].target_timestamp"
            )

        _require_valid_timestamp(self.recalibrated_at, "recalibrated_at")
        source_through = _require_valid_timestamp(
            self.source_trained_through, "source_trained_through"
        )
        successor_through = _require_valid_timestamp(
            self.successor_trained_through, "successor_trained_through"
        )
        if successor_through < source_through:
            raise LineageValidationError(
                "successor_trained_through no puede retroceder respecto de "
                "source_trained_through."
            )

        if (
            not isinstance(self.contract_version, int)
            or isinstance(self.contract_version, bool)
            or self.contract_version < 1
        ):
            raise LineageValidationError("contract_version debe ser un entero positivo.")

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
