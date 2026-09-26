"""Ingestion-level tests for the separate Hito 2 demonstration executor.

Builds small synthetic CSV files that reproduce the REAL ERA5-Land/NASA
POWER file formats (headers, column names, sentinel, date reconstruction)
-- never the real Pergamino data. Covers:

1. Parsing/aggregation/renaming/units end-to-end through `build_daily_frame`.
2. Hourly-coverage validation (`n_obs`/`n_unique_hours`/`n_finite_<col>`):
   a missing hour, a duplicated hour masking a missing one, and a
   non-finite reading must all invalidate that day's `soil_moisture`,
   and must never produce a false "observed" target label.
3. That 2024-2025 rows -- present in the raw CSV, loaded into a DataFrame
   transiently -- never affect the permitted frame, the physical
   threshold, or the training/calibration feature matrices.

Never touches `controlled_daily_v4/` beyond the same read-only ingestion
functions the runner itself reuses; never opens the real holdout.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiment_runner.pergamino_ensemble_demo_runner import (
    FEATURE_COLUMNS,
    LAGS,
    ROLLING_WINDOWS,
    TARGET_LABEL_COLUMN,
    build_daily_frame,
    build_feature_frame,
    resolve_training_threshold,
)
from predictive_modeling.operational_preparation import (
    add_calendar_target,
    add_multihorizon_targets,
)

ERA5_FILENAME = "pergamino_era5land_soil_hourly_2015_2025.csv"
NASA_POWER_FILENAME = "pergamino_nasa_power_daily_2015_2025.csv"

ERA5_HEADER = [
    "latitude,longitude,elevation,utc_offset_seconds,timezone,timezone_abbreviation",
    "-33.899998,-60.6,70.0,-10800,America/Argentina/Buenos_Aires,GMT-3",
    "",
    "time,soil_moisture_0_to_7cm (m³/m³),soil_moisture_7_to_28cm (m³/m³),"
    "soil_moisture_28_to_100cm (m³/m³),soil_moisture_100_to_255cm (m³/m³)",
]


def _era5_lines(day_hours: dict[date, list[tuple[int, float]]]) -> list[str]:
    lines = list(ERA5_HEADER)
    for day in sorted(day_hours):
        for hour, value in day_hours[day]:
            cell = "" if isinstance(value, float) and math.isnan(value) else str(value)
            lines.append(f"{day.isoformat()}T{hour:02d}:00,{cell},{cell},{cell},{cell}")
    return lines


def _write_era5_csv(path: Path, day_hours: dict[date, list[tuple[int, float]]]) -> None:
    path.write_text("\n".join(_era5_lines(day_hours)) + "\n", encoding="utf-8")


def _full_day(value: float) -> list[tuple[int, float]]:
    return [(hour, value) for hour in range(24)]


def _nasa_power_lines(daily_values: dict[date, tuple[float, float]]) -> list[str]:
    dates = sorted(daily_values)
    start, end = dates[0], dates[-1]
    lines = [
        "-BEGIN HEADER-",
        "NASA/POWER Source Native Resolution Daily Data",
        f"Dates (month/day/year): {start.month:02d}/{start.day:02d}/{start.year} through "
        f"{end.month:02d}/{end.day:02d}/{end.year} in LST",
        "Location: latitude  -33.891   longitude -60.5746",
        "elevation from MERRA-2: Average for 0.5 x 0.625 degree lat/lon region = 69.07 meters",
        "The value for missing source data that cannot be computed or is outside of the "
        "sources availability range: -999",
        "parameter(s):",
        "RH2M                  MERRA-2 Relative Humidity at 2 Meters (%)",
        "ALLSKY_SFC_SW_DWN     CERES SYN1deg All Sky Surface Shortwave Downward Irradiance "
        "(MJ/m^2/day)",
        "T2M                   MERRA-2 Temperature at 2 Meters (C)",
        "PRECTOTCORR           MERRA-2 Precipitation Corrected (mm/day)",
        "-END HEADER-",
        "YEAR,DOY,RH2M,ALLSKY_SFC_SW_DWN,T2M,PRECTOTCORR",
    ]
    for day in dates:
        rh2m, allsky = daily_values[day]
        doy = day.timetuple().tm_yday
        lines.append(f"{day.year},{doy},{rh2m},{allsky},20.0,0.0")
    return lines


def _write_nasa_power_csv(path: Path, daily_values: dict[date, tuple[float, float]]) -> None:
    path.write_text("\n".join(_nasa_power_lines(daily_values)) + "\n", encoding="utf-8")


def _date_range(start: date, end: date) -> list[date]:
    n = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(n)]


# ---------------------------------------------------------------------------
# 1. Parsing/aggregation/renaming/units, end to end
# ---------------------------------------------------------------------------


def test_build_daily_frame_parses_the_real_csv_formats_and_renames_correctly(tmp_path):
    days = _date_range(date(2022, 6, 1), date(2022, 6, 10))
    era5_days = {day: _full_day(0.30 + 0.01 * i) for i, day in enumerate(days)}
    nasa_days = {day: (55.0 + i, 20.0 + i) for i, day in enumerate(days)}
    # One day with the NASA POWER missing-value sentinel on RH2M.
    sentinel_day = days[3]
    nasa_days[sentinel_day] = (-999, nasa_days[sentinel_day][1])

    era5_csv = tmp_path / ERA5_FILENAME
    nasa_csv = tmp_path / NASA_POWER_FILENAME
    _write_era5_csv(era5_csv, era5_days)
    _write_nasa_power_csv(nasa_csv, nasa_days)

    frame, dataset_sha256 = build_daily_frame(era5_csv, nasa_csv)

    assert list(frame.columns) == [
        "timestamp",
        "soil_moisture",
        "relative_humidity",
        "solar_radiation",
    ]
    assert len(frame) == len(days)
    row0 = frame.loc[frame["timestamp"] == pd.Timestamp(days[0])].iloc[0]
    assert row0["soil_moisture"] == pytest.approx(0.30)
    assert row0["relative_humidity"] == pytest.approx(55.0)
    assert row0["solar_radiation"] == pytest.approx(20.0)

    # NASA POWER's -999 sentinel must be converted to NaN, never used as a
    # literal -999 relative humidity.
    sentinel_row = frame.loc[frame["timestamp"] == pd.Timestamp(sentinel_day)].iloc[0]
    assert pd.isna(sentinel_row["relative_humidity"])

    # Deterministic hash for identical input.
    frame_again, dataset_sha256_again = build_daily_frame(era5_csv, nasa_csv)
    assert dataset_sha256 == dataset_sha256_again
    pd.testing.assert_frame_equal(frame, frame_again)


# ---------------------------------------------------------------------------
# 2. Hourly coverage validation -- never a silently-incomplete average
# ---------------------------------------------------------------------------


def _build_frame_with_one_bad_day(
    tmp_path: Path, bad_day_hours: list[tuple[int, float]]
) -> tuple[pd.DataFrame, date, date]:
    """9 clean days around one bad day (index 4 of 9) -- enough for the bad
    day to be both a feature day and, for its predecessor, a horizon+1
    target day."""
    days = _date_range(date(2022, 6, 1), date(2022, 6, 9))
    bad_day = days[4]
    era5_days = {day: _full_day(0.30) for day in days}
    era5_days[bad_day] = bad_day_hours
    nasa_days = {day: (55.0, 20.0) for day in days}

    era5_csv = tmp_path / ERA5_FILENAME
    nasa_csv = tmp_path / NASA_POWER_FILENAME
    _write_era5_csv(era5_csv, era5_days)
    _write_nasa_power_csv(nasa_csv, nasa_days)

    frame, _ = build_daily_frame(era5_csv, nasa_csv)
    return frame, bad_day, days[3]  # (frame, bad_day, the day right before it)


def test_a_missing_hour_invalidates_soil_moisture_for_that_day(tmp_path):
    hours = [(h, 0.30) for h in range(24) if h != 12]  # hour 12 missing -> 23 rows
    frame, bad_day, _ = _build_frame_with_one_bad_day(tmp_path, hours)
    row = frame.loc[frame["timestamp"] == pd.Timestamp(bad_day)].iloc[0]
    assert pd.isna(row["soil_moisture"])


def test_a_duplicated_hour_masking_a_missing_one_invalidates_soil_moisture(tmp_path):
    # 24 rows, but hour 12 appears twice and hour 13 never appears --
    # n_obs=24 (would look complete by row count alone) but n_unique_hours=23.
    hours = [(h, 0.30) for h in range(24) if h != 13]
    hours.append((12, 0.30))
    frame, bad_day, _ = _build_frame_with_one_bad_day(tmp_path, hours)
    row = frame.loc[frame["timestamp"] == pd.Timestamp(bad_day)].iloc[0]
    assert pd.isna(row["soil_moisture"])


def test_a_non_finite_hourly_value_invalidates_soil_moisture(tmp_path):
    # 24 rows, 24 distinct hours (n_obs=24, n_unique_hours=24 -- would look
    # complete by both row and hour-uniqueness counts) but one reading is
    # non-finite: groupby(...).mean() would otherwise skip it silently.
    hours = [(h, 0.30) for h in range(24)]
    hours[12] = (12, float("nan"))
    frame, bad_day, _ = _build_frame_with_one_bad_day(tmp_path, hours)
    row = frame.loc[frame["timestamp"] == pd.Timestamp(bad_day)].iloc[0]
    assert pd.isna(row["soil_moisture"])


def test_an_incomplete_coverage_day_never_produces_a_false_observed_target_label(tmp_path):
    """The day before the bad day has the bad day as its horizon+1 target.
    That target must come back unobserved (NaN label), never a real 0/1
    computed from an incomplete average."""
    hours = [(h, 0.30) for h in range(24) if h != 12]
    frame, bad_day, day_before = _build_frame_with_one_bad_day(tmp_path, hours)

    labeled = add_calendar_target(frame, column="soil_moisture", horizon_days=1, threshold=0.5)
    row = labeled.loc[labeled["timestamp"] == pd.Timestamp(day_before)].iloc[0]
    assert row["target_date"] == pd.Timestamp(bad_day)
    assert bool(row["target_observed"]) is False
    assert pd.isna(row[TARGET_LABEL_COLUMN])

    # A clean day's target (also horizon+1) must be genuinely observed.
    clean_predecessor = day_before - timedelta(days=1)
    clean_row = labeled.loc[labeled["timestamp"] == pd.Timestamp(clean_predecessor)].iloc[0]
    assert bool(clean_row["target_observed"]) is True
    assert not pd.isna(clean_row[TARGET_LABEL_COLUMN])


# ---------------------------------------------------------------------------
# 3. 2024-2025 rows never affect the permitted frame, threshold, or matrices
# ---------------------------------------------------------------------------


def _build_leak_test_csvs(tmp_path: Path, *, tamper_2024_2025: bool) -> tuple[Path, Path]:
    train_tail = _date_range(date(2021, 12, 1), date(2021, 12, 31))
    calib_head = _date_range(date(2022, 1, 1), date(2022, 1, 31))
    permitted_days = train_tail + calib_head
    excluded_days = _date_range(date(2024, 1, 1), date(2024, 1, 10))

    era5_days: dict[date, list[tuple[int, float]]] = {}
    nasa_days: dict[date, tuple[float, float]] = {}
    for i, day in enumerate(permitted_days):
        value = 0.20 + 0.002 * i
        era5_days[day] = _full_day(value)
        nasa_days[day] = (50.0 + 0.1 * i, 18.0 + 0.1 * i)
    for day in excluded_days:
        # Deliberately extreme/absurd values -- if these ever leaked into
        # the permitted frame, threshold or matrices, this test would fail.
        value = 999.0 if tamper_2024_2025 else 0.0
        era5_days[day] = _full_day(value)
        nasa_days[day] = (value, value)

    tmp_path.mkdir(parents=True, exist_ok=True)
    era5_csv = tmp_path / ERA5_FILENAME
    nasa_csv = tmp_path / NASA_POWER_FILENAME
    _write_era5_csv(era5_csv, era5_days)
    _write_nasa_power_csv(nasa_csv, nasa_days)
    return era5_csv, nasa_csv


def _train_and_calibration_matrices(frame: pd.DataFrame, threshold: float):
    feature_frame, feature_names_tuple = build_feature_frame(
        frame, list(FEATURE_COLUMNS), lags=list(LAGS), windows=list(ROLLING_WINDOWS)
    )
    feature_names = list(feature_names_tuple)
    labeled_by_horizon = add_multihorizon_targets(
        feature_frame, column="soil_moisture", thresholds={1: threshold, 2: threshold, 3: threshold}
    )
    from experiment_runner.pergamino_ensemble_demo_runner import build_cut_plan
    from predictive_modeling.operational_preparation import partition_labeled_horizon

    prepared = partition_labeled_horizon(
        labeled_by_horizon[1], cuts=build_cut_plan(), required_inference_columns=feature_names
    )
    train_rows = prepared.train.dropna(subset=feature_names)
    calib_rows = prepared.calibration.dropna(subset=feature_names)
    return (
        train_rows[feature_names].to_numpy(),
        train_rows[TARGET_LABEL_COLUMN].astype(int).to_numpy(),
        calib_rows[feature_names].to_numpy(),
        calib_rows[TARGET_LABEL_COLUMN].astype(int).to_numpy(),
    )


def test_tampering_2024_2025_never_changes_the_permitted_frame_threshold_or_matrices(tmp_path):
    baseline_era5, baseline_nasa = _build_leak_test_csvs(
        tmp_path / "baseline", tamper_2024_2025=False
    )
    tampered_era5, tampered_nasa = _build_leak_test_csvs(
        tmp_path / "tampered", tamper_2024_2025=True
    )

    baseline_frame, baseline_sha256 = build_daily_frame(baseline_era5, baseline_nasa)
    tampered_frame, tampered_sha256 = build_daily_frame(tampered_era5, tampered_nasa)

    pd.testing.assert_frame_equal(baseline_frame, tampered_frame)
    assert baseline_sha256 == tampered_sha256
    # Sanity: the permitted frame never contains a 2024 row at all.
    assert (baseline_frame["timestamp"].dt.year < 2024).all()

    baseline_threshold = resolve_training_threshold(baseline_frame)
    tampered_threshold = resolve_training_threshold(tampered_frame)
    assert baseline_threshold == tampered_threshold

    baseline_matrices = _train_and_calibration_matrices(baseline_frame, baseline_threshold)
    tampered_matrices = _train_and_calibration_matrices(tampered_frame, tampered_threshold)
    for baseline_array, tampered_array in zip(baseline_matrices, tampered_matrices, strict=True):
        assert baseline_array.shape[0] > 0
        np.testing.assert_array_equal(baseline_array, tampered_array)
