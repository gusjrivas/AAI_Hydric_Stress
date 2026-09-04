"""Evapotranspiración de referencia (et0) por FAO-56 Penman-Monteith
(spec data-quality, requirement "Derivación de et0 con temperatura
media"). El esquema (`data_ingestion.schema`) solo registra temperatura
media diaria, no Tmax/Tmin — se usa la variante de FAO-56 que sustituye
ambas por la temperatura media (Allen et al., 1998, FAO Irrigation and
Drainage Paper 56), documentada por la propia FAO como aproximación
válida cuando no hay Tmax/Tmin disponibles, a costa de algo de
precisión frente a la fórmula completa.
"""

from __future__ import annotations

import math

import pandas as pd

_ALBEDO = 0.23  # albedo del cultivo de referencia (pasto), FAO-56
_STEFAN_BOLTZMANN = 4.903e-9  # MJ K^-4 m^-2 día^-1
_SOLAR_CONSTANT = 0.0820  # MJ m^-2 min^-1
_SOIL_HEAT_FLUX = 0.0  # MJ m^-2 día^-1, despreciable a escala diaria (FAO-56)


def _saturation_vapor_pressure(temperature: float) -> float:
    return 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))


def _slope_of_saturation_vapor_pressure(temperature: float) -> float:
    es = _saturation_vapor_pressure(temperature)
    return 4098 * es / (temperature + 237.3) ** 2


def _atmospheric_pressure(elevation: float) -> float:
    return 101.3 * ((293 - 0.0065 * elevation) / 293) ** 5.26


def _extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    latitude = math.radians(latitude_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    solar_declination = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    sunset_hour_angle = math.acos(
        max(-1.0, min(1.0, -math.tan(latitude) * math.tan(solar_declination)))
    )
    return (
        (24 * 60 / math.pi)
        * _SOLAR_CONSTANT
        * dr
        * (
            sunset_hour_angle * math.sin(latitude) * math.sin(solar_declination)
            + math.cos(latitude) * math.cos(solar_declination) * math.sin(sunset_hour_angle)
        )
    )


def _net_radiation(
    solar_radiation: float,
    temperature: float,
    actual_vapor_pressure: float,
    latitude: float,
    elevation: float,
    day_of_year: int,
) -> float:
    net_shortwave = (1 - _ALBEDO) * solar_radiation

    extraterrestrial_radiation = _extraterrestrial_radiation(latitude, day_of_year)
    clear_sky_radiation = (0.75 + 2e-5 * elevation) * extraterrestrial_radiation
    cloudiness_factor = 1.35 * (solar_radiation / clear_sky_radiation) - 0.35
    cloudiness_factor = max(0.05, min(1.0, cloudiness_factor))

    temperature_kelvin = temperature + 273.16
    net_longwave = (
        _STEFAN_BOLTZMANN
        * temperature_kelvin**4
        * (0.34 - 0.14 * math.sqrt(max(actual_vapor_pressure, 0.0)))
        * cloudiness_factor
    )

    return net_shortwave - net_longwave


def estimate_et0(
    temperature: float,
    relative_humidity: float,
    solar_radiation: float,
    wind_speed: float,
    timestamp: pd.Timestamp | str,
    latitude: float = -34.95,
    elevation: float = 15.0,
) -> float:
    """Estima et0 (mm/día) por FAO-56 Penman-Monteith, sustituyendo
    Tmax/Tmin por `temperature` (temperatura media diaria) ya que el
    esquema del proyecto no registra extremos diarios. `latitude` y
    `elevation` toman por defecto el sitio de referencia del proyecto
    (Melchor Romero, Partido de La Plata, HU2).
    """
    day_of_year = pd.Timestamp(timestamp).day_of_year

    saturation_vapor_pressure = _saturation_vapor_pressure(temperature)
    actual_vapor_pressure = saturation_vapor_pressure * relative_humidity / 100

    slope = _slope_of_saturation_vapor_pressure(temperature)
    psychrometric_constant = 0.665e-3 * _atmospheric_pressure(elevation)

    net_radiation = _net_radiation(
        solar_radiation, temperature, actual_vapor_pressure, latitude, elevation, day_of_year
    )

    numerator = 0.408 * slope * (net_radiation - _SOIL_HEAT_FLUX) + psychrometric_constant * (
        900 / (temperature + 273)
    ) * wind_speed * (saturation_vapor_pressure - actual_vapor_pressure)
    denominator = slope + psychrometric_constant * (1 + 0.34 * wind_speed)

    return max(0.0, numerator / denominator)
