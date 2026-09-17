from datetime import date

import pytest

from scripts.demo_simulation.config import DemoConfigError, DemoSessionConfig, validate_config

_TODAY = date(2026, 9, 17)


def _config(**overrides) -> DemoSessionConfig:
    base = dict(
        sensor_id="demo-abc123",
        start_date=date(2026, 1, 1),
        days=5,
        history_days=120,
        seed=42,
        backend_url="http://127.0.0.1:8000",
        interval_seconds=1,
    )
    base.update(overrides)
    return DemoSessionConfig(**base)


def test_valid_config_passes():
    validate_config(_config(), today=_TODAY, horizon_days=3)


def test_rejects_sensor_without_demo_prefix():
    with pytest.raises(DemoConfigError, match="prefijo"):
        validate_config(_config(sensor_id="sensor-a"), today=_TODAY, horizon_days=3)


def test_rejects_start_date_not_in_the_past():
    with pytest.raises(DemoConfigError, match="pasada"):
        validate_config(_config(start_date=_TODAY), today=_TODAY, horizon_days=3)


def test_rejects_period_that_reaches_today_once_horizon_is_added():
    # end_date=2026-09-16 (1 día antes de hoy), horizonte 3 días => llega a hoy
    start = date(2026, 9, 12)
    with pytest.raises(DemoConfigError, match="horizonte"):
        validate_config(_config(start_date=start, days=5), today=_TODAY, horizon_days=3)


def test_rejects_zero_days():
    with pytest.raises(DemoConfigError, match="días a reproducir"):
        validate_config(_config(days=0), today=_TODAY, horizon_days=3)


def test_rejects_zero_history_days():
    with pytest.raises(DemoConfigError, match="historial inicial"):
        validate_config(_config(history_days=0), today=_TODAY, horizon_days=3)


def test_rejects_negative_seed():
    with pytest.raises(DemoConfigError, match="semilla"):
        validate_config(_config(seed=-1), today=_TODAY, horizon_days=3)


@pytest.mark.parametrize("interval", [0, 61])
def test_rejects_interval_outside_bounds(interval):
    with pytest.raises(DemoConfigError, match="intervalo"):
        validate_config(_config(interval_seconds=interval), today=_TODAY, horizon_days=3)


def test_history_and_end_date_properties():
    config = _config(start_date=date(2026, 1, 10), days=5, history_days=10)
    assert config.history_start == date(2025, 12, 31)
    assert config.history_end == date(2026, 1, 9)
    assert config.end_date == date(2026, 1, 14)
