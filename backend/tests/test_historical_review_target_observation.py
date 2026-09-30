"""Elegibilidad de la revisión del recorrido histórico: además del reloj
simulado, exige una observación de la variable objetivo (humedad del suelo)
en su propia fecha, con procedencia verificada. Un valor imputado, ausente o
de procedencia no verificada no habilita la revisión (GET y POST), aunque su
fecha ya haya pasado. Solo el recorrido histórico: el feedback operativo no
cambia.

Datos sintéticos y el identificador `melchor-romero-demo`, que exige
marcadores de imputación (`REQUIRED_IMPUTATION_FLAGS_BY_SENSOR`).
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
from app.routers import producer_v2
from fastapi.testclient import TestClient

from data_ingestion.history import HistoryError
from data_ingestion.storage import save_dataset
from experiment_runner.pergamino_ensemble_demo_runner import (
    INGESTION_END,
    INGESTION_START,
    run_demo_from_frame,
)

SENSOR_ID = "melchor-romero-demo"
DAY_A = date(2023, 6, 13)
TARGET = DAY_A + timedelta(days=1)  # objetivo del horizonte +1
FLAG_VARIABLES = ("soil_moisture", "relative_humidity", "solar_radiation")


def _synthetic_frame() -> pd.DataFrame:
    start = date.fromisoformat(INGESTION_START)
    end = date.fromisoformat(INGESTION_END)
    n_days = (end - start).days + 1
    dates = pd.date_range(start=start, periods=n_days, freq="D")
    day = np.arange(n_days)
    rng = np.random.default_rng(20260929)
    frame = pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": np.clip(
                0.5 + 0.25 * np.sin(2 * np.pi * day / 365.25) + rng.normal(0, 0.03, n_days),
                0.05,
                0.95,
            ),
            "relative_humidity": 60
            + 15 * np.cos(2 * np.pi * day / 30)
            + rng.normal(0, 2.0, n_days),
            "solar_radiation": 20
            + 8 * np.sin(2 * np.pi * day / 90 + 1.0)
            + rng.normal(0, 1.0, n_days),
        }
    )
    for variable in FLAG_VARIABLES:
        frame[f"{variable}_imputado"] = False
    frame["origen"] = "real"
    return frame


@pytest.fixture(scope="module")
def module_state(tmp_path_factory):
    frame = _synthetic_frame()
    base = frame[[c for c in frame.columns if not c.endswith("_imputado") and c != "origen"]]
    sha = hashlib.sha256(base.to_csv(index=False).encode("utf-8")).hexdigest()
    root = tmp_path_factory.mktemp("historical_review_target_bundles")
    run_demo_from_frame(base, sha, root, sensor_id=SENSOR_ID, horizons=(1, 2, 3))
    return root, frame


@pytest.fixture
def env(tmp_path, module_state):
    root, frame = module_state
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: root
    try:
        with TestClient(app) as http:
            causal = frame.loc[pd.to_datetime(frame["timestamp"]).dt.date <= DAY_A]
            save_dataset(f"sensor__{SENSOR_ID}", causal, data_dir=tmp_path)
            response = http.post(
                f"/api/v2/sensors/{SENSOR_ID}/forecasts",
                headers={"Idempotency-Key": "prepare-a"},
                json={},
            )
            assert response.status_code == 201, response.text
            slot = next(s for s in response.json()["slots"] if s["horizon_days"] == 1)
            assert slot["target_date"] == TARGET.isoformat()
            yield http, tmp_path, frame, slot["forecast_id"]
    finally:
        app.dependency_overrides.clear()


def _reveal(tmp_path, frame, mutate=None, drop_target=False, drop_columns=()):
    """Reescribe las lecturas con los días objetivo ya observados; `mutate`
    ajusta la fila del día objetivo (marcadores, valores)."""
    full = frame.copy()
    stamp = pd.Timestamp(TARGET)
    index = full.index[pd.to_datetime(full["timestamp"]) == stamp][0]
    if mutate:
        for column, value in mutate.items():
            full[column] = (
                full[column].astype(object) if column.endswith("_imputado") else full[column]
            )
            full.at[index, column] = value
    if drop_target:
        full = full.drop(index)
    full = full.drop(columns=list(drop_columns))
    save_dataset(f"sensor__{SENSOR_ID}", full, data_dir=tmp_path)


def _card(http, revealed=TARGET):
    response = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts",
        params={"revealed_through": revealed.isoformat()},
    )
    assert response.status_code == 200, response.text
    return next(s for s in response.json()["slots"] if s["horizon_days"] == 1)["review"]


def _post(http, forecast_id, request_id="r1", expected_revision=0, at=TARGET, action="confirm"):
    return http.post(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{at.isoformat()}/forecasts/{forecast_id}/reviews",
        json={"request_id": request_id, "expected_revision": expected_revision, "action": action},
    )


def _historical_store_files(tmp_path):
    return (
        sorted(p.name for p in (tmp_path / "historical_feedback").glob("*"))
        if (tmp_path / "historical_feedback").exists()
        else []
    )


def test_observed_verified_revealed_target_allows_review(env):
    http, tmp_path, frame, forecast_id = env
    _reveal(tmp_path, frame)
    review = _card(http)
    assert review["reviewable"] is True and review["blocked_reason"] is None
    response = _post(http, forecast_id)
    assert response.status_code == 201
    assert response.json()["revision"] == 1


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"mutate": {"soil_moisture_imputado": True}}, "target_observation_imputed"),
        ({"drop_target": True}, "target_observation_missing"),
        ({"mutate": {"soil_moisture": float("nan")}}, "target_observation_missing"),
        ({"mutate": {"soil_moisture_imputado": None}}, "target_observation_unverified"),
        ({"drop_columns": ("soil_moisture_imputado",)}, "target_observation_unverified"),
    ],
    ids=["imputed", "missing-row", "missing-value", "flag-null", "flag-column-absent"],
)
def test_imputed_missing_or_unverified_target_blocks_get_and_post(env, kwargs, code):
    http, tmp_path, frame, forecast_id = env
    _reveal(tmp_path, frame, **kwargs)

    review = _card(http)
    assert review["reviewable"] is False
    assert review["blocked_reason"] == code

    response = _post(http, forecast_id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == code
    assert _historical_store_files(tmp_path) == []  # ninguna revisión persistida
    assert _card(http)["revision"] == 0


def test_auxiliary_variable_imputed_does_not_block(env):
    http, tmp_path, frame, forecast_id = env
    _reveal(
        tmp_path,
        frame,
        mutate={"relative_humidity_imputado": True, "solar_radiation_imputado": True},
    )
    assert _card(http)["reviewable"] is True
    assert _post(http, forecast_id).status_code == 201


def test_future_target_keeps_the_time_block_and_does_not_look_at_readings(env, monkeypatch):
    http, tmp_path, frame, forecast_id = env
    _reveal(tmp_path, frame, mutate={"soil_moisture_imputado": True})

    def _forbidden(*args, **kwargs):
        raise AssertionError("no debe consultar lecturas mientras el objetivo no esté revelado")

    monkeypatch.setattr(producer_v2, "query_readings", _forbidden)
    early = _card(http, revealed=DAY_A)
    assert early["reviewable"] is False and early["blocked_reason"] == "review_not_open"
    response = _post(http, forecast_id, at=DAY_A)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "review_not_open"


def test_clock_going_back_hides_a_recorded_review(env):
    http, tmp_path, frame, forecast_id = env
    _reveal(tmp_path, frame)
    assert _post(http, forecast_id).status_code == 201
    assert _card(http)["status"] == "confirmed"
    back = _card(http, revealed=DAY_A)
    assert back["blocked_reason"] == "review_not_open"
    assert back["latest_review"] is None


def test_valid_reviews_stay_idempotent_and_concurrency_controlled(env):
    http, tmp_path, frame, forecast_id = env
    _reveal(tmp_path, frame)
    first = _post(http, forecast_id, request_id="same")
    replay = _post(http, forecast_id, request_id="same")
    assert first.status_code == 201
    assert replay.status_code in (200, 201)
    assert replay.json()["revision"] == first.json()["revision"] == 1
    stale = _post(http, forecast_id, request_id="other", expected_revision=0, action="reject")
    assert stale.status_code == 409
    assert not stale.json()["error"]["code"].startswith("target_observation")
    fresh = _post(http, forecast_id, request_id="third", expected_revision=1, action="reject")
    assert fresh.status_code == 201 and fresh.json()["revision"] == 2


def test_an_existing_review_is_kept_when_the_row_is_no_longer_reviewable(env):
    http, tmp_path, frame, forecast_id = env
    _reveal(tmp_path, frame)
    assert _post(http, forecast_id).status_code == 201
    _reveal(tmp_path, frame, mutate={"soil_moisture_imputado": True})
    review = _card(http)
    assert review["reviewable"] is False
    assert review["blocked_reason"] == "target_observation_imputed"
    assert review["latest_review"]["action"] == "confirm"  # el registro se conserva
    assert review["revision"] == 1


def test_storage_failure_is_a_technical_error_not_missing_observation(env, monkeypatch):
    http, tmp_path, frame, forecast_id = env
    _reveal(tmp_path, frame)

    def _broken(*args, **kwargs):
        raise HistoryError(
            "readings_storage_unavailable", "No se pudo leer la serie del sensor.", 503
        )

    monkeypatch.setattr(producer_v2, "query_readings", _broken)
    get_response = http.get(
        f"/api/v2/sensors/{SENSOR_ID}/historical/{DAY_A.isoformat()}/forecasts",
        params={"revealed_through": TARGET.isoformat()},
    )
    assert get_response.status_code == 503
    post_response = _post(http, forecast_id)
    assert post_response.status_code == 503
    assert _historical_store_files(tmp_path) == []
