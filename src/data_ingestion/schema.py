"""Esquema del contrato de acceso a datos (capacidad data-ingestion, ADR-0002).

Distingue columnas obligatorias y opcionales según
docs/research/hu1-variables-y-antecedentes.md. Una fuente individual
puede no cubrir todas las obligatorias (ej. una fuente puramente
climática no reporta humedad de suelo); la validez para modelado se
evalúa a nivel del dataset combinado, no por fuente.
"""

from __future__ import annotations

import pandas as pd

TIMESTAMP_COLUMN = "timestamp"
PROVENANCE_COLUMN = "origen"

REQUIRED_COLUMNS: dict[str, str] = {
    TIMESTAMP_COLUMN: "datetime64[ns]",
    "soil_moisture": "float64",
    "temperature": "float64",
    "relative_humidity": "float64",
    "precipitation": "float64",
    "solar_radiation": "float64",
    "wind_speed": "float64",
    "et0": "float64",
}

OPTIONAL_COLUMNS: dict[str, str] = {
    "canopy_temperature": "float64",
    "ndvi": "float64",
    "stomatal_conductance": "float64",
    "leaf_water_potential": "float64",
}

VALID_PROVENANCE_VALUES = {"real", "sintetico"}


def normalize_to_schema(df: pd.DataFrame, provenance: str = "real") -> pd.DataFrame:
    """Reindexa `df` para que contenga todas las columnas obligatorias y
    opcionales del esquema, agregando como NaN las que la fuente no reporta,
    y fija la columna de procedencia (real | sintetico) desde la ingesta.
    """
    if provenance not in VALID_PROVENANCE_VALUES:
        raise ValueError(
            f"Procedencia inválida: {provenance!r}. Debe ser una de {VALID_PROVENANCE_VALUES}."
        )

    normalized = df.copy()
    for column in {**REQUIRED_COLUMNS, **OPTIONAL_COLUMNS}:
        if column not in normalized.columns:
            normalized[column] = pd.NA

    normalized[PROVENANCE_COLUMN] = provenance

    ordered_columns = (
        [TIMESTAMP_COLUMN]
        + [c for c in REQUIRED_COLUMNS if c != TIMESTAMP_COLUMN]
        + list(OPTIONAL_COLUMNS)
        + [PROVENANCE_COLUMN]
    )
    return normalized[ordered_columns]


def missing_required_columns(df: pd.DataFrame) -> list[str]:
    """Columnas obligatorias completamente ausentes (100% nulas) en `df`."""
    return [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns or df[column].isna().all()
    ]
