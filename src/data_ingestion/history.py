"""Consulta historica v2 sobre un snapshot inmutable de una serie."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from data_ingestion.schema import PROVENANCE_COLUMN, TIMESTAMP_COLUMN
from data_ingestion.sensor_naming import dataset_name_for, validate_sensor_id
from data_ingestion.storage import load_dataset_snapshot

VARIABLE_UNITS = {
    "soil_moisture": "m3/m3",
    "relative_humidity": "%",
    "solar_radiation": "MJ/m2/day",
    "temperature": "degC",
    "precipitation": "mm/day",
    "wind_speed": "m/s",
    "et0": "mm/day",
}


class HistoryError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _origin(value: Any) -> str:
    if pd.isna(value):
        return "unknown"
    if value == "real":
        return "real"
    if value in {"sintetico", "synthetic"}:
        return "synthetic"
    return "unknown"


def _number(value: Any, flags: list[str], variable: str) -> float | None:
    if pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        flags.append(f"invalid_numeric:{variable}")
        return None
    if not math.isfinite(number):
        flags.append(f"non_finite:{variable}")
        return None
    return number


def _validate_calendar(dataframe: pd.DataFrame) -> pd.Series:
    if TIMESTAMP_COLUMN not in dataframe:
        raise HistoryError("invalid_calendar", "La serie no contiene timestamp.", 409)
    timestamps = pd.to_datetime(dataframe[TIMESTAMP_COLUMN], errors="coerce", utc=True)
    if timestamps.isna().any():
        raise HistoryError("invalid_calendar", "La serie contiene fechas invalidas.", 409)
    naive = timestamps.dt.tz_convert("UTC").dt.tz_localize(None)
    if (naive != naive.dt.normalize()).any():
        raise HistoryError("invalid_calendar", "La serie contiene timestamps subdiarios.", 409)
    dates = naive.dt.date
    if dates.duplicated().any():
        duplicates = sorted({item.isoformat() for item in dates[dates.duplicated(False)]})
        raise HistoryError(
            "invalid_calendar", "La serie contiene dias duplicados.", 409, {"dates": duplicates}
        )
    return dates


def query_readings(
    sensor_id: str,
    data_dir: Path,
    *,
    registered: bool,
    days: int = 30,
    end: date | None = None,
    server_today: date | None = None,
) -> dict[str, Any]:
    try:
        validate_sensor_id(sensor_id)
    except ValueError as error:
        raise HistoryError(
            "invalid_sensor_id",
            str(error),
            422,
            {"field": "sensor_id"},
        ) from error
    if not 1 <= days <= 365:
        raise HistoryError(
            "invalid_window",
            "days debe estar entre 1 y 365.",
            422,
            {"field": "days"},
        )
    today = server_today or datetime.now(timezone.utc).date()
    name = dataset_name_for(sensor_id)
    try:
        snapshot = load_dataset_snapshot(name, data_dir=data_dir)
    except FileNotFoundError as error:
        if not registered:
            raise HistoryError("sensor_not_found", "El sensor no existe.", 404) from error
        window_end = end or today
        return _empty_response(sensor_id, days, window_end, today)
    except Exception as error:
        raise HistoryError(
            "readings_storage_unavailable", "No se pudo leer la serie del sensor.", 503
        ) from error

    dataframe = snapshot.dataframe.copy()
    dates = _validate_calendar(dataframe)
    dataframe["__date"] = dates
    dataframe = dataframe.sort_values("__date").reset_index(drop=True)
    last_date = dataframe["__date"].max() if len(dataframe) else None
    window_end = end or last_date or today
    window_start = window_end - timedelta(days=days - 1)
    expected_dates = [window_start + timedelta(days=offset) for offset in range(days)]
    window = dataframe[(dataframe["__date"] >= window_start) & (dataframe["__date"] <= window_end)]

    rows = []
    observed_dates = set()
    origins = []
    observed_by_variable = {variable: 0 for variable in VARIABLE_UNITS}
    for _, source in window.iterrows():
        reading_date = source["__date"]
        observed_dates.add(reading_date)
        flags: list[str] = []
        if reading_date > today:
            flags.append("future_date")
        row = {"date": reading_date, "quality_flags": flags}
        for variable in VARIABLE_UNITS:
            value = _number(source.get(variable), flags, variable)
            row[variable] = value
            if value is not None:
                observed_by_variable[variable] += 1
        row_origin = _origin(source.get(PROVENANCE_COLUMN))
        if row_origin == "unknown":
            flags.append("unknown_origin")
        row["origin"] = row_origin
        origins.append(row_origin)
        rows.append(row)

    if not origins or "unknown" in origins:
        provenance = "unknown"
    elif len(set(origins)) > 1:
        provenance = "mixed"
    else:
        provenance = origins[0]
    coverage = [
        {
            "variable": variable,
            "observed_days": observed_by_variable[variable],
            "missing_days": days - observed_by_variable[variable],
        }
        for variable in VARIABLE_UNITS
    ]
    return {
        "sensor_id": sensor_id,
        "calendar_timezone": "UTC",
        "server_today": today,
        "snapshot_id": snapshot.dataset_sha256,
        "window": {"start_date": window_start, "end_date": window_end, "expected_days": days},
        "status": "ready" if len(dataframe) else "no_readings",
        "rows": rows,
        "missing_dates": [item for item in expected_dates if item not in observed_dates],
        "variable_coverage": coverage,
        "units": VARIABLE_UNITS,
        "input_roles": [
            {
                "variable": variable,
                "role": "unknown",
                "basis": "configured",
                "model_reference": None,
            }
            for variable in VARIABLE_UNITS
        ],
        "last_reading_date": last_date,
        "data_age_days": (today - last_date).days if last_date else None,
        "provenance": provenance,
    }


def _empty_response(sensor_id: str, days: int, end: date, today: date) -> dict[str, Any]:
    start = end - timedelta(days=days - 1)
    return {
        "sensor_id": sensor_id,
        "calendar_timezone": "UTC",
        "server_today": today,
        "snapshot_id": None,
        "window": {"start_date": start, "end_date": end, "expected_days": days},
        "status": "no_readings",
        "rows": [],
        "missing_dates": [start + timedelta(days=offset) for offset in range(days)],
        "variable_coverage": [
            {"variable": variable, "observed_days": 0, "missing_days": days}
            for variable in VARIABLE_UNITS
        ],
        "units": VARIABLE_UNITS,
        "input_roles": [
            {
                "variable": variable,
                "role": "unknown",
                "basis": "configured",
                "model_reference": None,
            }
            for variable in VARIABLE_UNITS
        ],
        "last_reading_date": None,
        "data_age_days": None,
        "provenance": "unknown",
    }
