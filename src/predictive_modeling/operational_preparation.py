"""Operational preparation for direct +1/+2/+3 daily predictors.

This module is intentionally separate from ``controlled_daily_v3``/v4 and from
the positional legacy labeler.  Operational targets are joined by their exact
UTC calendar date, so a missing day can never be compacted into another target.
No function in this module fits a threshold, a transformer, or a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import pandas as pd

from data_ingestion.schema import TIMESTAMP_COLUMN

SUPPORTED_HORIZONS = (1, 2, 3)
TARGET_DATE_COLUMN = "target_date"
TARGET_VALUE_COLUMN = "target_value"
TARGET_LABEL_COLUMN = "stress_label"


def _as_date(value: date | str, field: str) -> date:
    if type(value) is date:
        return value
    if not isinstance(value, str):
        raise ValueError(f'{field} debe ser una fecha ISO YYYY-MM-DD.')
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} debe ser una fecha ISO YYYY-MM-DD válida.") from exc
    if value != parsed.isoformat():
        raise ValueError(f"{field} debe usar el formato ISO YYYY-MM-DD.")
    return parsed


def _validate_horizon(horizon_days: int) -> None:
    if (
        isinstance(horizon_days, bool)
        or not isinstance(horizon_days, int)
        or horizon_days not in SUPPORTED_HORIZONS
    ):
        raise ValueError("horizon_days debe ser uno de 1, 2 o 3.")


def _validate_threshold(threshold: float) -> float:
    if isinstance(threshold, bool) or not isinstance(
        threshold, (int, float, np.integer, np.floating)
    ):
        raise ValueError("threshold debe ser un valor numérico finito y explícito.")
    try:
        value = float(threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError("threshold debe ser un valor numérico finito y explícito.") from exc
    if not np.isfinite(value):
        raise ValueError("threshold debe ser un valor numérico finito y explícito.")
    return value


def validate_utc_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted UTC-naive daily frame, rejecting invalid/duplicate dates.

    Gaps are deliberately allowed: the calendar join performed by
    :func:`add_calendar_target` keeps them visible instead of treating the next
    stored row as the next day.
    """

    if TIMESTAMP_COLUMN not in df.columns or df.empty:
        raise ValueError("Se requiere una serie no vacía con timestamp.")
    result = df.copy()
    try:
        timestamps = pd.to_datetime(result[TIMESTAMP_COLUMN], errors="raise", utc=True)
    except (TypeError, ValueError) as exc:
        raise ValueError("timestamp contiene fechas inválidas.") from exc
    if timestamps.isna().any():
        raise ValueError("timestamp contiene fechas nulas.")
    if not timestamps.eq(timestamps.dt.normalize()).all():
        raise ValueError("timestamp debe representar medianoche UTC sin datos subdiarios.")
    timestamps = timestamps.dt.tz_localize(None)
    if timestamps.duplicated().any():
        raise ValueError("timestamp contiene días UTC duplicados.")
    result[TIMESTAMP_COLUMN] = timestamps
    return result.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)


def add_calendar_target(
    df: pd.DataFrame,
    *,
    column: str,
    horizon_days: int,
    threshold: float,
) -> pd.DataFrame:
    """Attach an observed binary target for the exact date ``t + h``.

    ``threshold`` is mandatory and only consumed; it is never calculated here.
    Rows without an observed value on the exact target date retain a nullable
    label and remain inference candidates.  ``supervised_eligible`` only means
    that the target is observed; downstream feature checks can narrow it further.
    """

    _validate_horizon(horizon_days)
    frozen_threshold = _validate_threshold(threshold)
    if column not in df.columns:
        raise ValueError(f"Falta la variable objetivo {column!r}.")

    result = validate_utc_calendar(df)
    try:
        target_values = pd.to_numeric(result[column], errors='raise')
    except (TypeError, ValueError) as exc:
        raise ValueError(f'La variable objetivo {column!r} debe ser numerica.') from exc
    if pd.api.types.is_bool_dtype(target_values.dtype):
        raise ValueError(f'La variable objetivo {column!r} no puede ser booleana.')
    result[column] = target_values
    result[TARGET_DATE_COLUMN] = result[TIMESTAMP_COLUMN] + pd.Timedelta(days=horizon_days)
    observed_by_date = result.set_index(TIMESTAMP_COLUMN)[column]
    result[TARGET_VALUE_COLUMN] = result[TARGET_DATE_COLUMN].map(observed_by_date)
    result["target_observed"] = result[TARGET_VALUE_COLUMN].notna()

    labels = (result[TARGET_VALUE_COLUMN] < frozen_threshold).astype("Float64")
    labels = labels.mask(~result["target_observed"], pd.NA)
    result[TARGET_LABEL_COLUMN] = labels
    result["supervised_eligible"] = result["target_observed"]
    result["inference_candidate"] = True
    return result


def add_multihorizon_targets(
    df: pd.DataFrame, *, column: str, thresholds: dict[int, float]
) -> dict[int, pd.DataFrame]:
    """Build isolated h=1/2/3 labeled frames from explicit frozen thresholds."""

    if set(thresholds) != set(SUPPORTED_HORIZONS):
        raise ValueError("thresholds debe declarar exactamente los horizontes 1, 2 y 3.")
    return {
        horizon: add_calendar_target(
            df, column=column, horizon_days=horizon, threshold=thresholds[horizon]
        )
        for horizon in SUPPORTED_HORIZONS
    }


@dataclass(frozen=True)
class DateRange:
    start: date | str
    end: date | str

    def __post_init__(self) -> None:
        start = _as_date(self.start, "start")
        end = _as_date(self.end, "end")
        if start > end:
            raise ValueError("El inicio de un rango temporal no puede superar su fin.")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    def contains(self, timestamps: pd.Series) -> pd.Series:
        start = pd.Timestamp(self.start)
        end = pd.Timestamp(self.end)
        return timestamps.between(start, end, inclusive="both")

    def to_dict(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}


@dataclass(frozen=True)
class TemporalCutPlan:
    """Explicit operational dates; no split percentage is calculated here."""

    allowed_data: DateRange
    train: DateRange
    calibration: DateRange
    evaluation: DateRange
    inference_as_of: date | str

    def __post_init__(self) -> None:
        inference_as_of = _as_date(self.inference_as_of, "inference_as_of")
        object.__setattr__(self, "inference_as_of", inference_as_of)
        ranges = (self.train, self.calibration, self.evaluation)
        if not (self.train.end < self.calibration.start <= self.calibration.end):
            raise ValueError("train y calibration deben ser cronológicos y no solaparse.")
        if not (self.calibration.end < self.evaluation.start <= self.evaluation.end):
            raise ValueError("calibration y evaluation deben ser cronológicos y no solaparse.")
        if any(
            part.start < self.allowed_data.start or part.end > self.allowed_data.end
            for part in ranges
        ):
            raise ValueError("Todas las particiones deben quedar dentro de allowed_data.")
        if inference_as_of < self.evaluation.end or inference_as_of > self.allowed_data.end:
            raise ValueError(
                "inference_as_of debe cubrir evaluation y quedar dentro de allowed_data."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed_data": self.allowed_data.to_dict(),
            "train": self.train.to_dict(),
            "calibration": self.calibration.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "inference_as_of": self.inference_as_of.isoformat(),
        }


@dataclass(frozen=True)
class PreparedHorizonData:
    train: pd.DataFrame
    calibration: pd.DataFrame
    evaluation: pd.DataFrame
    inference: pd.DataFrame


def partition_labeled_horizon(
    labeled: pd.DataFrame,
    *,
    cuts: TemporalCutPlan,
    required_inference_columns: tuple[str, ...] = (),
) -> PreparedHorizonData:
    """Partition and purge a labeled frame using ``target_date`` boundaries.

    A supervised row belongs to a partition only when both its feature date and
    target date are inside that same explicit range.  Inference candidates do
    not require an observed target.
    """

    required = {
        TIMESTAMP_COLUMN,
        TARGET_DATE_COLUMN,
        TARGET_LABEL_COLUMN,
        "supervised_eligible",
        "inference_candidate",
    }
    missing = sorted(required - set(labeled.columns))
    if missing:
        raise ValueError(f"Faltan columnas de preparación operacional: {missing}")
    missing_features = sorted(set(required_inference_columns) - set(labeled.columns))
    if missing_features:
        raise ValueError(f"Faltan variables requeridas para inferencia: {missing_features}")

    frame = validate_utc_calendar(labeled)
    target_dates = pd.to_datetime(frame[TARGET_DATE_COLUMN], errors="raise")
    if target_dates.isna().any() or target_dates.dt.tz is not None:
        raise ValueError("target_date debe contener días UTC válidos sin zona horaria.")
    if not target_dates.eq(target_dates.dt.normalize()).all():
        raise ValueError("target_date no admite timestamps subdiarios.")
    frame[TARGET_DATE_COLUMN] = target_dates

    if not cuts.allowed_data.contains(frame[TIMESTAMP_COLUMN]).all():
        raise ValueError("La preparación recibió datos fuera de allowed_data.")

    def supervised(part: DateRange) -> pd.DataFrame:
        mask = (
            part.contains(frame[TIMESTAMP_COLUMN])
            & part.contains(frame[TARGET_DATE_COLUMN])
            & frame["supervised_eligible"].eq(True)
            & frame[TARGET_LABEL_COLUMN].notna()
        )
        return frame.loc[mask].reset_index(drop=True)

    inference_mask = frame["inference_candidate"].eq(True) & (
        frame[TIMESTAMP_COLUMN] <= pd.Timestamp(cuts.inference_as_of)
    )
    if required_inference_columns:
        inference_mask &= frame[list(required_inference_columns)].notna().all(axis=1)
    inference = frame.loc[inference_mask].reset_index(drop=True)
    return PreparedHorizonData(
        train=supervised(cuts.train),
        calibration=supervised(cuts.calibration),
        evaluation=supervised(cuts.evaluation),
        inference=inference,
    )
