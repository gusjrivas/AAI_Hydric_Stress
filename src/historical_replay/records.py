"""Typed, immutable records of already-archived v3 predictions (spec
`historical-replay`, requirements RH-01, RH-06, RH-11).

Builds `HistoricalPredictionRecord` from the raw rows of a run's
`predictions.json`, without recalculating anything: `y_true`/`y_proba`/
`y_pred`/baselines are copied verbatim from the archived artifact, only
validated and normalized for comparison (never rewritten on disk — this
module never touches the original JSON files).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from types import MappingProxyType

ADMITTED_CLASSES = (0, 1)
_IDENTITY_FIELDS = ("experiment_id", "run_id", "config_name", "seed")
_REQUIRED_ROW_FIELDS = (
    "timestamp",
    "target_timestamp",
    "target_observed",
    "y_proba",
    "y_pred",
)


class MalformedRowError(ValueError):
    """A row is missing a field this module requires to interpret it."""


class MissingIdentityError(ValueError):
    """A required identity field is absent from both the row and the
    authorized run context — never silently replaced by the string
    `"None"`."""


class ForeignIdentityError(ValueError):
    """A row declares an identity field that conflicts with the run this
    build was authorized for; it never silently overrides it."""


class DuplicateIdentityError(ValueError):
    """Raised when two rows share the full prediction identity (RH-01),
    including when two equivalent date representations normalize to the
    same identity."""


class HorizonMismatchError(ValueError):
    """Raised when a row's target_timestamp does not match the declared
    horizon."""


class InvalidHorizonError(ValueError):
    """`horizon_days` itself is not a positive integer."""


class InvalidBooleanError(ValueError):
    """`target_observed` is not a real Python `bool` (rejects `"true"`,
    `1`, etc., which would silently coerce via truthiness)."""


class InvalidProbabilityError(ValueError):
    """`y_proba` is not a finite number in `[0, 1]`."""


class InvalidClassError(ValueError):
    """`y_pred` (or `y_true`, when present) is outside {0, 1}."""


class TargetObservedCoherenceError(ValueError):
    """`target_observed` and the presence of `y_true` are inconsistent."""


@dataclass(frozen=True)
class PredictionIdentity:
    """Stable identity of a historical prediction. `target_timestamp` is
    deliberately excluded: it is a derived field (`timestamp_origen +
    horizon_days`), not an independent identity dimension (design.md §4.1).
    `timestamp_origen` is a normalized `date`, not a raw string, so that two
    equivalent textual representations of the same day are recognized as
    the same identity."""

    experiment_id: str
    run_id: str
    config_name: str
    seed: int
    timestamp_origen: date


@dataclass(frozen=True)
class HistoricalPredictionRecord:
    """Immutable evidence for one archived prediction. Never mutated by the
    replay clock; only its projection (`projection.py`) changes with it.
    `baselines` is a `MappingProxyType`: a frozen dataclass does not make a
    nested plain dict immutable, so an actual read-only mapping is used."""

    identity: PredictionIdentity
    target_timestamp: date
    raw_timestamp_origen: str
    raw_target_timestamp: str
    target_observed: bool
    y_true: float | None
    y_proba: float
    y_pred: int
    baselines: Mapping[str, int]


def _parse_date(value: str, *, field_name: str) -> date:
    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError) as exc:
        raise MalformedRowError(f"{field_name!r} inválido: {value!r}") from exc


def _resolve_identity_field(row: dict, key: str, authorized):
    row_has_value = key in row and row[key] is not None
    if row_has_value:
        row_value = row[key]
        if authorized is not None and row_value != authorized:
            raise ForeignIdentityError(
                f"La fila declara {key}={row_value!r}, distinto del run autorizado "
                f"({authorized!r}). No se sustituye silenciosamente."
            )
        return row_value
    if authorized is not None:
        return authorized
    raise MissingIdentityError(f"Falta {key!r}: ni la fila ni el candidato autorizado lo declaran.")


def _validate_target_observed(row: dict) -> bool:
    value = row["target_observed"]
    if not isinstance(value, bool):
        raise InvalidBooleanError(
            f"target_observed debe ser bool, no {type(value).__name__}: {value!r}"
        )
    return value


def _validate_y_proba(row: dict) -> float:
    value = row["y_proba"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidProbabilityError(f"y_proba debe ser numérico: {value!r}")
    if not math.isfinite(value):
        raise InvalidProbabilityError(f"y_proba no finito: {value!r}")
    if not 0.0 <= float(value) <= 1.0:
        raise InvalidProbabilityError(f"y_proba fuera de [0, 1]: {value!r}")
    return float(value)


def _validate_class(value, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidClassError(f"{field_name} debe ser numérico: {value!r}")
    if float(value) not in ADMITTED_CLASSES:
        raise InvalidClassError(f"{field_name} fuera de las clases admitidas {{0, 1}}: {value!r}")
    return int(value)


def _validate_target_observed_coherence(target_observed: bool, row: dict):
    y_true = row.get("y_true")
    if target_observed and y_true is None:
        raise TargetObservedCoherenceError(
            "target_observed=true exige y_true presente; no se infiere ni se completa."
        )
    if not target_observed and y_true is not None:
        raise TargetObservedCoherenceError(
            "target_observed=false exige y_true ausente; no se descarta un valor archivado."
        )


def build_records(
    rows: list[dict],
    *,
    experiment_id: str | None = None,
    run_id: str | None = None,
    config_name: str | None = None,
    seed: int | None = None,
    horizon_days: int,
) -> list[HistoricalPredictionRecord]:
    """Build immutable records from raw `predictions.json` rows, sorted
    chronologically by normalized `timestamp_origen` so that the initial
    selection of a walkthrough never depends on incidental JSON row order.

    `experiment_id`/`run_id`/`config_name`/`seed` are the run this build is
    authorized for. When a row also declares one of these fields, it must
    match the authorized value exactly (`ForeignIdentityError` otherwise) —
    a row can never silently substitute a different run/config/seed.
    """
    if not isinstance(horizon_days, int) or isinstance(horizon_days, bool) or horizon_days <= 0:
        raise InvalidHorizonError(f"horizon_days debe ser un entero positivo: {horizon_days!r}")

    authorized = {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "config_name": config_name,
        "seed": seed,
    }

    seen_identity: set[PredictionIdentity] = set()
    records = []
    for row in rows:
        missing = [field for field in _REQUIRED_ROW_FIELDS if field not in row]
        if missing:
            raise MalformedRowError(f"Fila incompleta, faltan campos {missing}: {row!r}")

        resolved = {
            key: _resolve_identity_field(row, key, authorized[key]) for key in _IDENTITY_FIELDS
        }
        seed_value = resolved["seed"]
        if isinstance(seed_value, bool) or not isinstance(seed_value, int):
            raise MalformedRowError(f"seed debe ser un entero: {seed_value!r}")

        origin_date = _parse_date(row["timestamp"], field_name="timestamp")
        target_date = _parse_date(row["target_timestamp"], field_name="target_timestamp")

        identity = PredictionIdentity(
            experiment_id=str(resolved["experiment_id"]),
            run_id=str(resolved["run_id"]),
            config_name=str(resolved["config_name"]),
            seed=int(seed_value),
            timestamp_origen=origin_date,
        )
        if identity in seen_identity:
            raise DuplicateIdentityError(f"Identidad de predicción duplicada: {identity}")
        seen_identity.add(identity)

        if target_date - origin_date != timedelta(days=horizon_days):
            raise HorizonMismatchError(
                f"Horizonte incompatible en {identity}: "
                f"target_timestamp - timestamp = {target_date - origin_date}, "
                f"horizon_days declarado = {horizon_days}"
            )

        target_observed = _validate_target_observed(row)
        _validate_target_observed_coherence(target_observed, row)
        y_proba = _validate_y_proba(row)
        y_pred = _validate_class(row["y_pred"], field_name="y_pred")
        y_true = (
            float(_validate_class(row["y_true"], field_name="y_true"))
            if row.get("y_true") is not None
            else None
        )

        baselines = MappingProxyType(
            {
                key: row[key]
                for key in ("persistence", "majority_class", "always_stress")
                if key in row
            }
        )
        records.append(
            HistoricalPredictionRecord(
                identity=identity,
                target_timestamp=target_date,
                raw_timestamp_origen=row["timestamp"],
                raw_target_timestamp=row["target_timestamp"],
                target_observed=target_observed,
                y_true=y_true,
                y_proba=y_proba,
                y_pred=y_pred,
                baselines=baselines,
            )
        )

    records.sort(
        key=lambda r: (
            r.identity.timestamp_origen,
            r.identity.experiment_id,
            r.identity.run_id,
            r.identity.config_name,
            r.identity.seed,
        )
    )
    return records
