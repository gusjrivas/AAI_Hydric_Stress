"""Consolidación multi-fuente (spec data-ingestion, requirement
"Implementar procedimiento reproducible de ingestión y consolidación"):
combina varios datasets normalizados en un único conjunto experimental,
por timestamp.
"""

from __future__ import annotations

import pandas as pd

from data_ingestion.schema import TIMESTAMP_COLUMN, schema_column_order


def consolidate_sources(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Combina `frames` (cada uno ya normalizado al esquema) en un único
    DataFrame indexado por timestamp: para cada columna, conserva el primer
    valor no nulo entre las fuentes, en el orden en que se pasan. Pensado
    para fuentes complementarias (cada una cubre columnas distintas del
    esquema), no para reconciliar mediciones en conflicto de una misma
    columna entre fuentes.
    """
    if not frames:
        raise ValueError("Se requiere al menos un dataset para consolidar")

    indexed = [frame.set_index(TIMESTAMP_COLUMN) for frame in frames]
    combined = indexed[0]
    for frame in indexed[1:]:
        combined = combined.combine_first(frame)

    combined = combined.reset_index()
    return combined[schema_column_order()]
