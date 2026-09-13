"""Captura de advertencias de ajuste con contexto (hallazgo H-05).

Envuelve un bloque de ajuste (una familia, un outer fold, el congelamiento
final) y agrega al log únicamente advertencias efectivamente emitidas, con el
contexto necesario para asociarlas a ese ajuste. Deduplica por
`(contexto, categoría, mensaje)` con un contador, para que un warning
repetido en cientos de fits de tuning no infle el artefacto — nunca vuelca
datos ni tracebacks completos.
"""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Any


@contextmanager
def collect_context_warnings(log: list[dict[str, Any]], **context: Any):
    """Registra en `log` las advertencias emitidas dentro del bloque `with`,
    asociadas al `context` dado (por ejemplo `family`, `outer_fold_index`,
    `phase`)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield
    _record(log, caught, context)


def _record(log: list[dict[str, Any]], caught: list, context: dict[str, Any]) -> None:
    counts: dict[tuple[str, str], int] = {}
    for w in caught:
        key = (w.category.__name__, str(w.message))
        counts[key] = counts.get(key, 0) + 1
    for (category, message), count in counts.items():
        log.append({**context, "category": category, "message": message, "count": count})


__all__ = ["collect_context_warnings"]
