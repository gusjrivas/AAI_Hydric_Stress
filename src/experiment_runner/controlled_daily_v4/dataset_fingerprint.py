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

FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS = "stage_a_eligible_rows_only"
"""Único `scope` autorizado de una huella de A o B -- tanto si la calcula la
Etapa A sobre su propio `eligible_frame` como si la recalcula la Etapa B
sobre el suyo (mismo período, protocolo): ambas describen el mismo tipo de
conjunto ("filas elegibles"), nunca el entrenamiento extendido de la Etapa C.
La admisibilidad de un futuro consumidor de B exige este valor exacto, no
una coincidencia mutua entre huellas con un `scope` arbitrario."""

FINGERPRINT_SCOPE_STAGE_C_EVALUATION = "stage_c_evaluation_2024_2025"
"""`scope` explícito del conjunto de EVALUACIÓN única del holdout de la Etapa
C (2024-01-04..2025-12-31, protocolo sección 11) -- revisión dirigida
(hallazgo 5, segunda ronda): identidad e integridad separadas de la del
entrenamiento extendido (`FINGERPRINT_SCOPE_STAGE_C_EXTENDED_TRAINING`).
Se calcula EXCLUSIVAMENTE después de la apertura autorizada del holdout
(dentro de `stage_c_runner.run_stage_c`, nunca antes): esta huella no
sustituye ni se compara contra la de A/B, es evidencia propia del conjunto
efectivamente evaluado en esta corrida concreta."""

FINGERPRINT_SCOPE_STAGE_C_EXTENDED_TRAINING = "stage_c_extended_training_through_2023"
"""`scope` explícito del entrenamiento EXTENDIDO y autorizado de la Etapa C
(hasta 2023-12-31, protocolo sección 11) -- revisión dirigida (hallazgo 5):
etiquetar este conjunto con `FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS` sería
falso (cubre un período distinto y más amplio que el de A/B) y sugeriría,
incorrectamente, que admite la misma comparación de igualdad exacta que
`check_stage_b_admissibility` exige entre A y B. C nunca se compara por
igualdad de huella contra A/B (`stage_c_runner.py`, docstring del módulo);
este `scope` distinto lo deja explícito en el propio artefacto."""

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


def compute_dataset_fingerprint(
    eligible_frame: pd.DataFrame, *, scope: str = FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS
) -> dict[str, Any]:
    """SHA-256 de una representación canónica y estable del conjunto diario
    elegible efectivamente usado, junto con la definición explícita de
    columnas, orden, tipos y política de valores especiales que produce esa
    huella. No modifica `eligible_frame` ni los valores que entrena/evalúa la
    etapa que la invoca -- es exclusivamente una huella de auditoría.

    `scope` identifica EXPLÍCITAMENTE el alcance real del conjunto huellado
    (revisión dirigida, hallazgo 5): por defecto
    `FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS` (A y B, mismo período que A);
    `stage_c_runner.py` pasa `FINGERPRINT_SCOPE_STAGE_C_EXTENDED_TRAINING`
    explícitamente para su entrenamiento extendido -- nunca se etiqueta un
    conjunto con un `scope` que no describe su período real."""
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
        "scope": scope,
    }


__all__ = [
    "DATASET_FINGERPRINT_FORMAT_VERSION",
    "FINGERPRINT_COLUMNS",
    "FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS",
    "FINGERPRINT_SCOPE_STAGE_C_EVALUATION",
    "FINGERPRINT_SCOPE_STAGE_C_EXTENDED_TRAINING",
    "compute_dataset_fingerprint",
]
