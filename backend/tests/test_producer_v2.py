import hashlib

import pandas as pd
import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import save_dataset


@pytest.fixture
def client(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_catalog_flow_creates_sector_sensor_and_primary_selection(client):
    sector_response = client.post(
        "/api/v2/sectors",
        json={"display_name": "  Lote norte  ", "crop": "  tomate  "},
    )
    assert sector_response.status_code == 201
    sector = sector_response.json()
    assert sector["display_name"] == "Lote norte"

    sensor_response = client.post(
        "/api/v2/sensors",
        json={
            "sensor_id": "sensor-a",
            "display_name": "Punto A",
            "sector_id": sector["sector_id"],
            "source_kind": "real",
        },
    )
    assert sensor_response.status_code == 201

    patch_response = client.patch(
        f"/api/v2/sectors/{sector['sector_id']}",
        json={"expected_revision": 1, "primary_sensor_id": "sensor-a"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["primary_sensor_id"] == "sensor-a"
    assert patch_response.json()["revision"] == 2

    assert client.get("/api/v2/sectors").json()["items"][0]["sector_id"] == sector["sector_id"]
    assert (
        client.get(
            "/api/v2/sensors",
            params={"sector_id": sector["sector_id"]},
        ).json()["items"][
            0
        ]["sensor_id"]
        == "sensor-a"
    )


def test_catalog_text_limits_are_applied_after_trim(client):
    display_name = "x" * 80

    response = client.post(
        "/api/v2/sectors",
        json={"display_name": f"  {display_name}  "},
    )

    assert response.status_code == 201
    assert response.json()["display_name"] == display_name


def test_sensor_pagination_is_stable_and_cursor_is_bound_to_filters(client):
    for sensor_id in ["sensor-a", "sensor-b", "sensor-c"]:
        response = client.post(
            "/api/v2/sensors",
            json={
                "sensor_id": sensor_id,
                "display_name": sensor_id,
                "source_kind": "unknown",
            },
        )
        assert response.status_code == 201

    first = client.get("/api/v2/sensors", params={"limit": 2}).json()
    assert [item["sensor_id"] for item in first["items"]] == ["sensor-a", "sensor-b"]
    assert first["next_cursor"] is not None

    second = client.get(
        "/api/v2/sensors",
        params={"limit": 2, "cursor": first["next_cursor"]},
    )
    assert second.status_code == 200
    assert [item["sensor_id"] for item in second.json()["items"]] == ["sensor-c"]
    assert second.json()["next_cursor"] is None

    mismatched = client.get(
        "/api/v2/sensors",
        params={"sector_id": "another", "cursor": first["next_cursor"]},
    )
    assert mismatched.status_code == 422
    assert mismatched.json()["error"]["code"] == "invalid_cursor"


def test_sensor_pagination_keeps_the_initial_cutoff(client):
    for sensor_id in ["sensor-a", "sensor-b"]:
        client.post(
            "/api/v2/sensors",
            json={
                "sensor_id": sensor_id,
                "display_name": sensor_id,
                "source_kind": "unknown",
            },
        )

    first = client.get("/api/v2/sensors", params={"limit": 1}).json()
    client.post(
        "/api/v2/sensors",
        json={
            "sensor_id": "sensor-c",
            "display_name": "sensor-c",
            "source_kind": "unknown",
        },
    )
    second = client.get(
        "/api/v2/sensors",
        params={"limit": 2, "cursor": first["next_cursor"]},
    ).json()

    assert [item["sensor_id"] for item in second["items"]] == ["sensor-b"]
    assert second["next_cursor"] is None


def test_patch_validation_uses_v2_error_envelope(client):
    created = client.post(
        "/api/v2/sensors",
        json={
            "sensor_id": "sensor-a",
            "display_name": "Punto",
            "source_kind": "unknown",
        },
    )
    assert created.status_code == 201

    response = client.patch(
        "/api/v2/sensors/sensor-a",
        json={"expected_revision": 1},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_readings_adopt_legacy_series_without_changing_bytes(client, tmp_path):
    name = dataset_name_for("legacy-a")
    save_dataset(
        name,
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2026-01-01", "2026-01-03"]),
                "soil_moisture": [0.2, 0.18],
                "origen": ["real", "sintetico"],
            }
        ),
        data_dir=tmp_path,
    )
    path = tmp_path / f"{name}.parquet"
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    discovered = client.get("/api/v2/sensors").json()["items"]
    assert discovered[0]["registered"] is False

    adopted = client.post(
        "/api/v2/sensors",
        json={
            "sensor_id": "legacy-a",
            "display_name": "Punto adoptado",
            "source_kind": "unknown",
        },
    )
    assert adopted.status_code == 201

    readings = client.get(
        "/api/v2/sensors/legacy-a/readings",
        params={"days": 3, "end": "2026-01-03"},
    )
    assert readings.status_code == 200
    body = readings.json()
    assert body["missing_dates"] == ["2026-01-02"]
    assert body["rows"][1]["origin"] == "synthetic"
    assert body["snapshot_id"] == before
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_registered_sensor_without_data_and_unknown_sensor_are_distinct(client):
    created = client.post(
        "/api/v2/sensors",
        json={
            "sensor_id": "empty",
            "display_name": "Vacío",
            "source_kind": "unknown",
        },
    )
    assert created.status_code == 201

    empty = client.get("/api/v2/sensors/empty/readings", params={"days": 7})
    assert empty.status_code == 200
    assert empty.json()["status"] == "no_readings"
    assert len(empty.json()["missing_dates"]) == 7

    missing = client.get("/api/v2/sensors/unknown/readings")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "sensor_not_found"
    assert missing.json()["error"]["request_id"] == missing.headers["X-Request-ID"]


def test_v2_validation_error_does_not_change_legacy_error_shape(client):
    v2 = client.get("/api/v2/sensors", params={"limit": 0})
    assert v2.status_code == 422
    assert v2.json()["error"]["code"] == "validation_error"

    legacy = client.post(
        "/sensors/sensor.invalid/readings",
        json={"timestamp": "2026-01-01T00:00:00"},
    )
    assert legacy.status_code == 422
    assert "detail" in legacy.json()
    assert "error" not in legacy.json()


def test_reading_storage_failure_returns_typed_error(client, tmp_path):
    client.post(
        "/api/v2/sensors",
        json={
            "sensor_id": "broken",
            "display_name": "Roto",
            "source_kind": "unknown",
        },
    )
    (tmp_path / f"{dataset_name_for('broken')}.parquet").write_bytes(b"not parquet")

    response = client.get("/api/v2/sensors/broken/readings")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "readings_storage_unavailable"


def test_openapi_publishes_v2_contracts_and_keeps_legacy_routes(client):
    document = client.get("/openapi.json").json()

    assert "/api/v2/sectors" in document["paths"]
    assert "/api/v2/sensors" in document["paths"]
    assert "/api/v2/sensors/{sensor_id}/readings" in document["paths"]
    assert "/sensors/{sensor_id}/readings" in document["paths"]
    response = document["paths"]["/api/v2/sensors"]["get"]["responses"]
    assert response["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "SensorListResponse"
    )
    assert response["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ErrorResponse"
    )


def test_v2_can_be_disabled_without_affecting_legacy(tmp_path, monkeypatch):
    monkeypatch.delenv("PRODUCER_V2_ENABLED", raising=False)
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    try:
        with TestClient(app) as test_client:
            disabled = test_client.get("/api/v2/sensors")
            legacy = test_client.post(
                "/sensors/sensor-a/readings",
                json={"timestamp": "2026-01-01T00:00:00"},
            )
    finally:
        app.dependency_overrides.clear()

    assert disabled.status_code == 404
    assert disabled.json()["error"]["code"] == "resource_not_found"
    assert legacy.status_code == 200
