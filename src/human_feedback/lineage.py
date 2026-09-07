"""Linaje explícito de recalibraciones HITL (spec human-feedback,
requirement "Linaje explícito de recalibraciones HITL").

Representación tipada, agnóstica de MLflow, de la relación entre el
feedback que dispara una recalibración, el predictor que lo originó y
el predictor sucesor que produce. La persistencia concreta (artefacto
JSON dentro del run de MLflow que registra al sucesor) vive en
`human_feedback.model_registry`.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import asdict, dataclass, field

import pandas as pd

# Versión del ESQUEMA del evento de linaje — no confundir con
# `RecalibrationLineage.contract_version`, que es el `contract_version`
# del contrato de modelado (`predictive_modeling.contract.make_contract`)
# del predictor sucesor, un eje de versionado completamente distinto.
#
# v1: forma histórica (sin `dataset_sha256`); v2: exige `dataset_sha256`
# (provenance verificable del dataset usado para recalibrar).
LINEAGE_VERSION_1 = 1
LINEAGE_VERSION_2 = 2
SUPPORTED_LINEAGE_VERSIONS = (LINEAGE_VERSION_1, LINEAGE_VERSION_2)
CURRENT_LINEAGE_VERSION = LINEAGE_VERSION_2

_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def _require_valid_sha256(value, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_HEX_PATTERN.fullmatch(value):
        raise LineageValidationError(
            f"{field_name} debe ser un SHA-256 hexadecimal en minúsculas de 64 caracteres, "
            f"recibido: {value!r}."
        )
    return value


@dataclass(frozen=True)
class RecalibrationLineage:
    """Evento inmutable de recalibración: qué feedback nuevo la disparó,
    qué predictor originó ese feedback (`source_model_id`) y qué
    predictor produjo la recalibración (`successor_model_id`).

    La semántica mínima (identificadores no vacíos, `source_model_id !=
    successor_model_id`, al menos una referencia de feedback, todas
    provenientes del mismo sensor y del mismo `source_model_id`, sin
    duplicados, fechas/timestamps válidos, `successor_trained_through >=
    source_trained_through`, `lineage_version` soportada y, a partir de
    `LINEAGE_VERSION_2`, `dataset_sha256` presente y con forma válida) se
    valida siempre en la construcción — tanto al crear el evento como al
    reconstruirlo con `from_dict` —, nunca de forma opcional o diferida.
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
    lineage_version: int = field(default=LINEAGE_VERSION_1)
    dataset_sha256: str | None = field(default=None)

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

        if (
            not isinstance(self.lineage_version, int)
            or isinstance(self.lineage_version, bool)
            or self.lineage_version not in SUPPORTED_LINEAGE_VERSIONS
        ):
            raise LineageValidationError(
                f"lineage_version no soportada: {self.lineage_version!r}. "
                f"Soportadas: {SUPPORTED_LINEAGE_VERSIONS}."
            )

        if self.dataset_sha256 is not None:
            _require_valid_sha256(self.dataset_sha256, "dataset_sha256")
        elif self.lineage_version >= LINEAGE_VERSION_2:
            raise LineageValidationError(
                f"dataset_sha256 es obligatorio a partir de lineage_version={LINEAGE_VERSION_2}."
            )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data) -> RecalibrationLineage:
        """Reconstruye el evento desde un artefacto persistido, ejecutando
        la misma validación que en la construcción. Los eventos
        históricos que no incluyen `lineage_version`/`dataset_sha256`
        (persistidos antes de que existieran estos campos) se interpretan
        explícitamente como `LINEAGE_VERSION_1` — nunca se los reinterpreta
        como si cumplieran una versión posterior.

        Cualquier estructura inválida (el artefacto no es un objeto JSON,
        `feedback_references` no es una lista, una referencia no es un
        objeto o le faltan campos, faltan campos obligatorios del evento)
        se normaliza a `LineageValidationError` — nunca se propaga
        `TypeError`/`KeyError`/`AttributeError` sin envolver.
        """
        if not isinstance(data, dict):
            raise LineageValidationError(
                "El artefacto de linaje debe ser un objeto JSON (dict), recibido: "
                f"{type(data).__name__}."
            )

        raw_references = data.get("feedback_references", [])
        # Acepta lista o tupla: `to_dict()` (`dataclasses.asdict`) conserva
        # `feedback_references` como tupla cuando se usa en memoria (sin pasar
        # por JSON); un artefacto JSON deserializado siempre trae una lista.
        if not isinstance(raw_references, (list, tuple)):
            raise LineageValidationError(
                "feedback_references debe ser una lista, recibido: "
                f"{type(raw_references).__name__}."
            )
        refs = []
        for entry in raw_references:
            if not isinstance(entry, dict):
                raise LineageValidationError(
                    "Cada referencia de feedback debe ser un objeto JSON (dict), recibido: "
                    f"{type(entry).__name__}."
                )
            try:
                refs.append(FeedbackReference(**entry))
            except TypeError as error:
                raise LineageValidationError(
                    f"Referencia de feedback con campos ausentes o inesperados: {entry!r}."
                ) from error

        rest = {
            k: v
            for k, v in data.items()
            if k not in {"feedback_references", "lineage_version", "dataset_sha256"}
        }
        try:
            return cls(
                feedback_references=refs,
                lineage_version=data.get("lineage_version", LINEAGE_VERSION_1),
                dataset_sha256=data.get("dataset_sha256"),
                **rest,
            )
        except TypeError as error:
            raise LineageValidationError(
                f"El artefacto de linaje tiene campos ausentes, inesperados o de tipo "
                f"incorrecto: {error}"
            ) from error


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


def compute_dataset_sha256(path: str | os.PathLike, chunk_size: int = 1024 * 1024) -> str:
    """SHA-256 del contenido binario exacto de `path`, leído de forma
    incremental (sin cargar el archivo completo en memoria) — provenance
    verificable del dataset usado en una recalibración, distinta de
    `(mtime, size)` (`data_ingestion.storage.get_dataset_fingerprint`),
    que sigue siendo la clave económica de invalidación de caché y no
    identifica el contenido.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as dataset_file:
        for chunk in iter(lambda: dataset_file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
