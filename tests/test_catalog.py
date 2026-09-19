import hashlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
import pytest

from data_ingestion.catalog import CatalogError, CatalogRepository
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import save_dataset


def _create_sensor_in_process(data_dir: str) -> str:
    repository = CatalogRepository(Path(data_dir))
    try:
        repository.create_sensor("sensor-shared", "Sensor compartido", None, "real")
    except CatalogError as error:
        return error.code
    return "created"


def test_catalog_persists_sector_sensor_and_primary_selection(tmp_path):
    repository = CatalogRepository(tmp_path)
    sector = repository.create_sector("  Lote norte  ", "  tomate  ")
    sensor = repository.create_sensor("sensor-a", "  Punto A  ", sector["sector_id"], "real")
    updated = repository.update_sector(
        sector["sector_id"],
        expected_revision=1,
        changes={"primary_sensor_id": sensor["sensor_id"]},
    )

    restarted = CatalogRepository(tmp_path)
    assert restarted.list_sectors() == [
        {
            **sector,
            "display_name": "Lote norte",
            "crop": "tomate",
            "primary_sensor_id": "sensor-a",
            "revision": 2,
        }
    ]
    assert restarted.list_sensors() == [
        {
            **sensor,
            "display_name": "Punto A",
        }
    ]
    assert updated["revision"] == 2


def test_catalog_rejects_stale_revision(tmp_path):
    repository = CatalogRepository(tmp_path)
    sector = repository.create_sector("Lote", None)
    repository.update_sector(
        sector["sector_id"],
        expected_revision=1,
        changes={"display_name": "Lote actualizado"},
    )

    with pytest.raises(CatalogError) as raised:
        repository.update_sector(
            sector["sector_id"],
            expected_revision=1,
            changes={"display_name": "Cambio perdido"},
        )

    assert raised.value.code == "revision_conflict"
    assert raised.value.status_code == 409


def test_adopting_legacy_series_preserves_exact_bytes(tmp_path):
    dataset_name = dataset_name_for("legacy-a")
    save_dataset(
        dataset_name,
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2026-01-01"]),
                "soil_moisture": [0.21],
                "origen": ["real"],
            }
        ),
        data_dir=tmp_path,
    )
    path = tmp_path / f"{dataset_name}.parquet"
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    repository = CatalogRepository(tmp_path)
    discovered = repository.list_sensors()
    assert discovered[0]["registered"] is False
    assert not repository.path.exists()

    adopted = repository.create_sensor("legacy-a", "Punto adoptado", None, "unknown")

    assert adopted["registered"] is True
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_catalog_operations_preserve_research_dataset_bytes(tmp_path):
    path = save_dataset(
        "melchor_romero_2024_consolidado",
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01"]),
                "soil_moisture": [0.21],
            }
        ),
        data_dir=tmp_path,
    )
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    repository = CatalogRepository(tmp_path)
    sector = repository.create_sector("Lote", None)
    repository.create_sensor("sensor-a", "Punto A", sector["sector_id"], "real")
    repository.list_sectors()
    repository.list_sensors()

    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_sensor_with_readings_cannot_be_reassigned(tmp_path):
    repository = CatalogRepository(tmp_path)
    first = repository.create_sector("Primero", None)
    second = repository.create_sector("Segundo", None)
    sensor = repository.create_sensor("sensor-a", "Punto A", first["sector_id"], "real")
    save_dataset(
        dataset_name_for("sensor-a"),
        pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"])}),
        data_dir=tmp_path,
    )

    with pytest.raises(CatalogError) as raised:
        repository.update_sensor(
            sensor["sensor_id"],
            expected_revision=1,
            changes={"sector_id": second["sector_id"]},
        )

    assert raised.value.code == "sensor_reassignment_conflict"
    assert raised.value.status_code == 409


def test_unassigned_sensor_with_readings_cannot_gain_a_sector_later(tmp_path):
    repository = CatalogRepository(tmp_path)
    sector = repository.create_sector("Lote", None)
    sensor = repository.create_sensor("sensor-a", "Punto A", None, "real")
    save_dataset(
        dataset_name_for("sensor-a"),
        pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"])}),
        data_dir=tmp_path,
    )

    with pytest.raises(CatalogError) as raised:
        repository.update_sensor(
            sensor["sensor_id"],
            expected_revision=1,
            changes={"sector_id": sector["sector_id"]},
        )

    assert raised.value.code == "sensor_reassignment_conflict"


def test_two_processes_cannot_create_the_same_sensor(tmp_path):
    with ProcessPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                _create_sensor_in_process,
                [str(tmp_path), str(tmp_path)],
                timeout=20,
            )
        )

    assert sorted(results) == ["created", "sensor_already_exists"]
    repository = CatalogRepository(tmp_path)
    assert [item["sensor_id"] for item in repository.list_sensors()] == ["sensor-shared"]


def test_catalog_rejects_invalid_sensor_id_with_typed_error(tmp_path):
    repository = CatalogRepository(tmp_path)

    with pytest.raises(CatalogError) as raised:
        repository.create_sensor("sensor.invalid", "Punto", None, "real")

    assert raised.value.code == "invalid_sensor_id"
    assert raised.value.status_code == 422
