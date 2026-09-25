"""Contrato de acceso a datos (ADR-0002): interfaz estable sobre Parquet
local. Ningún módulo de otras capas debe leer archivos directamente; deben
usar `load_dataset` / `save_dataset`, de forma que el backend de
almacenamiento sea intercambiable sin afectar otras capas.
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from data_ingestion.schema import PROVENANCE_COLUMN, TIMESTAMP_COLUMN, normalize_to_schema


class StorageLockTimeout(TimeoutError):
    """Raised when a storage resource stays locked past the deadline."""

    pass


def _acquire_file_lock(handle: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _release_file_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def interprocess_lock(lock_path: Path, timeout: float = 10.0) -> Iterator[None]:
    """Exclude writers in different processes from the same resource."""
    if timeout < 0:
        raise ValueError("timeout debe ser mayor o igual que cero")

    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    deadline = time.monotonic() + timeout
    acquired = False
    try:
        while not acquired:
            try:
                handle.seek(0)
                _acquire_file_lock(handle)
                acquired = True
            except OSError:
                if time.monotonic() >= deadline:
                    raise StorageLockTimeout(f"Timeout al adquirir lock {lock_path}")
                time.sleep(0.01)
        yield
    finally:
        if acquired:
            _release_file_lock(handle)
        handle.close()


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Replace path atomically without exposing a partial destination."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _serialize_parquet(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _dataset_lock_path(name: str, data_dir: Path) -> Path:
    return data_dir / ".locks" / f"{name}.lock"


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def dataset_lock_path(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Public accessor for the lock path `save_dataset` uses internally,
    so callers that need to protect a load→modify→save cycle spanning
    multiple `data_ingestion.storage` calls (e.g.
    `human_feedback.registry.update_feedback_log_atomically`, F-09) can
    acquire the *same* lock without duplicating the naming scheme."""
    return _dataset_lock_path(name, data_dir)


def save_dataset(name: str, df: pd.DataFrame, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{name}.parquet"
    content = _serialize_parquet(df)
    with interprocess_lock(_dataset_lock_path(name, data_dir)):
        atomic_write_bytes(path, content)
    return path


def load_dataset(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset '{name}' en {data_dir}")
    return pd.read_parquet(path)


def get_dataset_fingerprint(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> tuple[float, int]:
    """Devuelve una huella barata (fecha de modificación, tamaño en
    bytes) del archivo de `name`, sin leer su contenido. Cambia si y
    solo si el archivo fue reescrito con `save_dataset`. Sirve como
    clave económica de invalidación de caché o cambio, no como
    identidad de contenido: dos archivos distintos pueden compartir
    tamaño y fecha de modificación por coincidencia.
    """
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset '{name}' en {data_dir}")
    stat = path.stat()
    return (stat.st_mtime, stat.st_size)


def get_dataset_path(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Ruta del archivo Parquet que persiste el dataset `name`, para los
    escasos casos que necesitan su contenido binario exacto (p. ej.
    `human_feedback.lineage.compute_dataset_sha256`) en vez de leerlo
    como DataFrame. No usar para lectura tabular — para eso, `load_dataset`.
    """
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset '{name}' en {data_dir}")
    return path


@dataclass(frozen=True)
class DatasetSnapshot:
    """DataFrame y `dataset_sha256` derivados de la MISMA captura de bytes
    del dataset — nunca de dos lecturas independientes del archivo, que
    podrían ver contenido distinto si el archivo cambia entre medio.
    `cache_fingerprint` ((mtime, size) al momento de la captura) sigue
    siendo únicamente la clave económica de invalidación de caché
    (`get_dataset_fingerprint`); `dataset_sha256` es la provenance
    verificable del contenido exacto usado para construir `dataframe`.
    """

    dataframe: pd.DataFrame
    dataset_sha256: str
    cache_fingerprint: tuple[float, int]
    content: bytes = b""


def load_dataset_snapshot(
    name: str, data_dir: Path = DEFAULT_DATA_DIR, chunk_size: int = 1024 * 1024
) -> DatasetSnapshot:
    """Captura una única instantánea inmutable de bytes del dataset `name`
    y deriva de ella tanto el `DataFrame` como su `dataset_sha256`: ambos
    se construyen a partir del mismo contenido leído una sola vez, así que
    no pueden divergir (a diferencia de leer el archivo por separado para
    cada uno). Aborta con `RuntimeError` si el archivo cambió (según
    `(mtime, size)`) entre el momento en que se empezó y se terminó de
    leer, en vez de devolver silenciosamente una instantánea potencialmente
    inconsistente.
    """
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset '{name}' en {data_dir}")

    stat_before = path.stat()
    content = path.read_bytes()
    stat_after = path.stat()
    fingerprint_before = (stat_before.st_mtime, stat_before.st_size)
    fingerprint_after = (stat_after.st_mtime, stat_after.st_size)
    if fingerprint_before != fingerprint_after:
        raise RuntimeError(
            f"El dataset '{name}' cambió mientras se leía; no se puede garantizar una "
            "instantánea estable. Repetir la solicitud."
        )

    digest = hashlib.sha256()
    view = memoryview(content)
    for offset in range(0, len(view), chunk_size):
        digest.update(view[offset : offset + chunk_size])

    dataframe = pd.read_parquet(io.BytesIO(content))
    return DatasetSnapshot(
        dataframe=dataframe,
        dataset_sha256=digest.hexdigest(),
        cache_fingerprint=fingerprint_after,
        content=content,
    )


def _append_reading_locked(name: str, new_row: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{name}.parquet"
    with interprocess_lock(_dataset_lock_path(name, data_dir)):
        try:
            existing = load_dataset(name, data_dir=data_dir)
            updated = pd.concat([existing, new_row], ignore_index=True)
        except FileNotFoundError:
            updated = new_row
        updated = updated.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)
        updated = updated.drop_duplicates(subset=TIMESTAMP_COLUMN, keep="last").reset_index(
            drop=True
        )
        content = _serialize_parquet(updated)
        atomic_write_bytes(path, content)
        return pd.read_parquet(io.BytesIO(content))


def append_reading(name: str, row: dict, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Agrega `row` (un dict con al menos `timestamp`) como una fila
    nueva al dataset `name`, normalizada al esquema completo. Crea el
    dataset si todavía no existe. Si ya existe una fila con el mismo
    timestamp (mismo día), la reemplaza en vez de duplicarla. Devuelve
    el dataset actualizado, ya guardado, ordenado por `timestamp`.
    """
    provenance = row.get(PROVENANCE_COLUMN, "real")
    new_row = normalize_to_schema(pd.DataFrame([row]), provenance=provenance)
    return _append_reading_locked(name, new_row, data_dir)
