"""Hallazgo H-02: calendario y horizonte.

Nunca se acepta en silencio una serie diaria con huecos, duplicados,
cobertura horaria incompleta (incluida una hora duplicada que oculte otra
ausente) o valores no finitos en las columnas requeridas -- todo dentro del
propio rango recibido, sin tocar el período de B/C (hallazgo H-03).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.config import (
    PRIMARY_DEPTH_COLUMN,
    STAGE_A_BOUNDS,
    CalendarIntegrityError,
    ProtocolConfig,
)
from experiment_runner.controlled_daily_v4.features import (
    build_feature_frame,
    restrict_to_stage_window,
    validate_continuous_daily_calendar,
)
from experiment_runner.controlled_daily_v4.ingestion import (
    aggregate_era5_daily,
    build_daily_joined_series,
    load_era5_hourly_raw,
    load_nasa_power_daily_raw,
    replace_missing_sentinel,
)
from experiment_runner.controlled_daily_v4.stage_a_runner import build_eligible_frame, run_stage_a
from tests.controlled_daily_v4_fixtures import (
    corrupt_era5_hourly_value,
    drop_one_hourly_row,
    duplicate_hour_hiding_missing_hour,
    make_synthetic_daily_frame,
    remove_calendar_day,
    write_synthetic_pergamino_csv_pair,
)


def _build_daily_series_from_csvs(era5_path, nasa_path):
    _era5_meta, era5_df = load_era5_hourly_raw(era5_path)
    era5_daily = aggregate_era5_daily(era5_df)
    _nasa_meta, nasa_df = load_nasa_power_daily_raw(nasa_path)
    nasa_df = replace_missing_sentinel(nasa_df)
    return build_daily_joined_series(era5_daily, nasa_df)


def test_valid_continuous_series_is_accepted_without_raising():
    daily = make_synthetic_daily_frame(n_days=60, seed=1)
    validate_continuous_daily_calendar(daily, PRIMARY_DEPTH_COLUMN)  # no debe lanzar
    frame = build_feature_frame(daily, PRIMARY_DEPTH_COLUMN)
    d0 = daily.index[0]
    d3 = daily.index[3]
    assert frame.loc[d0, "target_timestamp"] == d3
    assert frame.loc[d0, "future_soil_moisture"] == daily.loc[d3, PRIMARY_DEPTH_COLUMN]


def test_missing_calendar_day_in_era5_only_is_rejected(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=2)
    remove_calendar_day(era5, nasa, "2015-01-20", from_era5=True, from_nasa=False)
    daily_series = _build_daily_series_from_csvs(era5, nasa)

    with pytest.raises(CalendarIntegrityError, match="fecha"):
        build_eligible_frame(daily_series, PRIMARY_DEPTH_COLUMN)


def test_missing_calendar_day_in_both_sources_is_rejected(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=3)
    remove_calendar_day(era5, nasa, "2015-01-20", from_era5=True, from_nasa=True)
    daily_series = _build_daily_series_from_csvs(era5, nasa)

    with pytest.raises(CalendarIntegrityError, match="fecha"):
        build_eligible_frame(daily_series, PRIMARY_DEPTH_COLUMN)


def test_day_with_23_hourly_observations_is_rejected(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=4)
    drop_one_hourly_row(era5, day_index=15)
    daily_series = _build_daily_series_from_csvs(era5, nasa)

    with pytest.raises(CalendarIntegrityError, match="cobertura horaria incompleta"):
        build_eligible_frame(daily_series, PRIMARY_DEPTH_COLUMN)


def test_duplicated_hour_hiding_a_missing_hour_is_rejected_even_with_24_rows(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=5)
    duplicate_hour_hiding_missing_hour(era5, day_index=15)

    _era5_meta, era5_df = load_era5_hourly_raw(era5)
    era5_daily = aggregate_era5_daily(era5_df)
    day = era5_daily.index[15]
    assert era5_daily.loc[day, "n_obs"] == 24
    assert era5_daily.loc[day, "n_unique_hours"] == 23

    _nasa_meta, nasa_df = load_nasa_power_daily_raw(nasa)
    nasa_df = replace_missing_sentinel(nasa_df)
    daily_series = build_daily_joined_series(era5_daily, nasa_df)

    with pytest.raises(CalendarIntegrityError, match="cobertura horaria incompleta"):
        build_eligible_frame(daily_series, PRIMARY_DEPTH_COLUMN)


def test_invalid_humidity_value_within_the_authorized_window_is_rejected(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=6)
    daily_series = _build_daily_series_from_csvs(era5, nasa)
    poisoned = daily_series.copy()
    poisoned.loc[poisoned.index[20], "RH2M"] = np.nan

    with pytest.raises(CalendarIntegrityError, match="no finitos"):
        build_eligible_frame(poisoned, PRIMARY_DEPTH_COLUMN)


def test_sentinel_outside_stage_a_never_breaks_stage_a_processing():
    """H-03: un `-999` en 2024 (fuera de la Etapa A) no puede tumbar el
    procesamiento de la Etapa A -- la ventana autorizada ni siquiera llega a
    ver esa fila."""
    daily = make_synthetic_daily_frame(n_days=4000, seed=7)
    daily_series = daily.copy()
    future_date = pd.Timestamp("2024-06-01")
    assert future_date > pd.Timestamp(STAGE_A_BOUNDS.target_end)
    daily_series.loc[future_date, "RH2M"] = -999

    # No debe lanzar: 2024-06-01 queda fuera de la ventana autorizada.
    eligible = build_eligible_frame(daily_series.sort_index(), PRIMARY_DEPTH_COLUMN)
    assert len(eligible) > 0


def test_missing_day_changes_target_alignment_reproduction_is_rejected_not_silently_wrong(tmp_path):
    """Reproducción externa H-02: al eliminar un día, una emisión cercana no
    puede terminar declarando un `target_timestamp` que no corresponde al
    valor efectivamente usado por `shift(-3)`. La corrección exige rechazar
    con diagnóstico en vez de calcular ese target incorrecto en silencio."""
    daily = make_synthetic_daily_frame(n_days=60, seed=8)
    corrupted = daily.drop(index=pd.Timestamp("2015-01-11"))

    with pytest.raises(CalendarIntegrityError):
        build_feature_frame(corrupted, PRIMARY_DEPTH_COLUMN)


def test_restrict_to_stage_window_does_not_itself_validate_but_feature_frame_does():
    """`restrict_to_stage_window` sigue siendo un recorte puro; la garantía
    de continuidad la exige `build_feature_frame` sobre lo que reciba,
    ninguna llamada directa relevante puede saltearla (hallazgo H-02)."""
    daily = make_synthetic_daily_frame(n_days=400, seed=9)
    restricted = restrict_to_stage_window(daily, STAGE_A_BOUNDS)
    validate_continuous_daily_calendar(restricted, PRIMARY_DEPTH_COLUMN)  # no debe lanzar


# --------------------------------------------------------------------------
# H-02 (completado): cobertura de lecturas horarias válidas.
#
# Reproducción externa: un CSV ERA5 con 24 registros y 24 horas distintas
# para un día, pero con una lectura de humedad ausente/no finita, superaba
# la validación porque `groupby(...).mean()` ignora el `NaN` en silencio
# (`skipna=True`) y produce un promedio "completo" a partir de solo 23
# lecturas. `n_obs == 24` y `n_unique_hours == 24` no alcanzan para
# detectarlo -- se agrega `n_finite_<columna>` en `aggregate_era5_daily`.
# --------------------------------------------------------------------------


def test_day_with_24_rows_and_24_hours_but_one_nan_reading_is_rejected(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=15)
    corrupt_era5_hourly_value(
        era5,
        day_index=20,
        hour=9,
        column_name="soil_moisture_0_to_7cm (m³/m³)",
        raw_value="",
    )

    _era5_meta, era5_df = load_era5_hourly_raw(era5)
    era5_daily = aggregate_era5_daily(era5_df)
    day = era5_daily.index[20]
    assert era5_daily.loc[day, "n_obs"] == 24
    assert era5_daily.loc[day, "n_unique_hours"] == 24
    assert era5_daily.loc[day, "n_finite_soil_moisture_0_to_7cm"] == 23
    assert np.isfinite(
        era5_daily.loc[day, "soil_moisture_0_to_7cm"]
    ), "el promedio en sí sigue siendo finito -- por eso n_obs/n_unique_hours no alcanzan"

    _nasa_meta, nasa_df = load_nasa_power_daily_raw(nasa)
    nasa_df = replace_missing_sentinel(nasa_df)
    daily_series = build_daily_joined_series(era5_daily, nasa_df)

    with pytest.raises(CalendarIntegrityError, match="lecturas horarias ausentes o no finitas"):
        build_eligible_frame(daily_series, PRIMARY_DEPTH_COLUMN)


def test_day_with_an_infinite_hourly_reading_is_rejected(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=16)
    corrupt_era5_hourly_value(
        era5,
        day_index=20,
        hour=9,
        column_name="soil_moisture_0_to_7cm (m³/m³)",
        raw_value="inf",
    )

    _era5_meta, era5_df = load_era5_hourly_raw(era5)
    era5_daily = aggregate_era5_daily(era5_df)
    day = era5_daily.index[20]
    assert era5_daily.loc[day, "n_obs"] == 24
    assert era5_daily.loc[day, "n_unique_hours"] == 24
    assert era5_daily.loc[day, "n_finite_soil_moisture_0_to_7cm"] == 23

    _nasa_meta, nasa_df = load_nasa_power_daily_raw(nasa)
    nasa_df = replace_missing_sentinel(nasa_df)
    daily_series = build_daily_joined_series(era5_daily, nasa_df)

    with pytest.raises(CalendarIntegrityError, match="lecturas horarias ausentes o no finitas"):
        build_eligible_frame(daily_series, PRIMARY_DEPTH_COLUMN)


def test_missing_hourly_reading_rejection_happens_before_any_model_fit(tmp_path, monkeypatch):
    """El rechazo debe ocurrir antes de cualquier ajuste (`fit_estimator`),
    no solo antes de que el runner termine."""
    import experiment_runner.controlled_daily_v4.stage_a_runner as stage_a_runner_module

    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=400, seed=17)
    corrupt_era5_hourly_value(
        era5,
        day_index=20,
        hour=9,
        column_name="soil_moisture_0_to_7cm (m³/m³)",
        raw_value="",
    )
    _era5_meta, era5_df = load_era5_hourly_raw(era5)
    era5_daily = aggregate_era5_daily(era5_df)
    _nasa_meta, nasa_df = load_nasa_power_daily_raw(nasa)
    nasa_df = replace_missing_sentinel(nasa_df)
    daily_series = build_daily_joined_series(era5_daily, nasa_df)

    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("fit_estimator nunca debe invocarse ante una lectura no finita")

    monkeypatch.setattr(stage_a_runner_module, "fit_estimator", _fail_if_called)

    with pytest.raises(CalendarIntegrityError, match="lecturas horarias ausentes o no finitas"):
        run_stage_a(daily_series, PRIMARY_DEPTH_COLUMN, ProtocolConfig(bootstrap_replicas=10))


def test_finite_reading_check_only_applies_to_the_depth_actually_analyzed(tmp_path):
    """No debe depender de las profundidades excluidas ni de la otra
    profundidad (principal/sensibilidad) que no participa de esta corrida:
    un defecto en `soil_moisture_28_to_100cm` no puede tumbar el análisis
    de la profundidad principal."""
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=18)
    corrupt_era5_hourly_value(
        era5,
        day_index=20,
        hour=9,
        column_name="soil_moisture_28_to_100cm (m³/m³)",
        raw_value="",
    )
    daily_series = _build_daily_series_from_csvs(era5, nasa)

    # No debe lanzar: la profundidad principal (0-7cm) está intacta.
    eligible = build_eligible_frame(daily_series, PRIMARY_DEPTH_COLUMN)
    assert len(eligible) > 0
