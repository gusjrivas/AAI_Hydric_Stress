"""Features causales y target estricto de controlled_daily_v4_external_pergamino.

Las features se calculan exclusivamente sobre el período autorizado de la
etapa más la historia causal estrictamente necesaria para lags(1,2,3) y
rolling(3,7): `restrict_to_stage_window` recorta la serie ANTES de invocar a
`build_feature_frame`, de modo que ninguna observación posterior al corte de
la etapa entra al constructor de features ni recibe `future_soil_moisture`
(protocolo, sección 5). `P20_train` nunca se calcula sobre el DataFrame
completo — solo lo hace quien llama a `compute_p20_threshold`, siempre con el
segmento de train correspondiente.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.config import (
    HORIZON_DAYS,
    LAGS,
    RELATIVE_HUMIDITY_COLUMN,
    ROLLING_WINDOWS,
    SOLAR_RADIATION_COLUMN,
    CalendarIntegrityError,
    StageBounds,
)

_HOURLY_COMPLETENESS_COLUMNS = ("n_obs", "n_unique_hours")
_EXPECTED_HOURS_PER_DAY = 24

FEATURE_COLUMNS = (
    "soil_moisture",
    RELATIVE_HUMIDITY_COLUMN,
    SOLAR_RADIATION_COLUMN,
    "lag1",
    "lag2",
    "lag3",
    "roll_mean_3",
    "roll_mean_7",
)


def required_history_days(
    lags: tuple[int, ...] = LAGS, rolling_windows: tuple[int, ...] = ROLLING_WINDOWS
) -> int:
    """Días de historia cruda necesarios antes de la primera emisión para que
    lags y medias móviles queden completos. Una ventana móvil de `w` días que
    incluye el valor actual requiere `w - 1` observaciones previas."""
    return max(max(lags), max(rolling_windows) - 1)


def compute_stage_window_bounds(
    stage_bounds: StageBounds,
    lags: tuple[int, ...] = LAGS,
    rolling_windows: tuple[int, ...] = ROLLING_WINDOWS,
) -> tuple[date, date]:
    """Fronteras (inclusive) de la ventana autorizada de una etapa más la
    historia causal mínima necesaria para lags/rolling.

    Límite inferior: `emission_start` menos la historia necesaria para
    lags/rolling. Límite superior: `target_end`, la última observación cruda
    que puede usarse como target de la etapa. Única fuente de verdad para
    esta ventana: la reutilizan tanto `restrict_to_stage_window` (recorte de
    la serie diaria ya unida) como la CLI, para recortar las entradas crudas
    ERA5/NASA POWER ANTES de agregarlas o convertir su centinela -- ninguna
    fila fuera de esta ventana debe llegar a un agregador, un validador de
    valores ni al constructor de features (hallazgo H-03)."""
    start = stage_bounds.emission_start - timedelta(
        days=required_history_days(lags, rolling_windows)
    )
    end = stage_bounds.target_end
    return start, end


def restrict_to_stage_window(
    daily_series: pd.DataFrame,
    stage_bounds: StageBounds,
    lags: tuple[int, ...] = LAGS,
    rolling_windows: tuple[int, ...] = ROLLING_WINDOWS,
) -> pd.DataFrame:
    """Recorta la serie diaria al período autorizado de la etapa más la
    historia causal mínima, ANTES de construir cualquier feature.

    Ninguna fila posterior llega al constructor de features (protocolo,
    sección 5)."""
    index = pd.to_datetime(daily_series.index)
    start, end = compute_stage_window_bounds(stage_bounds, lags, rolling_windows)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    return daily_series.loc[(index >= start_ts) & (index <= end_ts)]


def validate_continuous_daily_calendar(daily_series: pd.DataFrame, depth_column: str) -> None:
    """Exige, sobre el rango propio de `daily_series` (ya recortado a la
    ventana autorizada por quien llama), calendario diario único, ordenado y
    sin huecos; cobertura horaria completa cuando esa información viaja en
    el frame (`n_obs`/`n_unique_hours`, ver `ingestion.aggregate_era5_daily`);
    y valores finitos en las columnas de humedad/RH2M/radiación requeridas.

    Precondición de `shift(-HORIZON_DAYS)` en `build_feature_frame`: sin
    continuidad garantizada, un desplazamiento posicional no equivale a
    `target_timestamp = feature_timestamp + HORIZON_DAYS días` (hallazgo
    H-02). Nunca repara ni imputa: reporta y aborta con un diagnóstico
    preciso, para que ninguna llamada directa acepte en silencio una serie
    irregular."""
    index = pd.to_datetime(daily_series.index)

    if index.has_duplicates:
        duplicated_dates = sorted({str(ts.date()) for ts in index[index.duplicated()]})
        raise CalendarIntegrityError(f"Fechas duplicadas en la serie diaria: {duplicated_dates}")
    if not index.is_monotonic_increasing:
        raise CalendarIntegrityError("La serie diaria no está ordenada cronológicamente")
    if len(index) == 0:
        return

    expected = pd.date_range(index.min(), index.max(), freq="D")
    missing = expected.difference(index)
    if len(missing):
        missing_dates = [str(ts.date()) for ts in missing[:10]]
        raise CalendarIntegrityError(
            f"Faltan {len(missing)} fecha(s) en el calendario diario continuo "
            f"({index.min().date()}..{index.max().date()}), por ejemplo: {missing_dates}"
        )

    for column in _HOURLY_COMPLETENESS_COLUMNS:
        if column not in daily_series.columns:
            continue
        incomplete = daily_series.index[daily_series[column] != _EXPECTED_HOURS_PER_DAY]
        if len(incomplete):
            offending = [str(pd.Timestamp(ts).date()) for ts in incomplete[:10]]
            raise CalendarIntegrityError(
                f"Día(s) con cobertura horaria incompleta según '{column}' "
                f"(se esperaban {_EXPECTED_HOURS_PER_DAY}): {offending}"
            )

    # n_obs/n_unique_hours no alcanzan: un día con 24 filas y 24 horas
    # distintas puede tener igual una lectura ausente/no finita en la
    # profundidad evaluada, oculta por `mean(skipna=True)` (hallazgo H-02).
    # Se exige solo para `depth_column` -- nunca para las profundidades
    # excluidas ni para la otra profundidad (principal/sensibilidad) que no
    # participa de esta corrida.
    finite_reads_column = f"n_finite_{depth_column}"
    if finite_reads_column in daily_series.columns:
        incomplete_reads = daily_series.index[
            daily_series[finite_reads_column] != _EXPECTED_HOURS_PER_DAY
        ]
        if len(incomplete_reads):
            offending = [str(pd.Timestamp(ts).date()) for ts in incomplete_reads[:10]]
            raise CalendarIntegrityError(
                f"Día(s) con lecturas horarias ausentes o no finitas en '{depth_column}' "
                f"(se esperaban {_EXPECTED_HOURS_PER_DAY} lecturas finitas): {offending}"
            )

    required_columns = [
        c
        for c in (depth_column, RELATIVE_HUMIDITY_COLUMN, SOLAR_RADIATION_COLUMN)
        if c in daily_series.columns
    ]
    for column in required_columns:
        values = daily_series[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            offending = [
                str(pd.Timestamp(ts).date())
                for ts, v in zip(daily_series.index, values, strict=True)
                if not np.isfinite(v)
            ][:10]
            raise CalendarIntegrityError(
                f"Valores ausentes o no finitos en la columna requerida '{column}': {offending}"
            )


def build_feature_frame(daily_series: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    """Construye, para una profundidad dada, el frame con todas las features
    causales, el target base (`future_soil_moisture`) y los timestamps de
    emisión/target.

    `daily_series` debe venir ya recortada a la ventana autorizada de la
    etapa (ver `restrict_to_stage_window`): esta función no vuelve a filtrar
    y calcularía features sobre cualquier fila que reciba. Antes de construir
    nada valida la continuidad del calendario recibido (hallazgo H-02): nunca
    acepta en silencio una serie con huecos, duplicados, cobertura horaria
    incompleta o valores no finitos."""
    validate_continuous_daily_calendar(daily_series, depth_column)
    s = daily_series[depth_column]

    frame = pd.DataFrame(index=daily_series.index)
    frame["soil_moisture"] = s
    frame[RELATIVE_HUMIDITY_COLUMN] = daily_series[RELATIVE_HUMIDITY_COLUMN]
    frame[SOLAR_RADIATION_COLUMN] = daily_series[SOLAR_RADIATION_COLUMN]
    for lag in LAGS:
        frame[f"lag{lag}"] = s.shift(lag)
    for window in ROLLING_WINDOWS:
        frame[f"roll_mean_{window}"] = s.rolling(window, min_periods=window).mean()

    frame["future_soil_moisture"] = s.shift(-HORIZON_DAYS)
    frame["feature_timestamp"] = frame.index
    frame["target_timestamp"] = frame.index + pd.to_timedelta(HORIZON_DAYS, unit="D")

    return frame


def select_eligible_rows(frame: pd.DataFrame, stage_bounds: StageBounds) -> pd.DataFrame:
    """Filtra `frame` a las filas elegibles de una etapa: features completas
    (sin NaN en `FEATURE_COLUMNS`) y `target_timestamp` dentro del rango
    autorizado de la etapa. No excluye por `feature_timestamp` directamente
    — la elegibilidad de la etapa está definida por el target, tal como
    exige el protocolo (sección 5): diciembre del año anterior puede aportar
    historia causal sin agregar filas evaluables propias, y en efecto no las
    agrega porque su `target_timestamp` cae fuera del rango autorizado."""
    features_complete = frame[list(FEATURE_COLUMNS)].notna().all(axis=1)
    target_available = frame["future_soil_moisture"].notna()

    target_ts = pd.to_datetime(frame["target_timestamp"]).dt.normalize()
    target_in_range = (target_ts >= pd.Timestamp(stage_bounds.target_start)) & (
        target_ts <= pd.Timestamp(stage_bounds.target_end)
    )

    eligible = frame[features_complete & target_available & target_in_range].copy()
    return eligible.sort_values("feature_timestamp")


def compute_p20_threshold(future_soil_moisture: pd.Series) -> float:
    """Percentil 20 de la humedad futura. Llamar EXCLUSIVAMENTE con el
    segmento de train correspondiente (nunca con validación/test ni con el
    conjunto completo antes de dividir)."""
    return float(future_soil_moisture.quantile(0.20))


def build_target(future_soil_moisture: pd.Series, p20_threshold: float) -> pd.Series:
    """`stress = 1` si `future_soil_moisture < p20_threshold` (estrictamente).
    Un valor futuro exactamente igual al umbral produce clase 0."""
    return (future_soil_moisture < p20_threshold).astype(int)
