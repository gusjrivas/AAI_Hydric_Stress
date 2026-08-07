import pandas as pd

from data_ingestion.schema import (
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    missing_required_columns,
    normalize_to_schema,
)


def test_normalize_adds_missing_columns_as_na():
    raw = pd.DataFrame({"timestamp": ["2026-01-01"], "temperature": [25.0]})

    normalized = normalize_to_schema(raw, provenance="real")

    for column in {**REQUIRED_COLUMNS, **OPTIONAL_COLUMNS}:
        assert column in normalized.columns
    assert normalized.loc[0, "soil_moisture"] is pd.NA
    assert normalized.loc[0, "temperature"] == 25.0


def test_normalize_sets_provenance_column():
    raw = pd.DataFrame({"timestamp": ["2026-01-01"]})

    normalized = normalize_to_schema(raw, provenance="sintetico")

    assert (normalized["origen"] == "sintetico").all()


def test_normalize_rejects_invalid_provenance():
    raw = pd.DataFrame({"timestamp": ["2026-01-01"]})

    try:
        normalize_to_schema(raw, provenance="invalido")
        assert False, "Se esperaba ValueError"
    except ValueError:
        pass


def test_missing_required_columns_detects_fully_null_column():
    raw = pd.DataFrame(
        {
            "timestamp": ["2026-01-01", "2026-01-02"],
            "temperature": [25.0, 26.0],
            "soil_moisture": [None, None],
        }
    )

    missing = missing_required_columns(raw)

    assert "soil_moisture" in missing
    assert "temperature" not in missing
