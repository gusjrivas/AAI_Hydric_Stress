import pandas as pd

from data_ingestion.mock_sensor import generate_next_reading, seed_mock_dataset
from data_ingestion.schema import REQUIRED_COLUMNS, TIMESTAMP_COLUMN
from data_quality.reference_et import estimate_et0
from data_quality.rules import get_range


def test_generate_next_reading_without_history_stays_within_physical_range():
    reading = generate_next_reading(None, pd.Timestamp("2026-01-01"), random_state=0)

    for column in REQUIRED_COLUMNS:
        if column == TIMESTAMP_COLUMN:
            continue
        low, high = get_range(column)
        assert low <= reading[column] <= high
    assert reading["origen"] == "sintetico"


def test_generate_next_reading_stays_close_to_previous_value():
    previous = pd.Series(
        {
            "soil_moisture": 0.3,
            "temperature": 20.0,
            "relative_humidity": 60.0,
            "precipitation": 0.0,
            "solar_radiation": 15.0,
            "wind_speed": 3.0,
        }
    )

    reading = generate_next_reading(previous, pd.Timestamp("2026-01-02"), random_state=0)

    low, high = get_range("temperature")
    max_step = (high - low) * 0.1  # tolerancia generosa: varios desvíos del paso (2% del rango)
    assert abs(reading["temperature"] - previous["temperature"]) <= max_step


def test_generate_next_reading_derives_et0_from_the_rest_of_the_reading():
    reading = generate_next_reading(None, pd.Timestamp("2026-01-01"), random_state=0)

    expected_et0 = estimate_et0(
        temperature=reading["temperature"],
        relative_humidity=reading["relative_humidity"],
        solar_radiation=reading["solar_radiation"],
        wind_speed=reading["wind_speed"],
        timestamp=pd.Timestamp("2026-01-01"),
    )
    assert reading["et0"] == expected_et0


def test_seed_mock_dataset_produces_one_row_per_day(tmp_path):
    generated = seed_mock_dataset(
        "mock_seed",
        start_date=pd.Timestamp("2026-01-01").date(),
        end_date=pd.Timestamp("2026-01-05").date(),
        data_dir=tmp_path,
    )

    assert len(generated) == 5
    assert list(generated[TIMESTAMP_COLUMN]) == list(pd.date_range("2026-01-01", "2026-01-05"))
    assert (generated["origen"] == "sintetico").all()
