"""Historical *reproduction* of already-prepared ensemble forecasts,
strictly separated from *preparation* (the one-time POST emission).

Reproduction here means the new `/sensors/{sensor_id}/historical/{as_of_date}/...`
routes: pure reads by an unambiguous emission date (never `target_date`),
with a clock simulated per-request (never a global override, never
affecting the live `/sensors/{sensor_id}/...` routes) -- and the one write
(historical review) still gated by that simulated clock, never by the real
wall clock.

Uses synthetic data only (never the real Pergamino CSVs or the real
bundles from PR #218/#219); see docs/design/ensemble-historical-walkthrough
-report-2026-09-26.md for the equivalent real, one-time run.
"""

from __future__ import annotations

import hashlib
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
    INGESTION_END,
    INGESTION_START,
    run_demo_from_frame,
)

SENSOR_ID = "pergamino-ensemble-demo-reproduction"
EXTERNAL_REANALYSIS_ORIGEN = "external_reanalysis_era5_nasa_power"
DAY_A = date(2023, 6, 13)
DAY_B = date(2023, 6, 14)
WINDOW_DAYS = [DAY_A + timedelta(days=i) for i in range(5)]  # 06-13..06-17


def _synthetic_daily_frame() -> pd.DataFrame:
    start = date.fromisoformat(INGESTION_START)
    end = date.fromisoformat(INGESTION_END)
    n_days = (end - start).days + 1
    dates = pd.date_range(start=start, periods=n_days, freq="D")
    day = np.arange(n_days)
    rng = np.random.default_rng(20260928)
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
    root = tmp_path_factory.mktemp("pergamino_reproduction_bundles")
    run_demo_from_frame(frame, dataset_sha256, root, sensor_id=SENSOR_ID, horizons=(1, 2, 3))
    return root, frame


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


def _prepare_day(client, tmp_path, frame, day):
    """The one-time PREPARATION step: a real POST emission. Never called
    again for the same day in this file's reproduction tests."""
    emission_frame = frame.loc[pd.to_datetime(frame["timestamp"]).dt.date <= day].copy()
    emission_frame["origen"] = EXTERNAL_REANALYSIS_ORIGEN
    save_dataset(f"sensor__{SENSOR_ID}", emission_frame, data_dir=tmp_path)
    response = client.post(
        f"/api/v2/sensors/{SENSOR_ID}/forecasts",
        headers={"Idempotency-Key": f"prepare-{day.isoformat()}"},
        json={},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_reproduction_never_invokes_inference(client, bundle_root, monkeypatch):
    """Hashes unchanged do not prove inference wasn't called -- block it
    directly: any call during reproduction fails the test immediately."""
    http, tmp_path = client
    _, frame = bundle_root

    for day in WINDOW_DAYS:
        _prepare_day(http, tmp_path, frame, day)

    def _forbidden(*args, **kwargs):
        raise AssertionError("inference must not be called during reproduction")

    monkeypatch.setattr("predictive_modeling.ensemble_bundle.predict_ensemble_bundle", _forbidden)
    monkeypatch.setattr(
        "predictive_modeling.operational_inference.predict_operational_bundle", _forbidden
    )

    # A -> B -> A navigation, reads only.
    for day in [WINDOW_DAYS[0], WINDOW_DAYS[1], WINDOW_DAYS[0], WINDOW_DAYS[-1]]:
        readings = http.get(
            f"/api/v2/sensors/{SENSOR_ID}/historical/{day.isoformat()}/readings",
            params={"days": 10},
        )
        assert readings.status_code == 200
        forecasts = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{day.isoformat()}/forecasts")
        assert forecasts.status_code == 200


def test_as_of_date_selection_is_unambiguous_across_a_to_b_to_a_navigation(client, bundle_root):
    http, tmp_path = client
    _, frame = bundle_root
    _prepare_day(http, tmp_path, frame, DAY_A)
    _prepare_day(http, tmp_path, frame, DAY_B)

    first_a = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts")
    b = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_B.isoformat()}/forecasts")
    second_a = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts")

    assert first_a.status_code == b.status_code == second_a.status_code == 200
    assert first_a.json() == second_a.json()  # A is unaffected by ever having visited B
    assert first_a.json()["as_of_date"] == DAY_A.isoformat()
    assert b.json()["as_of_date"] == DAY_B.isoformat()

    a_targets = {slot["target_date"] for slot in first_a.json()["slots"]}
    b_targets = {slot["target_date"] for slot in b.json()["slots"]}
    assert a_targets != b_targets  # emission date, never target_date, disambiguates them


def test_a_date_never_emitted_is_reported_as_not_prepared_not_as_empty_or_error(client):
    http, _ = client
    response = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{date(2023, 1, 1).isoformat()}/forecasts"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "batch_not_prepared"


def test_historical_review_is_gated_by_the_simulated_clock_not_real_now(client, bundle_root):
    http, tmp_path = client
    _, frame = bundle_root
    body = _prepare_day(http, tmp_path, frame, DAY_A)
    slot1 = next(s for s in body["slots"] if s["horizon_days"] == 1)
    assert slot1["target_date"] == (DAY_A + timedelta(days=1)).isoformat()
    forecast_id = slot1["forecast_id"]

    # Browsing DAY_A itself: the simulated clock (end of DAY_A) has not yet
    # reached the target_date (DAY_A + 1) -- must be refused, even though
    # the real wall clock (2026+) is long past it.
    too_early = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts/{forecast_id}/reviews",
        json={"request_id": "hist-review-early", "expected_revision": 0, "action": "confirm"},
    )
    assert too_early.status_code == 409
    assert too_early.json()["error"]["code"] == "review_not_open"

    # Browsing DAY_B (== the target_date): now open.
    on_time = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_B.isoformat()}/forecasts/{forecast_id}/reviews",
        json={
            "request_id": "hist-review-on-time",
            "expected_revision": 0,
            "action": "confirm",
            "comment": "PRUEBA TECNICA -- no es feedback real de un productor ni de un experto.",
        },
    )
    assert on_time.status_code == 201
    assert on_time.json()["revision"] == 1


def test_reviewing_a_later_emissions_forecast_is_refused_from_an_earlier_historical_date(
    client, bundle_root
):
    http, tmp_path = client
    _, frame = bundle_root
    _prepare_day(http, tmp_path, frame, DAY_A)
    body_b = _prepare_day(http, tmp_path, frame, DAY_B)
    forecast_id_b = next(s for s in body_b["slots"] if s["horizon_days"] == 1)["forecast_id"]

    # DAY_B's own forecast must never be reachable while browsing DAY_A --
    # moving the clock back to A must not expose B's emissions.
    response = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts/{forecast_id_b}/reviews",
        json={"request_id": "hist-review-future", "expected_revision": 0, "action": "confirm"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_not_visible_at_this_historical_date"


def test_historical_review_never_touches_the_bundle_files(client, bundle_root):
    http, tmp_path = client
    root, frame = bundle_root
    body = _prepare_day(http, tmp_path, frame, DAY_A)
    forecast_id = next(s for s in body["slots"] if s["horizon_days"] == 1)["forecast_id"]

    def _hashes():
        return {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / SENSOR_ID).rglob("*.joblib"))
        }

    before = _hashes()
    review = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_B.isoformat()}/forecasts/{forecast_id}/reviews",
        json={
            "request_id": "hist-review-isolation",
            "expected_revision": 0,
            "action": "confirm",
            "comment": "PRUEBA TECNICA -- verificacion de aislamiento, no feedback real.",
        },
    )
    assert review.status_code == 201
    after = _hashes()
    assert before == after  # historical feedback never recalibrates/retrains

    # Structural isolation, not just a comment: the historical demo's
    # feedback lives entirely under this test's own tmp_path (a data_dir
    # explicitly distinct from the operational DEFAULT_DATA_DIR), which no
    # retraining/recalibration entrypoint in this codebase auto-discovers --
    # every such entrypoint takes an explicit sensor_id + data_dir, never
    # scans a directory tree for feedback to incorporate.
    from data_ingestion.storage import DEFAULT_DATA_DIR

    assert tmp_path != DEFAULT_DATA_DIR
    assert DEFAULT_DATA_DIR not in tmp_path.parents


def test_reveal_through_2023_06_20_lets_the_06_17_horizon_3_target_be_contrasted(
    client, bundle_root
):
    """Reuses already-persisted observations and the already-prepared
    2023-06-17 emission -- never generates a new prediction."""
    http, tmp_path = client
    _, frame = bundle_root
    day = date(2023, 6, 17)
    body = _prepare_day(http, tmp_path, frame, day)
    slot3 = next(s for s in body["slots"] if s["horizon_days"] == 3)
    target_date = date.fromisoformat(slot3["target_date"])
    assert target_date == date(2023, 6, 20)

    # Save the fuller history (as if it had already happened, retrospectively)
    # so the reveal-through-06-20 readings request has something to reveal.
    full_frame = frame.loc[pd.to_datetime(frame["timestamp"]).dt.date <= target_date].copy()
    full_frame["origen"] = EXTERNAL_REANALYSIS_ORIGEN
    save_dataset(f"sensor__{SENSOR_ID}", full_frame, data_dir=tmp_path)

    revealed = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{target_date.isoformat()}/readings",
        params={"days": 10},
    )
    assert revealed.status_code == 200
    rows = revealed.json()["rows"]
    row_dates = [date.fromisoformat(r["date"]) for r in rows]
    assert target_date in row_dates
    assert all(d <= target_date for d in row_dates)  # no observation beyond the reveal date

    target_row = next(r for r in rows if r["date"] == target_date.isoformat())
    event = slot3["event_threshold"]
    assert event["variable"] == "soil_moisture"
    observed_value = target_row["soil_moisture"]
    assert observed_value is not None
    # Same comparison rule the ensemble itself uses (comparison="lt"),
    # applied here only to contrast against an already-revealed
    # observation -- never to produce a new prediction.
    assert event["comparison"] == "lt"
    observed_stress = observed_value < event["value"]
    assert isinstance(observed_stress, bool)


def test_revealed_through_walks_the_reviewable_clock_past_the_emission_date(
    client, bundle_root
):
    """UI necesita separar la emisión seleccionada (as_of_date) del punto
    del recorrido hasta el que se avanzó (revealed_through): la elegibilidad
    de revisión debe reflejar el reloj del recorrido, no la fecha de
    emisión, sin que el backend simule nada del lado del cliente."""
    http, tmp_path = client
    _, frame = bundle_root
    body = _prepare_day(http, tmp_path, frame, DAY_A)
    slot1 = next(s for s in body["slots"] if s["horizon_days"] == 1)
    target_date = date.fromisoformat(slot1["target_date"])
    assert target_date == DAY_A + timedelta(days=1) == DAY_B

    # Sin revealed_through: el reloj es el de la propia emisión (DAY_A),
    # anterior al target_date -- todavía no reviewable.
    at_emission = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts"
    )
    assert at_emission.status_code == 200
    slot_at_emission = next(
        s for s in at_emission.json()["slots"] if s["horizon_days"] == 1
    )
    assert slot_at_emission["review"]["reviewable"] is False
    assert slot_at_emission["review"]["blocked_reason"] == "review_not_open"

    # Con revealed_through == target_date: el reloj del recorrido ya
    # alcanzó el target_date -- reviewable, sin cambiar qué emisión se
    # seleccionó (sigue siendo la de DAY_A).
    walked_forward = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts",
        params={"revealed_through": target_date.isoformat()},
    )
    assert walked_forward.status_code == 200
    slot_walked = next(
        s for s in walked_forward.json()["slots"] if s["horizon_days"] == 1
    )
    assert slot_walked["review"]["reviewable"] is True
    assert slot_walked["review"]["blocked_reason"] is None
    assert slot_walked["forecast_id"] == slot_at_emission["forecast_id"]


def test_revealed_through_before_the_emission_date_is_rejected(client, bundle_root):
    http, tmp_path = client
    _, frame = bundle_root
    _prepare_day(http, tmp_path, frame, DAY_B)

    response = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_B.isoformat()}/forecasts",
        params={"revealed_through": DAY_A.isoformat()},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_reveal_window"


def test_server_today_reflects_revealed_through_not_as_of_date(client, bundle_root):
    """Regression: `server_today` used to always echo `as_of_date`, never
    the walked-forward `revealed_through` -- misreporting the clock the
    review route actually enforces."""
    http, tmp_path = client
    _, frame = bundle_root
    _prepare_day(http, tmp_path, frame, DAY_A)
    later = DAY_A + timedelta(days=3)

    without_reveal = http.get(f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts")
    assert without_reveal.json()["server_today"] == DAY_A.isoformat()

    with_reveal = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts",
        params={"revealed_through": later.isoformat()},
    )
    assert with_reveal.json()["server_today"] == later.isoformat()


def test_historical_readings_at_an_earlier_date_never_leak_a_later_last_reading_or_negative_age(
    client, bundle_root
):
    """Regression: `last_reading_date`/`data_age_days` used to be computed
    over the *whole* dataset file, ignoring the historical clock --
    browsing 2023-06-13 with data saved through 2023-06-20 must never
    report last_reading_date=2023-06-20 nor data_age_days=-7."""
    http, tmp_path = client
    _, frame = bundle_root
    later_boundary = DAY_A + timedelta(days=7)  # 2023-06-20

    full_frame = frame.loc[pd.to_datetime(frame["timestamp"]).dt.date <= later_boundary].copy()
    full_frame["origen"] = EXTERNAL_REANALYSIS_ORIGEN
    save_dataset(f"sensor__{SENSOR_ID}", full_frame, data_dir=tmp_path)

    response = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/readings",
        params={"days": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["last_reading_date"] == DAY_A.isoformat()
    assert body["data_age_days"] == 0
    row_dates = [date.fromisoformat(row["date"]) for row in body["rows"]]
    assert all(d <= DAY_A for d in row_dates)

    # Browsing forward to the later boundary now legitimately reveals it.
    later_response = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{later_boundary.isoformat()}/readings",
        params={"days": 10},
    )
    later_body = later_response.json()
    assert later_body["last_reading_date"] == later_boundary.isoformat()
    assert later_body["data_age_days"] == 0


def test_operational_review_never_changes_a_historical_cards_review_state(client, bundle_root):
    """Storage isolation, not just separate React components: a real
    review submitted through the *live* route on the same forecast_id
    must never be visible through the historical route, and a
    "prueba tecnica" historical review must never be visible through the
    live route."""
    http, tmp_path = client
    _, frame = bundle_root
    body = _prepare_day(http, tmp_path, frame, DAY_A)
    forecast_id = next(s for s in body["slots"] if s["horizon_days"] == 1)["forecast_id"]

    # A real wall-clock review through the live route (real "today" is
    # 2026+, long past this 2023 target_date, so it's legitimately open).
    live_review = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/forecasts/{forecast_id}/reviews",
        json={"request_id": "live-review-1", "expected_revision": 0, "action": "confirm"},
    )
    assert live_review.status_code == 201, live_review.text

    # The historical card for that same forecast_id must still show its
    # own (pending) state, untouched by the live review.
    historical_after_live = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts",
        params={"revealed_through": DAY_B.isoformat()},
    )
    slot = next(s for s in historical_after_live.json()["slots"] if s["horizon_days"] == 1)
    assert slot["review"]["status"] == "pending"
    assert slot["review"]["revision"] == 0

    # Submitting the historical ("prueba tecnica") review must not touch
    # the live review just recorded.
    historical_review = http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_B.isoformat()}/forecasts/{forecast_id}/reviews",
        json={
            "request_id": "hist-review-isolation",
            "expected_revision": 0,
            "action": "reject",
            "comment": "PRUEBA TECNICA -- no es feedback real de un productor ni de un experto.",
        },
    )
    assert historical_review.status_code == 201, historical_review.text
    assert historical_review.json()["status"] == "rejected"

    live_forecast = http.get(f"/api/v2/sensors/{SENSOR_ID}/forecasts/{forecast_id}")
    assert live_forecast.json()["review"]["status"] == "confirmed"
    assert live_forecast.json()["review"]["revision"] == 1
