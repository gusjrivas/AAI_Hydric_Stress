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


# Raw `origen` value written by the Hito 2 ensemble demo (ERA5-Land +
# NASA POWER, `experiment_runner.pergamino_ensemble_demo_runner`) -- real
# external reanalysis data, never our own physical sensor ("real" would
# claim exactly that) and never synthetic. A new, explicit category, not a
# reclassification of either existing one; any other unrecognized value
# still falls through to "unknown".
EXTERNAL_REANALYSIS_RAW_VALUE = "external_reanalysis_era5_nasa_power"
EXTERNAL_REANALYSIS_ORIGIN = "external_reanalysis"

# Per-variable, per-row imputation flag column produced by
# `data_quality.imputation.interpolate_missing_causal` ("<columna>_imputado",
# boolean). Distinct from `origen` (PROVENANCE_COLUMN, dataset-level: real
# vs synthetic vs external reanalysis): a real, non-synthetic dataset can
# still contain individual values completed by causal forward-fill because
# the source lacked an observation for that day.
IMPUTATION_FLAG_SUFFIX = "_imputado"

# Three states for the treatment of one variable's value on one row --
# never conflated with `origin` (dataset-level provenance):
#
# - VARIABLE_STATE_OBSERVED: the flag column is absent from this
#   dataframe's schema AND this sensor is not known to require it
#   (`REQUIRED_IMPUTATION_FLAGS_BY_SENSOR`) -- the common case: most
#   sensors/sites never impute, and their behavior here is unchanged
#   from before this distinction existed. Or the column is present and
#   this row's flag is explicitly `False`.
# - VARIABLE_STATE_IMPUTED: the flag column is present in the schema and
#   this row's flag is explicitly `True`.
# - VARIABLE_STATE_UNVERIFIED: either (a) the flag column IS present in
#   this dataframe's schema (this dataset/demo context does track
#   imputation for `variable`) but this particular row's flag value is
#   null/missing, or (b) the column is absent but this sensor is known
#   to require it -- an absent column is then itself evidence that the
#   treatment of this value was never recorded, not evidence that it
#   wasn't imputed. Neither case is evidence of a real observation: the
#   treatment of that specific value can neither be counted as observed
#   nor as imputed. This is decided purely from dataset schema (does the
#   tracking column exist, and is this sensor in
#   `REQUIRED_IMPUTATION_FLAGS_BY_SENSOR`) and an explicit, named
#   sensor/variable association -- never from comparing this value
#   against another row/date's value, never from column-name matching
#   (`startswith`/partial matches). Value equality is never used to
#   infer provenance (see
#   `scripts/refresh_melchor_romero_historical_demo_readings.py`, which
#   forbids the same pattern for the same reason).
VARIABLE_STATE_OBSERVED = "observed"
VARIABLE_STATE_IMPUTED = "imputed"
VARIABLE_STATE_UNVERIFIED = "unverified"

# Sensors whose prepared frame is known, by construction, to track
# imputation for these specific variables (see
# `src/experiment_runner/melchor_romero_historical_demo_runner.py`).
# Explicit association only: never inferred from column-name matching
# (no `startswith`/partial matches) and never from value equality across
# rows. A dataframe for one of these sensors that is MISSING the flag
# column for a required variable did not choose not to track it -- that
# absence itself means the treatment of that value cannot be verified,
# so it must not default to observed the way an ordinary sensor's
# never-tracked variable does.
REQUIRED_IMPUTATION_FLAGS_BY_SENSOR: dict[str, frozenset[str]] = {
    "melchor-romero-demo": frozenset(
        {
            "soil_moisture",
            "relative_humidity",
            "solar_radiation",
        }
    ),
}


def _variable_state(
    source: Any,
    variable: str,
    *,
    requires_imputation_flag: bool = False,
) -> str:
    flag_column = f"{variable}{IMPUTATION_FLAG_SUFFIX}"
    if flag_column not in source.index:
        # Ordinarily "this dataframe never tracks imputation for
        # `variable`" (VARIABLE_STATE_OBSERVED, unchanged behavior for
        # sensors that never impute). But for a sensor known to require
        # this flag (`REQUIRED_IMPUTATION_FLAGS_BY_SENSOR`), an absent
        # column means the treatment of this value cannot be verified --
        # never default to observed.
        return VARIABLE_STATE_UNVERIFIED if requires_imputation_flag else VARIABLE_STATE_OBSERVED
    flag_value = source.get(flag_column)
    if pd.isna(flag_value):
        return VARIABLE_STATE_UNVERIFIED
    return VARIABLE_STATE_IMPUTED if bool(flag_value) else VARIABLE_STATE_OBSERVED


def _origin(value: Any) -> str:
    if pd.isna(value):
        return "unknown"
    if value == "real":
        return "real"
    if value in {"sintetico", "synthetic"}:
        return "synthetic"
    if value == EXTERNAL_REANALYSIS_RAW_VALUE:
        return EXTERNAL_REANALYSIS_ORIGIN
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
    # `last_date` (unfiltered, whole file) only anchors the displayed
    # window when the caller doesn't pin `end` -- existing operational
    # behavior (no clock argument), preserved as-is.
    last_date = dataframe["__date"].max() if len(dataframe) else None
    window_end = end or last_date or today
    # `last_reading_date`/`data_age_days` must instead reflect only what
    # is *admissible* under the effective clock (`today`: the real wall
    # clock operationally, or the historical `server_today` when
    # browsing a past date) -- never the whole file's latest row
    # regardless of that clock. Scanned over the whole file, not just
    # `window`: the last admissible reading can be earlier than
    # `window_start` (a gap right before the displayed window), so
    # restricting the search to the window slice would miss it and
    # under-report age or report none at all.
    admissible_dates = dataframe.loc[dataframe["__date"] <= today, "__date"]
    admissible_last_date = admissible_dates.max() if len(admissible_dates) else None
    window_start = window_end - timedelta(days=days - 1)
    expected_dates = [window_start + timedelta(days=offset) for offset in range(days)]
    window = dataframe[(dataframe["__date"] >= window_start) & (dataframe["__date"] <= window_end)]

    required_flags = REQUIRED_IMPUTATION_FLAGS_BY_SENSOR.get(sensor_id, frozenset())
    rows = []
    observed_dates = set()
    origins = []
    observed_by_variable = {variable: 0 for variable in VARIABLE_UNITS}
    imputed_by_variable = {variable: 0 for variable in VARIABLE_UNITS}
    unverified_by_variable = {variable: 0 for variable in VARIABLE_UNITS}
    for _, source in window.iterrows():
        reading_date = source["__date"]
        observed_dates.add(reading_date)
        flags: list[str] = []
        if reading_date > today:
            flags.append("future_date")
        row = {"date": reading_date, "quality_flags": flags}
        imputed_variables: list[str] = []
        unverified_variables: list[str] = []
        for variable in VARIABLE_UNITS:
            value = _number(source.get(variable), flags, variable)
            row[variable] = value
            if value is not None:
                state = _variable_state(
                    source,
                    variable,
                    requires_imputation_flag=variable in required_flags,
                )
                if state == VARIABLE_STATE_IMPUTED:
                    imputed_by_variable[variable] += 1
                    imputed_variables.append(variable)
                    flags.append(f"imputed:{variable}")
                elif state == VARIABLE_STATE_UNVERIFIED:
                    unverified_by_variable[variable] += 1
                    unverified_variables.append(variable)
                    flags.append(f"unverified_provenance:{variable}")
                else:
                    observed_by_variable[variable] += 1
        row["imputed_variables"] = imputed_variables
        row["unverified_variables"] = unverified_variables
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
            "missing_days": (
                days
                - observed_by_variable[variable]
                - imputed_by_variable[variable]
                - unverified_by_variable[variable]
            ),
            "imputed_days": imputed_by_variable[variable],
            # Days where this variable had a value but the flag tracking its
            # treatment was present-but-null: provenance not verified.
            # Excluded from `observed_days` and `missing_days`, never
            # presented as a real observation (see `_variable_state`).
            "unverified_days": unverified_by_variable[variable],
        }
        for variable in VARIABLE_UNITS
    ]
    return {
        "sensor_id": sensor_id,
        "calendar_timezone": "UTC",
        "server_today": today,
        "snapshot_id": snapshot.dataset_sha256,
        "window": {"start_date": window_start, "end_date": window_end, "expected_days": days},
        # Un archivo con datos pero ninguno admisible hasta `today` (todo
        # posterior al reloj efectivo) debe verse igual que la ausencia de
        # lecturas -- nunca "ready" con filas vacías y sin fecha de última
        # lectura, que sería incoherente con esa ausencia.
        "status": "ready" if admissible_last_date is not None else "no_readings",
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
        "last_reading_date": admissible_last_date,
        "data_age_days": (today - admissible_last_date).days if admissible_last_date else None,
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
            {
                "variable": variable,
                "observed_days": 0,
                "missing_days": days,
                "imputed_days": 0,
                "unverified_days": 0,
            }
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
