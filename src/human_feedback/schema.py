"""Esquema del registro de retroalimentación humana sobre alertas
(spec human-feedback, requirements "Esquema de registro de
retroalimentación" y "Actualización del estado de validación de una
alerta").
"""

from __future__ import annotations

import pandas as pd

VALIDATION_STATES = {"pendiente", "confirmada", "rechazada"}

FEEDBACK_COLUMNS: dict[str, str] = {
    "fecha": "datetime64[ns]",
    "alerta_generada": "int64",
    "estado_validacion": "object",
    "etiqueta_corregida": "Int64",
    "observacion": "object",
}


def init_feedback_log(dates: pd.Series, alerts: pd.Series) -> pd.DataFrame:
    """Inicializa un registro de retroalimentación a partir de alertas
    generadas: una fila por fecha, estado `pendiente`, sin corrección ni
    observación todavía.
    """
    return pd.DataFrame(
        {
            "fecha": pd.Series(dates).reset_index(drop=True),
            "alerta_generada": pd.Series(alerts).reset_index(drop=True).astype("int64"),
            "estado_validacion": "pendiente",
            "etiqueta_corregida": pd.array([pd.NA] * len(dates), dtype="Int64"),
            "observacion": pd.Series([pd.NA] * len(dates), dtype="object"),
        }
    )


def update_feedback(
    log: pd.DataFrame,
    fecha: pd.Timestamp,
    estado_validacion: str,
    etiqueta_corregida: int | None = None,
    observacion: str | None = None,
) -> pd.DataFrame:
    """Actualiza el estado de validación (y opcionalmente la corrección/
    observación) de la fila de `log` correspondiente a `fecha`.
    """
    if estado_validacion not in VALIDATION_STATES:
        raise ValueError(
            f"Estado de validación inválido: {estado_validacion!r}. "
            f"Debe ser uno de {VALIDATION_STATES}."
        )

    result = log.copy()
    mask = result["fecha"] == fecha

    result.loc[mask, "estado_validacion"] = estado_validacion
    if etiqueta_corregida is not None:
        result.loc[mask, "etiqueta_corregida"] = etiqueta_corregida
    if observacion is not None:
        result.loc[mask, "observacion"] = observacion

    return result
