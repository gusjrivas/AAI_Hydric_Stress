"""Historical walkthrough of the Hito 2 ensemble demo bundle over a short
consecutive window of 2023, through the real, unmodified producer v2 API --
synthetic data only (mirrors the real walkthrough already run once against
the real Pergamino CSVs and the real bundles; see
docs/design/ensemble-historical-walkthrough-report-2026-09-26.md).

Never a second replay system: "moving the clock" here means calling the
same real emission endpoint with progressively later snapshots and reading
the already-persisted, immutable result back -- exactly the mechanism
`OperationalRepository.emit_snapshot`/`record_batch` already provides and
Hito 2's real execution already verified end to end.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.dependencies import get_producer_bundle_root
from app.main import app
from fastapi.testclient import TestClient

from data_ingestion.storage import save_dataset
from experiment_runner.pergamino_ensemble_demo_runner import (
    FIRST_ADMISSIBLE_DATE,
    INGESTION_END,
    INGESTION_START,
    run_demo_from_frame,
)

SENSOR_ID = "pergamino-ensemble-demo-walkthrough"
EXTERNAL_REANALYSIS_ORIGEN = "external_reanalysis_era5_nasa_power"
# Window selection rule (registered before consulting any prediction): a
# short, consecutive window fully inside the demonstration year 2023,
# centered on 2023-06-15 (the single date used for Hito 2's own real check),
# chosen only for full lookback availability and distance from either 2023
# edge -- never for a particular alert/disagreement outcome.
WINDOW_DAYS = [date(2023, 6, 13) + timedelta(days=i) for i in range(5)]  # 06-13..06-17


def _synthetic_daily_frame() -> pd.DataFrame:
    start = date.fromisoformat(INGESTION_START)
    end = date.fromisoformat(INGESTION_END)
    n_days = (end - start).days + 1
    dates = pd.date_range(start=start, periods=n_days, freq="D")
    day = np.arange(n_days)
    rng = np.random.default_rng(20260927)
    soil_moisture = 0.5 + 0.25 * np.sin(2 * np.pi * day / 365.25) + rng.normal(0, 0.03, n_days)
    rh2m = 60 + 15 * np.cos(2 * np.pi * day / 30) + rng.normal(0, 2.0, n_days)
    allsky = 20 + 8 * np.sin(2 * np.pi * day / 90 + 1.0) + rng.normal(0, 1.0, n_days)
    return pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": np.clip(soil_moisture, 0.05, 0.95),
            "relative_humidity": rh2m,
            "solar_radiation": allsky,
        }
    )


@pytest.fixture(scope="module")
def bundle_root(tmp_path_factory):
    frame = _synthetic_daily_frame()
    dataset_sha256 = hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()
    root = tmp_path_factory.mktemp("pergamino_walkthrough_bundles")
    run_demo_from_frame(frame, dataset_sha256, root, sensor_id=SENSOR_ID, horizons=(1, 2, 3))
    return root, frame


def _bundle_file_hashes(root) -> dict[str, str]:
    hashes = {}
    for path in sorted((root / SENSOR_ID).rglob("*.joblib")):
        hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


@pytest.fixture
def client(tmp_path, bundle_root):
    root, _ = bundle_root
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: root
    try:
        with TestClient(app) as test_client:
            yield test_client, tmp_path
    finally:
        app.dependency_overrides.clear()


def _emit_for_day(client, tmp_path, frame, day):
    emission_frame = frame.loc[pd.to_datetime(frame["timestamp"]).dt.date <= day].copy()
    emission_frame["origen"] = EXTERNAL_REANALYSIS_ORIGEN
    save_dataset(f"sensor__{SENSOR_ID}", emission_frame, data_dir=tmp_path)
    key = f"walkthrough-{day.isoformat()}"
    first = client.post(
        f"/api/v2/sensors/{SENSOR_ID}/forecasts", headers={"Idempotency-Key": key}, json={}
    )
    return first


def test_walkthrough_window_stays_inside_2023_with_coherent_ensemble_detail(client, bundle_root):
    http, tmp_path = client
    _, frame = bundle_root
    assert date.fromisoformat(FIRST_ADMISSIBLE_DATE) < WINDOW_DAYS[0]

    for day in WINDOW_DAYS:
        response = _emit_for_day(http, tmp_path, frame, day)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["provenance"] == "external_reanalysis"
        assert body["as_of_date"] == day.isoformat()
        for horizon in (1, 2, 3):
            slot = next(s for s in body["slots"] if s["horizon_days"] == horizon)
            assert slot["status"] == "available", slot.get("reason_code")
            target_date = date.fromisoformat(slot["target_date"])
            assert target_date.year == 2023
            assert target_date == day + timedelta(days=horizon)
            # Combined alert and vote category are separate concepts: never
            # conflated, and the top-level `alert` always mirrors the
            # combined decision, never the vote category.
            assert slot["alert"] == slot["ensemble"]["combined_alert"]
            assert slot["ensemble"]["agreement_category"] in (
                "alerta_por_unanimidad",
                "posible_alerta_acuerdo_parcial",
                "sin_alerta_por_mayoria_con_discrepancia",
                "sin_alerta_por_unanimidad",
            )
            assert slot["display_probability"] is None
            assert slot["probability_status"] == "not_qualified"


def test_repeating_the_same_day_returns_the_original_response_without_recomputing(
    client, bundle_root
):
    """Moving the clock forward and back to an already-emitted day must
    return the stored result, never re-run the models."""
    http, tmp_path = client
    _, frame = bundle_root
    day = WINDOW_DAYS[0]

    first = _emit_for_day(http, tmp_path, frame, day)
    before_hashes = _bundle_file_hashes(bundle_root[0])
    replay = _emit_for_day(http, tmp_path, frame, day)
    after_hashes = _bundle_file_hashes(bundle_root[0])

    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert before_hashes == after_hashes  # the bundle files themselves never change


def test_readings_never_reveal_observations_beyond_the_simulated_clock(client, bundle_root):
    http, tmp_path = client
    _, frame = bundle_root
    # Persist the full window's worth of observations once (as if they had
    # already happened, retrospectively) -- the `end` query parameter is
    # what actually simulates the clock for readings, independent of
    # emission.
    full_frame = frame.loc[pd.to_datetime(frame["timestamp"]).dt.date <= WINDOW_DAYS[-1]].copy()
    full_frame["origen"] = EXTERNAL_REANALYSIS_ORIGEN
    save_dataset(f"sensor__{SENSOR_ID}", full_frame, data_dir=tmp_path)

    previous_max_date = None
    for day in WINDOW_DAYS:
        response = http.get(
            f"/api/v2/sensors/{SENSOR_ID}/readings", params={"days": 10, "end": day.isoformat()}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["provenance"] == "external_reanalysis"
        assert all(row["origin"] == "external_reanalysis" for row in body["rows"])
        row_dates = [date.fromisoformat(row["date"]) for row in body["rows"]]
        assert all(d <= day for d in row_dates), f"a row after {day} leaked into the reveal"
        max_date = max(row_dates) if row_dates else None
        if previous_max_date is not None and max_date is not None:
            assert (
                max_date >= previous_max_date
            )  # monotonically non-decreasing as the clock advances
        previous_max_date = max_date


def test_historical_feedback_confirms_the_combined_decision_not_the_vote_category(
    client, bundle_root
):
    """Feedback in the historical context refers to the binary combined
    decision (`alert`/`combined_alert`), never the vote category -- and is
    explicitly tagged as a technical test, never presented as a real
    producer/expert opinion. Also verifies it never touches the bundle
    files (no recalibration from historical feedback)."""
    http, tmp_path = client
    _, frame = bundle_root
    day = WINDOW_DAYS[0]

    response = _emit_for_day(http, tmp_path, frame, day)
    body = response.json()
    slot1 = next(s for s in body["slots"] if s["horizon_days"] == 1)
    forecast_id = slot1["forecast_id"]

    before_hashes = _bundle_file_hashes(bundle_root[0])
    review = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/forecasts/{forecast_id}/reviews",
        json={
            "request_id": "walkthrough-technical-test-1",
            "expected_revision": 0,
            "action": "confirm",
            "comment": (
                "PRUEBA TECNICA (verificacion de contrato de recorrido historico) "
                "-- no es feedback real de un productor ni de un experto."
            ),
        },
    )
    after_hashes = _bundle_file_hashes(bundle_root[0])

    assert review.status_code == 201
    assert before_hashes == after_hashes  # historical feedback never recalibrates/retrains

    document_paths = list((tmp_path / "ui_metadata").glob(f"*{SENSOR_ID}*.json"))
    assert document_paths
    document = json.loads(document_paths[0].read_text())
    review_event = document["reviews"][forecast_id][0]
    # observed_label must mirror the combined decision (alert), never the
    # minority/majority vote category.
    assert review_event["observed_label"] == slot1["ensemble"]["combined_alert"]
    assert "PRUEBA TECNICA" in review_event["comment"]
