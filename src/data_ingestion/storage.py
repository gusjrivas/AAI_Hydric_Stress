"""Contrato de acceso a datos (ADR-0002): interfaz estable sobre Parquet
local. Ningún módulo de otras capas debe leer archivos directamente; deben
usar `load_dataset` / `save_dataset`, de forma que el backend de
almacenamiento sea intercambiable sin afectar otras capas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

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
