"""F02 follow-up (PR #228, second round of review): a prepared frame for
the exact sensor `melchor-romero-demo` that is MISSING one or all of its
required `<variable>_imputado` flag columns entirely (not merely null on a
given row) must never fall back to `VARIABLE_STATE_OBSERVED`. This sensor
is explicitly listed in `REQUIRED_IMPUTATION_FLAGS_BY_SENSOR`
(`src/data_ingestion/history.py`) -- an absent column for one of its
required variables means the treatment of that value cannot be verified,
never that it was observed.

Deliberately narrow: reads back the real, versioned Melchor Romero source
(`build_daily_frame_from_repo_dataset`) through the real HTTP readings
route, over a temporary `--data-dir`. No model training, no bundle export,
no forecast emission, no frozen evidence touched.
"""

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

# The exact sensor_id key `REQUIRED_IMPUTATION_FLAGS_BY_SENSOR` associates
# with soil_moisture/relative_humidity/solar_radiation -- never a
# look-alike id, since the association is deliberately exact-match only.
SENSOR_ID = "melchor-romero-demo"


@pytest.fixture(scope="module")
def real_frame():
    frame, _dataset_sha256 = build_daily_frame_from_repo_dataset()
    return frame


def _make_client(tmp_path, frame):
    persisted = frame.copy()
    persisted["origen"] = "real"
    save_dataset(f"sensor__{SENSOR_ID}", persisted, data_dir=tmp_path)

    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    return TestClient(app)


@pytest.mark.parametrize(
    "dropped_columns",
    [
        pytest.param(["soil_moisture_imputado"], id="only_soil_moisture_imputado_missing"),
        pytest.param(
            ["soil_moisture_imputado", "relative_humidity_imputado", "solar_radiation_imputado"],
            id="all_three_required_imputado_columns_missing",
        ),
    ],
)
def test_missing_imputation_flag_column_is_unverified_not_observed(
    tmp_path, real_frame, dropped_columns
):
    frame = real_frame.drop(columns=dropped_columns)
    assert not any(column in frame.columns for column in dropped_columns)

    client = _make_client(tmp_path, frame)
    try:
        with client:
            response = client.get(
                f"/api/v2/sensors/{SENSOR_ID}/historical/"
                f"{date(2024, 10, 26).isoformat()}/readings",
                params={"days": 1},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"

    day_26 = next(row for row in body["rows"] if row["date"] == "2024-10-26")

    # The prepared (forward-filled) value is still returned -- never
    # silently dropped -- but is neither an unqualified real observation
    # nor a confirmed imputation.
    assert day_26["soil_moisture"] is not None
    assert "soil_moisture" not in day_26["imputed_variables"]
    assert "soil_moisture" in day_26["unverified_variables"]
    assert "unverified_provenance:soil_moisture" in day_26["quality_flags"]
    # Dataset-level provenance (`origin`) is a distinct concept from
    # per-value treatment: this really is the real, versioned Melchor
    # Romero dataset, so `origin` stays "real" regardless of whether this
    # specific value's imputation treatment could be verified.
    assert day_26["origin"] == "real"

    soil_coverage = next(
        item for item in body["variable_coverage"] if item["variable"] == "soil_moisture"
    )
    assert soil_coverage["observed_days"] == 0
    assert soil_coverage["imputed_days"] == 0
    assert soil_coverage["unverified_days"] == 1
