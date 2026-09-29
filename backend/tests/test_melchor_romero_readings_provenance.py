"""F02 (independent-review follow-up to F01/PR#228): the real HTTP
`/sensors/{sensor_id}/historical/{as_of_date}/readings` response, over the
REAL, already-committed Melchor Romero dataset persisted through
`data_ingestion.storage.save_dataset` into a temporary `--data-dir`, must
label 2024-10-26 (missing in the source, forward-filled from 2024-10-25) as
imputed -- never as an unqualified real observation -- through the actual
API surface the frontend consumes, not just through `data_ingestion.history
.query_readings` in isolation (already covered by `tests/test_history.py`).

Deliberately narrow: builds the daily frame once
(`build_daily_frame_from_repo_dataset`, the same read-only, already-verified
helper `scripts/prepare_melchor_romero_historical_demo.py` uses) and reads
it back through the readings route. Never calls `run_demo`/`run_demo_from_
frame` (no model training, no bundle export, no scientific emission) and
never prepares a forecast batch -- the readings route needs neither."""

from __future__ import annotations

from datetime import date

import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.storage import save_dataset
from experiment_runner.melchor_romero_historical_demo_runner import (
    build_daily_frame_from_repo_dataset,
)

SENSOR_ID = "melchor-romero-demo-provenance-http"


@pytest.fixture(scope="module")
def real_frame():
    frame, dataset_sha256 = build_daily_frame_from_repo_dataset()
    return frame, dataset_sha256


@pytest.fixture
def client(tmp_path, real_frame):
    frame, _ = real_frame
    persisted = frame.copy()
    # Dataset-level provenance ("this really is the real Melchor Romero
    # dataset"): the same `origen="real"` value
    # `prepare_melchor_romero_historical_demo.py` sets, distinct from the
    # per-value `<variable>_imputado` columns `frame` already carries
    # (preserved here, never dropped).
    persisted["origen"] = "real"
    save_dataset(f"sensor__{SENSOR_ID}", persisted, data_dir=tmp_path)

    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_the_real_readings_http_response_identifies_the_imputed_day_and_the_real_values_around_it(
    client,
):
    response = client.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{date(2024, 10, 27).isoformat()}/readings",
        params={"days": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"

    by_date = {row["date"]: row for row in body["rows"]}
    day_25, day_26, day_27 = by_date["2024-10-25"], by_date["2024-10-26"], by_date["2024-10-27"]

    # Real values from the versioned source (data/melchor_romero_2024_consolidado.parquet).
    assert day_25["soil_moisture"] == pytest.approx(0.3632737398)
    assert day_25["imputed_variables"] == []
    assert day_25["unverified_variables"] == []
    assert day_25["origin"] == "real"

    assert day_27["soil_moisture"] == pytest.approx(0.3295690119)
    assert day_27["imputed_variables"] == []
    assert day_27["unverified_variables"] == []
    assert day_27["origin"] == "real"

    # 26/10: the source has no observation for this day; the prepared
    # frame forward-fills it from 25/10 (same numeric value) -- it must be
    # returned but explicitly identified as imputed, never as an
    # independent real observation.
    assert day_26["soil_moisture"] == pytest.approx(0.3632737398)
    assert day_26["imputed_variables"] == ["soil_moisture"]
    assert day_26["unverified_variables"] == []
    assert "imputed:soil_moisture" in day_26["quality_flags"]
    assert day_26["origin"] == "real"

    soil_coverage = next(
        item for item in body["variable_coverage"] if item["variable"] == "soil_moisture"
    )
    assert soil_coverage["imputed_days"] >= 1
    assert soil_coverage["unverified_days"] == 0
