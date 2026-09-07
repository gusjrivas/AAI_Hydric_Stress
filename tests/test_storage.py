import re
import time
from pathlib import Path

import pandas as pd
import pytest

from data_ingestion.storage import (
    get_dataset_fingerprint,
    load_dataset,
    load_dataset_snapshot,
    save_dataset,
)


def test_save_and_load_roundtrip(tmp_path):
    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})

    save_dataset("mi_dataset", df, data_dir=tmp_path)
    loaded = load_dataset("mi_dataset", data_dir=tmp_path)

    pd.testing.assert_frame_equal(loaded, df)


def test_load_missing_dataset_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset("no_existe", data_dir=tmp_path)


def test_get_dataset_fingerprint_changes_when_dataset_is_rewritten(tmp_path):
    from data_ingestion.storage import get_dataset_fingerprint

    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("mi_dataset", df, data_dir=tmp_path)
    fingerprint_before = get_dataset_fingerprint("mi_dataset", data_dir=tmp_path)

    time.sleep(0.05)
    df2 = pd.DataFrame(
        {"timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]), "temperature": [25.0, 26.0]}
    )
    save_dataset("mi_dataset", df2, data_dir=tmp_path)
    fingerprint_after = get_dataset_fingerprint("mi_dataset", data_dir=tmp_path)

    assert fingerprint_before != fingerprint_after


def test_get_dataset_fingerprint_stable_without_changes(tmp_path):
    from data_ingestion.storage import get_dataset_fingerprint

    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("mi_dataset", df, data_dir=tmp_path)

    fingerprint_1 = get_dataset_fingerprint("mi_dataset", data_dir=tmp_path)
    fingerprint_2 = get_dataset_fingerprint("mi_dataset", data_dir=tmp_path)

    assert fingerprint_1 == fingerprint_2


def test_get_dataset_fingerprint_raises_when_dataset_missing(tmp_path):
    from data_ingestion.storage import get_dataset_fingerprint

    with pytest.raises(FileNotFoundError):
        get_dataset_fingerprint("no_existe", data_dir=tmp_path)


def test_append_reading_creates_dataset_when_missing(tmp_path):
    from data_ingestion.storage import append_reading

    row = {"timestamp": pd.Timestamp("2026-01-01"), "temperature": 25.0, "origen": "real"}

    updated = append_reading("nuevo_dataset", row, data_dir=tmp_path)

    assert len(updated) == 1
    assert updated.loc[0, "temperature"] == 25.0
    assert updated.loc[0, "origen"] == "real"
    reloaded = load_dataset("nuevo_dataset", data_dir=tmp_path)
    pd.testing.assert_frame_equal(reloaded, updated)


def test_append_reading_adds_row_to_existing_dataset(tmp_path):
    from data_ingestion.storage import append_reading

    existing = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("con_historia", existing, data_dir=tmp_path)

    row = {"timestamp": pd.Timestamp("2026-01-02"), "temperature": 26.0, "origen": "real"}
    updated = append_reading("con_historia", row, data_dir=tmp_path)

    assert len(updated) == 2
    assert list(updated["timestamp"]) == list(pd.to_datetime(["2026-01-01", "2026-01-02"]))


def test_append_reading_sorts_by_timestamp_even_if_out_of_order(tmp_path):
    from data_ingestion.storage import append_reading

    existing = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-05"]), "temperature": [25.0]})
    save_dataset("desordenado", existing, data_dir=tmp_path)

    row = {"timestamp": pd.Timestamp("2026-01-02"), "temperature": 20.0, "origen": "real"}
    updated = append_reading("desordenado", row, data_dir=tmp_path)

    assert list(updated["timestamp"]) == list(pd.to_datetime(["2026-01-02", "2026-01-05"]))


def test_append_reading_replaces_row_for_same_timestamp(tmp_path):
    from data_ingestion.storage import append_reading

    row1 = {"timestamp": pd.Timestamp("2026-01-01"), "temperature": 25.0, "origen": "real"}
    append_reading("mismo_dia", row1, data_dir=tmp_path)

    row2 = {"timestamp": pd.Timestamp("2026-01-01"), "temperature": 30.0, "origen": "real"}
    updated = append_reading("mismo_dia", row2, data_dir=tmp_path)

    assert len(updated) == 1
    assert updated.loc[0, "temperature"] == 30.0


def test_load_dataset_snapshot_dataframe_and_sha_are_valid_and_consistent(tmp_path):
    """R2: el DataFrame y el SHA-256 de la instantánea corresponden al
    mismo contenido, y `cache_fingerprint` sigue siendo la clave (mtime,
    size) de `get_dataset_fingerprint` — el SHA no la reemplaza."""
    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("snapshot_valido", df, data_dir=tmp_path)

    snapshot = load_dataset_snapshot("snapshot_valido", data_dir=tmp_path)

    pd.testing.assert_frame_equal(snapshot.dataframe, df)
    assert re.fullmatch(r"[0-9a-f]{64}", snapshot.dataset_sha256)
    assert snapshot.cache_fingerprint == get_dataset_fingerprint(
        "snapshot_valido", data_dir=tmp_path
    )


def test_load_dataset_snapshot_sha_matches_manual_file_hash(tmp_path):
    """El SHA de la instantánea coincide con el hash calculado
    manualmente sobre los bytes reales del archivo — no es un hash de una
    representación reconstruida del DataFrame."""
    import hashlib

    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("hash_manual", df, data_dir=tmp_path)
    path = tmp_path / "hash_manual.parquet"
    expected = hashlib.sha256(path.read_bytes()).hexdigest()

    snapshot = load_dataset_snapshot("hash_manual", data_dir=tmp_path)

    assert snapshot.dataset_sha256 == expected


def test_load_dataset_snapshot_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset_snapshot("no_existe", data_dir=tmp_path)


def test_load_dataset_snapshot_distinguishes_different_content(tmp_path):
    """Dos datasets con contenido distinto nunca deben producir el mismo
    SHA — cada instantánea (DataFrame + SHA) corresponde inequívocamente
    a su propio contenido, sin depender de que (mtime, size) coincidan o
    no entre archivos."""
    df_a = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    df_b = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [99.0]})
    save_dataset("contenido_a", df_a, data_dir=tmp_path)
    save_dataset("contenido_b", df_b, data_dir=tmp_path)

    snapshot_a = load_dataset_snapshot("contenido_a", data_dir=tmp_path)
    snapshot_b = load_dataset_snapshot("contenido_b", data_dir=tmp_path)

    assert snapshot_a.dataset_sha256 != snapshot_b.dataset_sha256
    pd.testing.assert_frame_equal(snapshot_a.dataframe, df_a)
    pd.testing.assert_frame_equal(snapshot_b.dataframe, df_b)


def test_load_dataset_snapshot_aborts_when_file_changes_during_read(tmp_path, monkeypatch):
    """R2: si el archivo cambia entre el momento en que empieza y termina
    de leerse (sustitución concurrente simulada), la captura no es
    estable y debe abortar en vez de devolver un DataFrame y un SHA
    potencialmente inconsistentes entre sí."""
    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("mutable", df, data_dir=tmp_path)
    target_path = tmp_path / "mutable.parquet"
    original_read_bytes = Path.read_bytes

    def flaky_read_bytes(self, *args, **kwargs):
        content = original_read_bytes(self, *args, **kwargs)
        if self == target_path:
            # Simula una escritura concurrente justo después de leer los
            # bytes originales, antes de que se vuelva a mirar el (mtime,
            # size) del archivo.
            time.sleep(0.01)
            df2 = pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                    "temperature": [25.0, 26.0],
                }
            )
            save_dataset("mutable", df2, data_dir=tmp_path)
        return content

    monkeypatch.setattr(Path, "read_bytes", flaky_read_bytes)

    with pytest.raises(RuntimeError):
        load_dataset_snapshot("mutable", data_dir=tmp_path)
