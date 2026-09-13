"""Huella determinista del conjunto diario elegible de la Etapa A (hallazgo H-05).

Se calcula exclusivamente sobre `eligible_frame` (ya recortado a la ventana de
la Etapa A por `stage_a_runner.build_eligible_frame`): nunca sobre B/C. La
representación es explícita y estable — orden fijo por `feature_timestamp`,
columnas fijas, timestamps ISO 8601, y floats codificados con `repr()` de
Python (ver más abajo) — para no depender de `hash()` de Python (no
determinista entre procesos) ni de un formato ligado a cómo pandas decide
mostrar los valores en pantalla.

Revisión externa (2026-09-13), hallazgo 2: la versión anterior formateaba los
floats con `"%.12g"` (12 dígitos significativos). Un valor `float64` puede
necesitar hasta 17 dígitos significativos para reconstruirse exactamente, de
modo que dos valores `float64` distintos podían redondear a los mismos 12
dígitos y producir idéntica huella (reproducido con `0.3` vs.
`numpy.nextafter(0.3, 0)`, que además cambia la etiqueta de estrés resultante
sin cambiar la huella). Corregido: cada float se serializa con `repr()`, que
desde Python 3.1 devuelve la representación decimal más corta que, al
volver a interpretarse como `float`, reproduce exactamente el mismo valor
`float64` (round-trip exacto, sin redondeo con pérdida) -- dos valores
`float64` distintos producen siempre cadenas `repr()` distintas."""

from __future__ import annotations

import hashlib
import math
from typing import Any

import pandas as pd

from experiment_runner.controlled_daily_v4.features import FEATURE_COLUMNS

DATASET_FINGERPRINT_FORMAT_VERSION = "controlled_daily_v4_dataset_fingerprint.v2"
"""v1 (implícita, sin este campo): usaba `"%.12g"` para los floats -- con
pérdida de precisión, invalidada por el hallazgo 2 de la revisión externa
2026-09-13 (colisiona valores `float64` distintos). v2: cada float se
serializa con `repr()` de Python (round-trip exacto); primera versión que
declara explícitamente `schema_version` en el propio artefacto."""

FINGERPRINT_COLUMNS: tuple[str, ...] = (
    "feature_timestamp",
    "target_timestamp",
    *FEATURE_COLUMNS,
    "future_soil_moisture",
)

_TIMESTAMP_COLUMNS = ("feature_timestamp", "target_timestamp")
_FLOAT_COLUMNS = tuple(c for c in FINGERPRINT_COLUMNS if c not in _TIMESTAMP_COLUMNS)

_CELL_SEPARATOR = "|"
"""Separador de campos dentro de una fila canónica. Ninguna representación
de columna de este artefacto (timestamps ISO 8601, `repr()` de floats)
puede contener `|`, así que no hace falta escapado ni citado tipo CSV."""

_MISSING_VALUE_POLICY = (
    "El conjunto elegible de la Etapa A no admite valores faltantes en las columnas "
    "de la huella: `select_eligible_rows` ya excluye toda fila con features o target "
    "incompletos antes de que esta función se ejecute. Un `NaN`/`Infinity` inesperado "
    "igual se serializa con un literal explícito ('NaN', 'Infinity', '-Infinity'), sin "
    "fallar ni imputar, para que un cambio de ese contrato sea visible en la huella en "
    "lugar de pasar inadvertido."
)


def _timestamp_repr(value: pd.Timestamp) -> str:
    return value.isoformat() if pd.notna(value) else "NaN"


def _float_repr(value: float) -> str:
    """Representación canónica y sin pérdida de un `float64`.

    `repr()` de Python devuelve, desde 3.1, la cadena decimal más corta que
    vuelve a interpretarse exactamente como el mismo valor `float64` -- a
    diferencia de un formato de precisión fija (`"%.12g"`), nunca colisiona
    dos valores `float64` distintos. Los tres casos no finitos se serializan
    con un literal explícito, nunca con `str(float('nan'))` (que ya es
    `'nan'`, pero se fija aquí para no depender de ese detalle de
    implementación)."""
    f = float(value)
    if math.isnan(f):
        return "NaN"
    if math.isinf(f):
        return "Infinity" if f > 0 else "-Infinity"
    return repr(f)


def compute_dataset_fingerprint(eligible_frame: pd.DataFrame) -> dict[str, Any]:
    """SHA-256 de una representación canónica y estable del conjunto diario
    elegible efectivamente usado por la Etapa A, junto con la definición
    explícita de columnas, orden, tipos y política de valores especiales que
    produce esa huella. No modifica `eligible_frame` ni los valores que
    entrena/evalúa la Etapa A -- es exclusivamente una huella de auditoría."""
    ordered = eligible_frame.sort_values("feature_timestamp").reset_index(drop=True)
    columns = list(FINGERPRINT_COLUMNS)
    export = ordered[columns].copy()

    for column in _TIMESTAMP_COLUMNS:
        export[column] = pd.to_datetime(export[column]).map(_timestamp_repr)
    for column in _FLOAT_COLUMNS:
        export[column] = export[column].map(_float_repr)

    row_texts = export.astype(str).agg(_CELL_SEPARATOR.join, axis=1)
    header = _CELL_SEPARATOR.join(columns)
    body = "\n".join(row_texts) if len(row_texts) else ""
    canonical_text = f"{header}\n{body}" if body else f"{header}\n"
    digest = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()

    has_rows = len(ordered) > 0
    return {
        "schema_version": DATASET_FINGERPRINT_FORMAT_VERSION,
        "sha256": digest,
        "columns": columns,
        "row_order": "feature_timestamp_ascending",
        "n_rows": int(len(ordered)),
        "feature_timestamp_min": (
            ordered["feature_timestamp"].min().isoformat() if has_rows else None
        ),
        "feature_timestamp_max": (
            ordered["feature_timestamp"].max().isoformat() if has_rows else None
        ),
        "timestamp_encoding": "iso_8601",
        "float_encoding": "python_repr_round_trip",
        "cell_separator": _CELL_SEPARATOR,
        "missing_value_policy": _MISSING_VALUE_POLICY,
        "scope": "stage_a_eligible_rows_only",
    }


__all__ = [
    "DATASET_FINGERPRINT_FORMAT_VERSION",
    "FINGERPRINT_COLUMNS",
    "compute_dataset_fingerprint",
]
