import pytest
from app.dependencies import get_valid_sensor_id
from fastapi import HTTPException


def test_get_valid_sensor_id_returns_valid_id():
    assert get_valid_sensor_id("sensor-a") == "sensor-a"


def test_get_valid_sensor_id_raises_422_for_invalid_id():
    with pytest.raises(HTTPException) as exc_info:
        get_valid_sensor_id("invalido.con.puntos")
    assert exc_info.value.status_code == 422
