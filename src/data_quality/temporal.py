"""Daily experimental calendar: validate before positional temporal operations."""

from __future__ import annotations

import pandas as pd


def validate_daily_series(df: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted copy; never silently aggregate, fill dates or mix series."""
    if "timestamp" not in df or df.empty:
        raise ValueError("Se requiere una serie diaria no vacía con timestamp.")
    result = df.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="raise")
    dates = result["timestamp"]
    if dates.isna().any() or dates.dt.tz is not None:
        raise ValueError("timestamp debe ser válido, diario y sin zona horaria (día UTC).")
    result = result.sort_values("timestamp").reset_index(drop=True)
    dates = result["timestamp"]
    if dates.duplicated().any() or not dates.eq(dates.dt.normalize()).all():
        raise ValueError("Se requiere exactamente una fila por día y por serie.")
    if not dates.diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError("Calendario irregular: reindexar explícitamente a frecuencia diaria.")
    return result
