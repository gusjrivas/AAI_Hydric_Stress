"""Per-date measurement state and cause for `GET /replay/history` (spec
`historical-replay`, requirements RH-05/RH-08). Distinct from
`observations.link_observation`, which serves a single prediction's
already-revealed target measurement (`medicion_original`, unchanged by
this module): here, `soil_moisture` in the API response is always the
literal raw source value (including `null`), never substituted by an
estimate — a present raw value is always `medida`, regardless of what any
reconstructed marker says about a different representation of the series.
When a value is genuinely absent from the source but was filled by the
causal imputation pipeline, that fact is exposed as `imputada` with the
reconstructed value in its own clearly-derived field (`valor_imputado`),
never inside `soil_moisture`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from historical_replay.observations import IMPUTED, MEASURED, MISSING_FROM_SOURCE, UNDETERMINED


@dataclass(frozen=True)
class HistoryRowState:
    estado: str
    causa: str | None
    valor_imputado: float | None


def _undetermined(target_date: date, undetermined_causa: str | None) -> HistoryRowState:
    causa = undetermined_causa or (
        f"marcador de imputación no recomputado para la fecha {target_date.isoformat()}."
    )
    return HistoryRowState(estado=UNDETERMINED, causa=causa, valor_imputado=None)


def classify_history_row(
    *,
    raw_value: float | None,
    target_date: date,
    label_column: str,
    imputation_markers_df: pd.DataFrame | None,
    undetermined_causa: str | None = None,
) -> HistoryRowState:
    """`imputation_markers_df=None` covers both "markers could not be
    reconstructed at all for this response" (pass `undetermined_causa`
    naming e.g. `ImputationSourceDriftError`) and, from the caller's
    per-row loop, is never passed differently per date — the per-date
    "marker doesn't cover this date" case is detected internally instead
    and always uses the generic causa unless `undetermined_causa` was
    already supplied by the caller for the whole response."""
    if raw_value is not None:
        return HistoryRowState(estado=MEASURED, causa=None, valor_imputado=None)

    if imputation_markers_df is None:
        return _undetermined(target_date, undetermined_causa)

    marker_dates = pd.to_datetime(imputation_markers_df["timestamp"]).dt.date
    marker_matches = imputation_markers_df.loc[marker_dates == target_date]
    if marker_matches.empty:
        return _undetermined(target_date, undetermined_causa)

    imputed = bool(marker_matches.iloc[0][f"{label_column}_imputado"])
    if not imputed:
        return HistoryRowState(
            estado=MISSING_FROM_SOURCE,
            causa=(
                "ausente en la fuente incluso tras aplicar interpolate_missing_causal "
                f"para la fecha {target_date.isoformat()}."
            ),
            valor_imputado=None,
        )

    reconstructed_cell = marker_matches.iloc[0][label_column]
    valor_imputado = None if pd.isna(reconstructed_cell) else float(reconstructed_cell)
    return HistoryRowState(
        estado=IMPUTED,
        causa=(
            "interpolate_missing_causal completó esta fecha "
            f"({target_date.isoformat()}) a partir de un valor causal anterior; "
            f"identificado por el marcador {label_column}_imputado."
        ),
        valor_imputado=valor_imputado,
    )
