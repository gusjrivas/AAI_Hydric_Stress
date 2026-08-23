import pandas as pd
import pytest
import time

from data_ingestion.storage import load_dataset, save_dataset


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
