from datetime import date

import pandas as pd

from data_ingestion.ingest import run_ingestion
from data_ingestion.schema import normalize_to_schema
from data_ingestion.storage import load_dataset


def _fake_fetch(latitude, longitude, start, end):
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2025-01-01", "2025-01-02"]),
                "temperature": [20.0, 21.5],
                "relative_humidity": [60.0, 62.0],
                "precipitation": [0.0, 3.2],
                "solar_radiation": [18.0, 17.5],
                "wind_speed": [2.1, 2.4],
            }
        ),
        provenance="real",
    )


def test_run_ingestion_saves_dataset_coverage_and_dictionary(tmp_path):
    data_dir = tmp_path / "data"
    dictionaries_dir = tmp_path / "dictionaries"

    result = run_ingestion(
        fetch_fn=_fake_fetch,
        name="nasa_power_la_plata_2025",
        latitude=-34.92,
        longitude=-57.95,
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
        data_dir=data_dir,
        dictionaries_dir=dictionaries_dir,
    )

    saved = load_dataset("nasa_power_la_plata_2025", data_dir=data_dir)
    assert len(saved) == 2

    coverage = pd.read_csv(result["coverage_path"])
    temperature_row = coverage[coverage["column"] == "temperature"].iloc[0]
    assert temperature_row["completeness_pct"] == 100.0

    dictionary_path = dictionaries_dir / "nasa_power_la_plata_2025.json"
    assert dictionary_path.exists()
    assert result["dictionary_path"] == dictionary_path
