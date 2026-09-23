"""Link a `HistoricalPredictionRecord`'s target date to a raw measurement in
a specific dataset/series, rejecting cross-series or ambiguous associations
(spec `historical-replay`, requirement RH-12). Never fuses raw value,
imputation state, and derived label into one field — keeps them separate
(design.md §4.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

MEASURED = "medida"
IMPUTED = "imputada"
UNDETERMINED = "no_determinado"
MISSING_FROM_SOURCE = "sin_dato_en_fuente"


class CrossSeriesObservationError(ValueError):
    """The dataset/series being linked does not match the one declared for
    this prediction, the target date has no row in it, or more than one row
    matches — an ambiguous association is never resolved silently."""


class ObservationConsistencyError(ValueError):
    """`target_observed=True` (the archived prediction says the target
    matured) but the packaged dataset has no raw value for that date — an
    inconsistency between artifacts, not a missing-data state to paper over."""


@dataclass(frozen=True)
class LinkedObservation:
    dataset_name: str
    target_date: date
    raw_value: float | None
    state: str


def link_observation(
    *,
    record,
    dataset_name: str,
    expected_dataset_name: str,
    dataset_df: pd.DataFrame,
    label_column: str,
    imputation_markers_df: pd.DataFrame | None,
) -> LinkedObservation:
    if dataset_name != expected_dataset_name:
        raise CrossSeriesObservationError(
            f"Serie/dataset {dataset_name!r} no coincide con la declarada "
            f"para esta predicción ({expected_dataset_name!r})."
        )

    target_date = record.target_timestamp
    dates = pd.to_datetime(dataset_df["timestamp"]).dt.date
    matches = dataset_df.loc[dates == target_date]
    if matches.empty:
        raise CrossSeriesObservationError(
            f"No hay medición en la serie declarada para la fecha objetivo "
            f"{target_date.isoformat()}."
        )
    if len(matches) > 1:
        raise CrossSeriesObservationError(
            f"Más de una fila coincide con la fecha objetivo "
            f"{target_date.isoformat()}: asociación ambigua, no se resuelve "
            "eligiendo una arbitrariamente."
        )

    raw_cell = matches.iloc[0][label_column]
    raw_value = None if pd.isna(raw_cell) else float(raw_cell)

    if record.target_observed and raw_value is None:
        raise ObservationConsistencyError(
            f"target_observed=true para {target_date.isoformat()}, pero el "
            "dataset empaquetado no tiene un valor crudo para esa fecha."
        )

    if imputation_markers_df is None:
        state = MEASURED if raw_value is not None else UNDETERMINED
    else:
        marker_dates = pd.to_datetime(imputation_markers_df["timestamp"]).dt.date
        marker_matches = imputation_markers_df.loc[marker_dates == target_date]
        if marker_matches.empty:
            state = UNDETERMINED
        elif raw_value is None:
            state = MISSING_FROM_SOURCE
        else:
            imputed = bool(marker_matches.iloc[0][f"{label_column}_imputado"])
            state = IMPUTED if imputed else MEASURED

    return LinkedObservation(
        dataset_name=dataset_name,
        target_date=target_date,
        raw_value=raw_value,
        state=state,
    )
