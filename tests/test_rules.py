import pytest

from data_quality.rules import AGRONOMIC_RANGES, get_range


def test_get_range_returns_documented_bounds_for_temperature():
    minimum, maximum = get_range("temperature")

    assert minimum == -10.0
    assert maximum == 50.0


def test_agronomic_ranges_covers_every_required_column_except_timestamp():
    from data_ingestion.schema import REQUIRED_COLUMNS, TIMESTAMP_COLUMN

    for column in REQUIRED_COLUMNS:
        if column == TIMESTAMP_COLUMN:
            continue
        assert column in AGRONOMIC_RANGES, f"Falta rango documentado para {column!r}"


def test_get_range_raises_for_unknown_column():
    with pytest.raises(KeyError):
        get_range("columna_inexistente")
