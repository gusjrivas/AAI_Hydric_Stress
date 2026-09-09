"""Features causales y target estricto de controlled_daily_v4_external_pergamino.

Las features se calculan una única vez sobre la serie diaria continua
completa (nunca reiniciadas por etapa); el filtrado por etapa ocurre después,
por `target_timestamp` (protocolo, sección 5). `P20_train` nunca se calcula
sobre el DataFrame completo — solo lo hace quien llama a `compute_p20_threshold`,
siempre con el segmento de train correspondiente.
"""

from __future__ import annotations

import pandas as pd

from experiment_runner.controlled_daily_v4.config import (
    HORIZON_DAYS,
    LAGS,
    RELATIVE_HUMIDITY_COLUMN,
    ROLLING_WINDOWS,
    SOLAR_RADIATION_COLUMN,
    StageBounds,
)

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


def build_feature_frame(daily_series: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    """Construye, para una profundidad dada, el frame con todas las features
    causales, el target base (`future_soil_moisture`) y los timestamps de
    emisión/target, sobre TODA la serie diaria continua provista (sin
    filtrar por etapa)."""
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
