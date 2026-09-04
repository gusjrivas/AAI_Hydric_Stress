from data_quality.reference_et import estimate_et0
from data_quality.rules import get_range


def test_estimate_et0_stays_within_agronomic_range():
    et0 = estimate_et0(
        temperature=22.0,
        relative_humidity=55.0,
        solar_radiation=18.0,
        wind_speed=3.0,
        timestamp="2024-01-15",
    )

    low, high = get_range("et0")
    assert low <= et0 <= high


def test_estimate_et0_increases_with_solar_radiation():
    common = dict(
        temperature=22.0,
        relative_humidity=55.0,
        wind_speed=3.0,
        timestamp="2024-01-15",
    )

    low_radiation = estimate_et0(solar_radiation=10.0, **common)
    high_radiation = estimate_et0(solar_radiation=25.0, **common)

    assert high_radiation > low_radiation


def test_estimate_et0_decreases_with_relative_humidity():
    common = dict(
        temperature=22.0,
        solar_radiation=18.0,
        wind_speed=3.0,
        timestamp="2024-01-15",
    )

    dry = estimate_et0(relative_humidity=30.0, **common)
    humid = estimate_et0(relative_humidity=90.0, **common)

    assert dry > humid


def test_estimate_et0_is_higher_in_local_summer_than_local_winter():
    # Hemisferio sur (latitud por defecto -34.95): diciembre es verano, junio es invierno.
    common = dict(
        temperature=22.0,
        relative_humidity=55.0,
        solar_radiation=18.0,
        wind_speed=3.0,
    )

    summer = estimate_et0(timestamp="2024-12-15", **common)
    winter = estimate_et0(timestamp="2024-06-15", **common)

    assert summer > winter
