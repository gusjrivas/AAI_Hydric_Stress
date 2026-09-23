"""Measurement history filtered by the simulated clock (spec
`historical-replay`, design.md §6): the full dataset is never exposed as a
future public response — only rows up to and including the simulated clock
are ever returned, extending the same causality principle already applied
to predictions (RH-02) to the raw input history."""

from __future__ import annotations

from datetime import date

import pandas as pd


def filtered_history(
    dataset_df: pd.DataFrame, columns: list[str], simulated_clock: date
) -> pd.DataFrame:
    """Return only `["timestamp", *columns]` for rows whose date is `<=
    simulated_clock`. Rows after the clock are absent from the result, not
    merely blanked out."""
    if "timestamp" not in dataset_df.columns:
        raise ValueError("dataset_df requiere una columna 'timestamp'.")
    dates = pd.to_datetime(dataset_df["timestamp"]).dt.date
    mask = dates <= simulated_clock
    return dataset_df.loc[mask, ["timestamp", *columns]].reset_index(drop=True)
