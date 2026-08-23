"""Contrato de acceso a datos (ADR-0002): interfaz estable sobre Parquet
local. Ningún módulo de otras capas debe leer archivos directamente; deben
usar `load_dataset` / `save_dataset`, de forma que el backend de
almacenamiento sea intercambiable sin afectar otras capas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_ingestion.schema import PROVENANCE_COLUMN, TIMESTAMP_COLUMN, normalize_to_schema

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def save_dataset(name: str, df: pd.DataFrame, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path


def load_dataset(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset '{name}' en {data_dir}")
    return pd.read_parquet(path)


def get_dataset_fingerprint(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> tuple[float, int]:
    """Devuelve una huella barata (fecha de modificación, tamaño en
    bytes) del archivo de `name`, sin leer su contenido. Cambia si y
    solo si el archivo fue reescrito con `save_dataset`.
    """
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset '{name}' en {data_dir}")
    stat = path.stat()
    return (stat.st_mtime, stat.st_size)


def append_reading(name: str, row: dict, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Agrega `row` (un dict con al menos `timestamp`) como una fila
    nueva al dataset `name`, normalizada al esquema completo. Crea el
    dataset si todavía no existe. Devuelve el dataset actualizado, ya
    guardado, ordenado por `timestamp`.
    """
    provenance = row.get(PROVENANCE_COLUMN, "real")
    new_row = normalize_to_schema(pd.DataFrame([row]), provenance=provenance)

    try:
        existing = load_dataset(name, data_dir=data_dir)
        updated = pd.concat([existing, new_row], ignore_index=True)
    except FileNotFoundError:
        updated = new_row

    updated = updated.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)
    save_dataset(name, updated, data_dir=data_dir)
    return updated
