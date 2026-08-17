"""Reglas de calidad y rangos agronómicos esperados (spec data-quality,
requirement "Rangos físicos/climáticos plausibles por variable").

Rangos genéricos, no específicos de un cultivo hortícola en particular:
delimitan valores físicamente plausibles, no óptimos agronómicos. Un
valor fuera de este rango es un candidato a error de medición/carga, no
necesariamente una condición agronómica extrema real.
"""

from __future__ import annotations

AGRONOMIC_RANGES: dict[str, tuple[float, float]] = {
    # Humedad de suelo volumétrica: 0 (suelo seco) a ~0.6 m3/m3 (saturación,
    # el máximo típico de porosidad de la mayoría de los suelos agrícolas).
    "soil_moisture": (0.0, 0.6),
    # Temperatura del aire en superficie: rango extremo plausible para
    # Argentina (evita recortar heladas o olas de calor reales).
    "temperature": (-10.0, 50.0),
    # Humedad relativa: rango físico completo.
    "relative_humidity": (0.0, 100.0),
    # Precipitación diaria: no negativa; 500 mm/día cubre eventos extremos
    # documentados sin ser tan laxo como para no detectar errores de carga.
    "precipitation": (0.0, 500.0),
    # Radiación solar entrante diaria (MJ/m2/día): no negativa; 40 MJ/m2/día
    # excede el máximo teórico en latitudes bajas con cielo despejado.
    "solar_radiation": (0.0, 40.0),
    # Velocidad del viento a 2m (m/s): no negativa; 50 m/s cubre vientos de
    # tormenta severa, muy por encima de condiciones agrícolas habituales.
    "wind_speed": (0.0, 50.0),
    # Evapotranspiración de referencia diaria (mm/día, Penman-Monteith):
    # rara vez supera 12-13 mm/día incluso en climas áridos extremos.
    "et0": (0.0, 15.0),
}


def get_range(column: str) -> tuple[float, float]:
    """Devuelve el rango físico/climático plausible (mínimo, máximo)
    documentado para `column`. Lanza KeyError si no hay rango definido.
    """
    if column not in AGRONOMIC_RANGES:
        raise KeyError(f"No hay rango agronómico documentado para la columna {column!r}")
    return AGRONOMIC_RANGES[column]
