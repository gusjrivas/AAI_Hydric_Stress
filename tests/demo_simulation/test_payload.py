from datetime import date

from scripts.demo_simulation.payload import (
    build_ingest_payload,
    generate_day_reading,
    payload_hash,
    reading_to_json,
)


def test_generated_reading_includes_et0():
    reading = generate_day_reading(None, date(2026, 1, 1), seed=42)
    assert "et0" in reading
    assert reading["et0"] == reading["et0"]  # no es NaN


def test_payload_includes_et0_unlike_simple_client():
    reading = generate_day_reading(None, date(2026, 1, 1), seed=42)
    payload = build_ingest_payload(reading)
    assert payload["et0"] is not None
    assert set(payload) == {
        "timestamp",
        "procedencia",
        "soil_moisture",
        "temperature",
        "relative_humidity",
        "precipitation",
        "solar_radiation",
        "wind_speed",
        "et0",
    }
    assert payload["procedencia"] == "sintetico"


def test_generation_is_reproducible_given_same_seed_and_previous():
    previous = reading_to_json(generate_day_reading(None, date(2026, 1, 1), seed=42))

    reading_a = generate_day_reading(previous, date(2026, 1, 2), seed=43)
    reading_b = generate_day_reading(previous, date(2026, 1, 2), seed=43)

    assert build_ingest_payload(reading_a) == build_ingest_payload(reading_b)


def test_continuity_chains_from_previous_reading():
    day1 = generate_day_reading(None, date(2026, 1, 1), seed=42)
    day2 = generate_day_reading(reading_to_json(day1), date(2026, 1, 2), seed=43)

    # El paso aleatorio es chico: el día 2 no puede ser idéntico al día 1
    # (misma lectura repetida) para el mismo random_state distinto, y
    # tampoco arranca del punto medio del rango físico como si no hubiera
    # `previous`.
    day2_without_previous = generate_day_reading(None, date(2026, 1, 2), seed=43)
    assert build_ingest_payload(day2) != build_ingest_payload(day2_without_previous)


def test_payload_hash_is_stable_and_order_independent():
    payload = build_ingest_payload(generate_day_reading(None, date(2026, 1, 1), seed=42))
    reordered = dict(reversed(list(payload.items())))

    assert payload_hash(payload) == payload_hash(reordered)


def test_payload_hash_changes_with_content():
    payload_a = build_ingest_payload(generate_day_reading(None, date(2026, 1, 1), seed=42))
    payload_b = build_ingest_payload(generate_day_reading(None, date(2026, 1, 1), seed=43))

    assert payload_hash(payload_a) != payload_hash(payload_b)
