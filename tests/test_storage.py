import pandas as pd
import pytest

from data_ingestion.storage import load_dataset, save_dataset


def test_save_and_load_roundtrip(tmp_path):
    df = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})

    save_dataset("mi_dataset", df, data_dir=tmp_path)
    loaded = load_dataset("mi_dataset", data_dir=tmp_path)

    pd.testing.assert_frame_equal(loaded, df)


def test_load_missing_dataset_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset("no_existe", data_dir=tmp_path)
