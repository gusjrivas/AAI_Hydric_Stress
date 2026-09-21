"""Versioned metadata contracts for independent operational horizons.

The contract represents either an unfitted plan or an already trained bundle.
It does not fit, load, register, or persist a model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import numpy as np

from predictive_modeling.operational_preparation import SUPPORTED_HORIZONS, TemporalCutPlan

OPERATIONAL_CONTRACT_VERSION = "producer_daily_h123_v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class HorizonContractMismatch(ValueError):
    """Horizon contracts cannot form one compatible +1/+2/+3 family."""


def _non_empty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} debe ser texto no vacío.")


@dataclass(frozen=True)
class VariableMetadata:
    name: str
    unit: str

    def __post_init__(self) -> None:
        _non_empty(self.name, "name")
        _non_empty(self.unit, "unit")


@dataclass(frozen=True)
class ArtifactIdentity:
    """Identity metadata for an artifact that actually exists."""

    version: str
    sha256: str
    horizon_days: int
    contract_version: str = OPERATIONAL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _non_empty(self.version, "version")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 debe contener 64 caracteres hexadecimales minúsculos.")
        if (
            isinstance(self.horizon_days, bool)
            or not isinstance(self.horizon_days, int)
            or self.horizon_days not in SUPPORTED_HORIZONS
        ):
            raise ValueError("horizon_days de la identidad debe ser 1, 2 o 3.")
        if self.contract_version != OPERATIONAL_CONTRACT_VERSION:
            raise ValueError("Versión de contrato operacional no soportada.")


@dataclass(frozen=True)
class HorizonContract:
    horizon_days: int
    sensor_id: str
    data_snapshot_sha256: str
    imputation: str
    variables: tuple[VariableMetadata, ...]
    event_variable: str
    event_threshold: float
    event_unit: str
    temporal_cuts: TemporalCutPlan
    artifact_state: str = "plan"
    contract_version: str = OPERATIONAL_CONTRACT_VERSION
    event_comparison: str = "lt"
    model_identity: ArtifactIdentity | None = None
    calibrator_identity: ArtifactIdentity | None = None
    trained_through: date | None = None
    calibrated_through: date | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.horizon_days, bool)
            or not isinstance(self.horizon_days, int)
            or self.horizon_days not in SUPPORTED_HORIZONS
        ):
            raise ValueError("horizon_days debe ser 1, 2 o 3.")
        if self.contract_version != OPERATIONAL_CONTRACT_VERSION:
            raise ValueError("Versión de contrato operacional no soportada.")
        if self.artifact_state not in {"plan", "trained_bundle"}:
            raise ValueError("artifact_state debe ser plan o trained_bundle.")
        _non_empty(self.sensor_id, "sensor_id")
        _non_empty(self.imputation, "imputation")
        if not _SHA256.fullmatch(self.data_snapshot_sha256):
            raise ValueError("data_snapshot_sha256 debe ser un SHA-256 hexadecimal minusculo.")
        if not isinstance(self.variables, tuple) or not all(
            isinstance(item, VariableMetadata) for item in self.variables
        ):
            raise ValueError("variables debe ser una tupla de VariableMetadata.")
        if not self.variables or len({item.name for item in self.variables}) != len(self.variables):
            raise ValueError("variables debe ser no vacío y no contener nombres duplicados.")
        _non_empty(self.event_variable, "event_variable")
        _non_empty(self.event_unit, "event_unit")
        by_name = {item.name: item.unit for item in self.variables}
        if by_name.get(self.event_variable) != self.event_unit:
            raise ValueError(
                "La variable del evento y su unidad deben estar declaradas en variables."
            )
        if self.event_comparison != "lt":
            raise ValueError("El contrato solo admite la comparación de evento lt.")
        if (
            isinstance(self.event_threshold, bool)
            or not isinstance(self.event_threshold, int | float | np.integer | np.floating)
            or not np.isfinite(self.event_threshold)
        ):
            raise ValueError("event_threshold debe ser un valor finito congelado.")

        for field, value in (
            ("trained_through", self.trained_through),
            ("calibrated_through", self.calibrated_through),
        ):
            if value is not None and type(value) is not date:
                raise ValueError(f"{field} debe ser una fecha diaria sin hora.")

        identities = (self.model_identity, self.calibrator_identity)
        if any(
            identity is not None
            and (
                identity.horizon_days != self.horizon_days
                or identity.contract_version != self.contract_version
            )
            for identity in identities
        ):
            raise ValueError("La identidad de artefacto no coincide con horizonte/contrato.")

        if self.artifact_state == "plan":
            if any(identity is not None for identity in identities) or any(
                value is not None for value in (self.trained_through, self.calibrated_through)
            ):
                raise ValueError(
                    "Un plan no ajustado no puede declarar artefactos ni fechas de ajuste."
                )
        else:
            if self.model_identity is None or self.trained_through is None:
                raise ValueError(
                    "Un trained_bundle requiere identidad de modelo y trained_through."
                )
            if (self.calibrator_identity is None) != (self.calibrated_through is None):
                raise ValueError(
                    "Identidad y fecha del calibrador deben estar ambas presentes o ambas ausentes."
                )

        if self.trained_through is not None and not (
            self.temporal_cuts.train.start <= self.trained_through <= self.temporal_cuts.train.end
        ):
            raise ValueError("trained_through debe quedar dentro del rango train declarado.")
        if self.calibrated_through is not None and not (
            self.temporal_cuts.calibration.start
            <= self.calibrated_through
            <= self.temporal_cuts.calibration.end
        ):
            raise ValueError(
                "calibrated_through debe quedar dentro del rango calibration declarado."
            )

    def to_dict(self) -> dict[str, object]:
        common = {
            "sensor_id": self.sensor_id,
            "data_snapshot_sha256": self.data_snapshot_sha256,
            "imputation": self.imputation,
        }

        def artifact(value: ArtifactIdentity | None) -> dict[str, object] | None:
            if value is None:
                return None
            return {
                "version": value.version,
                "sha256": value.sha256,
                "horizon_days": value.horizon_days,
                "contract_version": value.contract_version,
            }

        return {
            **common,
            "horizon_days": self.horizon_days,
            "contract_version": self.contract_version,
            "artifact_state": self.artifact_state,
            "variables": [{"name": item.name, "unit": item.unit} for item in self.variables],
            "event": {
                "variable": self.event_variable,
                "threshold": float(self.event_threshold),
                "unit": self.event_unit,
                "comparison": self.event_comparison,
            },
            "temporal_cuts": self.temporal_cuts.to_dict(),
            "model_identity": artifact(self.model_identity),
            "calibrator_identity": artifact(self.calibrator_identity),
            "trained_through": (
                self.trained_through.isoformat() if self.trained_through is not None else None
            ),
            "calibrated_through": (
                self.calibrated_through.isoformat() if self.calibrated_through is not None else None
            ),
        }


def validate_horizon_contract_family(contracts: tuple[HorizonContract, ...]) -> None:
    """Require exactly one compatible, independently identified contract per horizon."""

    by_horizon = {contract.horizon_days: contract for contract in contracts}
    if len(contracts) != 3 or set(by_horizon) != set(SUPPORTED_HORIZONS):
        raise HorizonContractMismatch("Se requieren contratos únicos para h=1, h=2 y h=3.")
    reference = by_horizon[1]
    shared_fields = (
        "sensor_id",
        "data_snapshot_sha256",
        "imputation",
        "contract_version",
        "artifact_state",
        "variables",
        "event_variable",
        "event_threshold",
        "event_unit",
        "event_comparison",
        "temporal_cuts",
    )
    for horizon in SUPPORTED_HORIZONS[1:]:
        candidate = by_horizon[horizon]
        changed = [
            field
            for field in shared_fields
            if getattr(candidate, field) != getattr(reference, field)
        ]
        if changed:
            raise HorizonContractMismatch(
                f"Contrato h={horizon} incompatible en campos compartidos: {changed}"
            )

    model_ids = [
        contract.model_identity.sha256
        for contract in contracts
        if contract.model_identity is not None
    ]
    calibrator_ids = [
        contract.calibrator_identity.sha256
        for contract in contracts
        if contract.calibrator_identity is not None
    ]
    if len(model_ids) != len(set(model_ids)):
        raise HorizonContractMismatch(
            "Cada horizonte entrenado requiere identidad de modelo propia."
        )
    if len(calibrator_ids) != len(set(calibrator_ids)):
        raise HorizonContractMismatch("Cada calibrador existente requiere identidad propia.")
