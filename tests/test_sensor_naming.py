import pytest

from data_ingestion.sensor_naming import (
    dataset_name_for,
    feedback_log_name_for,
    registered_model_name_for,
    validate_sensor_id,
)


def test_validate_sensor_id_accepts_alphanumeric_dash_underscore():
    assert validate_sensor_id("sensor-melchor_1") == "sensor-melchor_1"


@pytest.mark.parametrize(
    "invalid_id",
    ["", "a" * 65, "sensor/1", "../etc/passwd", "sensor con espacio", "sensor.1"],
)
def test_validate_sensor_id_rejects_invalid_ids(invalid_id):
    with pytest.raises(ValueError):
        validate_sensor_id(invalid_id)


def test_dataset_name_for_includes_sensor_id_and_prefix():
    assert dataset_name_for("melchor-1") == "sensor__melchor-1"


def test_feedback_log_name_for_includes_sensor_id_and_prefix():
    assert feedback_log_name_for("melchor-1") == "feedback__melchor-1"


def test_registered_model_name_for_includes_sensor_id_and_prefix():
    assert registered_model_name_for("melchor-1") == "alerting_ui_recalibrated_model__melchor-1"


def test_different_sensor_ids_never_collide_on_any_resource_name():
    for namer in (dataset_name_for, feedback_log_name_for, registered_model_name_for):
        assert namer("sensor-a") != namer("sensor-b")


def test_dataset_name_for_can_never_equal_the_historical_dataset_name():
    historical = "melchor_romero_2024_consolidado"
    for sensor_id in ("melchor_romero_2024_consolidado", "a", "sensor-1", "melchor"):
        assert dataset_name_for(sensor_id) != historical


def test_invalid_sensor_id_raises_before_deriving_any_name():
    for namer in (dataset_name_for, feedback_log_name_for, registered_model_name_for):
        with pytest.raises(ValueError):
            namer("invalido/con/barras")
