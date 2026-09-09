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


def required_history_days(
    lags: tuple[int, ...] = LAGS, rolling_windows: tuple[int, ...] = ROLLING_WINDOWS
) -> int:
    """Días de historia cruda necesarios antes de la primera emisión para que
    lags y medias móviles queden completos. Una ventana móvil de `w` días que
    incluye el valor actual requiere `w - 1` observaciones previas."""
    return max(max(lags), max(rolling_windows) - 1)


def restrict_to_stage_window(
    daily_series: pd.DataFrame,
    stage_bounds: StageBounds,
    lags: tuple[int, ...] = LAGS,
    rolling_windows: tuple[int, ...] = ROLLING_WINDOWS,
) -> pd.DataFrame:
    """Recorta la serie diaria al período autorizado de la etapa más la
    historia causal mínima, ANTES de construir cualquier feature.

    Límite inferior: `emission_start` menos la historia necesaria para
    lags/rolling. Límite superior: `target_end`, la última observación cruda
    que puede usarse como target de la etapa. Ninguna fila posterior llega al
    constructor de features (protocolo, sección 5)."""
    index = pd.to_datetime(daily_series.index)
    start = pd.Timestamp(stage_bounds.emission_start) - pd.to_timedelta(
        required_history_days(lags, rolling_windows), unit="D"
    )
    end = pd.Timestamp(stage_bounds.target_end)
    return daily_series.loc[(index >= start) & (index <= end)]


def build_feature_frame(daily_series: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    """Construye, para una profundidad dada, el frame con todas las features
    causales, el target base (`future_soil_moisture`) y los timestamps de
    emisión/target.

    `daily_series` debe venir ya recortada a la ventana autorizada de la
    etapa (ver `restrict_to_stage_window`): esta función no vuelve a filtrar
    y calcularía features sobre cualquier fila que reciba."""
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
