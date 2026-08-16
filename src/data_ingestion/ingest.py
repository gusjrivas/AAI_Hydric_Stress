"""Procedimiento reproducible de ingestión y consolidación (spec
data-ingestion, requirement "Implementar procedimiento reproducible de
ingestión y consolidación"): descarga, guarda, calcula cobertura y
documenta el diccionario de datos de una fuente en un solo paso.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

import pandas as pd

from data_ingestion.coverage import coverage_report
from data_ingestion.dictionary import DEFAULT_DICTIONARIES_DIR, write_data_dictionary
from data_ingestion.storage import DEFAULT_DATA_DIR, save_dataset

FetchFn = Callable[[float, float, date, date], pd.DataFrame]


def run_ingestion(
    fetch_fn: FetchFn,
    name: str,
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    license_: str = "",
    limitations: str = "",
    data_dir: Path = DEFAULT_DATA_DIR,
    dictionaries_dir: Path = DEFAULT_DICTIONARIES_DIR,
) -> dict[str, Path]:
    """Descarga con `fetch_fn`, guarda el dataset, calcula el reporte de
    cobertura y escribe el diccionario de datos, todo bajo `name`.
    """
    df = fetch_fn(latitude, longitude, start, end)

    dataset_path = save_dataset(name, df, data_dir=data_dir)

    coverage = coverage_report(df)
    data_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = data_dir / f"{name}_coverage.csv"
    coverage.to_csv(coverage_path, index=False)

    dictionary_path = write_data_dictionary(
        source_name=name,
        provenance="real",
        license_=license_,
        limitations=limitations,
        dictionaries_dir=dictionaries_dir,
        extra={
            "latitude": latitude,
            "longitude": longitude,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "rows": len(df),
        },
    )

    return {
        "dataset_path": dataset_path,
        "coverage_path": coverage_path,
        "dictionary_path": dictionary_path,
    }
