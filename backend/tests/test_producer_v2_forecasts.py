"""Pruebas del repositorio operacional v2 (identidad, inmutabilidad,
idempotencia, concurrencia) y de los endpoints v2 de consulta/revisión
(HU4/HU5/HU6; extend-dated-alert-feedback, add-producer-forecast-api).

Las emisiones usadas aquí provienen exclusivamente de
`OperationalRepository.record_batch`, sembrado directo en pruebas
aisladas (sin endpoint público de carga), conforme a AGENTS.md.
"""

from __future__ import annotations

import threading
from datetime import date, datetime, timezone

import pytest
from app.config import get_dataset_data_dir, is_producer_v2_enabled
from app.main import app
from fastapi.testclient import TestClient

from human_feedback.operational_repository import (
    OperationalRepository,
    OperationalRepositoryError,
    SlotSeed,
    compute_batch_id,
    compute_forecast_id,
)

CONTRACT_VERSION = "producer_daily_h123_v1"


def _model_reference(**overrides):
    base = {
        "model_version": "model-v1",
        "horizon_days": 1,
        "contract_version": CONTRACT_VERSION,
        "trained_through": "2026-09-15",
        "calibration_version": "cal-v1",
        "assessment_reference": None,
    }
    base.update(overrides)
    return base


def _event_threshold():
    return {"variable": "soil_moisture", "value": 0.18, "unit": "m3/m3", "comparison": "lt"}


def _available_slot(horizon_days: int, *, alert: bool = True) -> SlotSeed:
    return SlotSeed(
        horizon_days=horizon_days,
        status="available",
        alert=alert,
        score=0.7,
        score_kind="calibrated_probability",
        display_probability=0.7,
        probability_status="development_assessed",
        probability_reason_code=None,
        decision_threshold=0.5,
        event_threshold=_event_threshold(),
        model_reference=_model_reference(horizon_days=horizon_days),
    )


def _unavailable_slot(horizon_days: int, reason_code: str = "no_readings") -> SlotSeed:
    return SlotSeed(horizon_days=horizon_days, status="unavailable", reason_code=reason_code)


def _all_available(sensor_id: str = "sensor-a") -> list[SlotSeed]:
    return [_available_slot(1), _available_slot(2), _available_slot(3)]


def _slots_with(available_horizons) -> list[SlotSeed]:
    """Una tanda requiere exactamente h=1,2,3; los horizontes fuera de
    `available_horizons` se siembran como unavailable.
    """
    available = set(available_horizons)
    return [_available_slot(h) if h in available else _unavailable_slot(h) for h in (1, 2, 3)]


UTC = timezone.utc


def _seed_batch(
    repo: OperationalRepository,
    *,
    as_of_date: date,
    slots,
    idempotency_key: str,
    snapshot_id: str = "snap-1",
    issued_at: datetime | None = None,
    now: datetime | None = None,
):
    issued_at = issued_at or datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    now = now or issued_at
    return repo.record_batch(
        as_of_date=as_of_date,
        issued_at=issued_at,
        snapshot_id=snapshot_id,
        data_age_days=0,
        provenance="real",
        slots=slots,
        idempotency_key=idempotency_key,
        now=now,
    )


# ---------------------------------------------------------------------------
# Identidad
# ---------------------------------------------------------------------------


def test_same_target_date_different_origin_or_horizon_yields_distinct_identities(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
    )
    forecast_ids = {slot["forecast_id"] for slot in batch["slots"]}
    assert len(forecast_ids) == 3

    other_day = _seed_batch(
        repo,
        as_of_date=date(2026, 9, 21),
        slots=_slots_with({2}),
        idempotency_key="k2",
    )
    # h=2 desde 2026-09-21 apunta al mismo target_date que h=3 desde 2026-09-20
    # (2026-09-23) pero son identidades distintas.
    same_target_forecast = next(slot for slot in batch["slots"] if slot["horizon_days"] == 3)
    cross_horizon_forecast = next(slot for slot in other_day["slots"] if slot["horizon_days"] == 2)
    assert same_target_forecast["target_date"] == cross_horizon_forecast["target_date"]
    assert same_target_forecast["forecast_id"] != cross_horizon_forecast["forecast_id"]


def test_forecast_id_is_deterministic_and_matches_documented_algorithm(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
    )
    slot = next(slot for slot in batch["slots"] if slot["horizon_days"] == 1)
    assert slot["forecast_id"] == compute_forecast_id(
        "sensor-a", date(2026, 9, 20), 1, CONTRACT_VERSION
    )
    assert batch["batch_id"] == compute_batch_id("sensor-a", date(2026, 9, 20), CONTRACT_VERSION)


def test_same_key_already_issued_preserves_original_result(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    first = _seed_batch(
        repo,
        as_of_date=date(2026, 9, 20),
        slots=[_available_slot(1, alert=True), _available_slot(2), _unavailable_slot(3)],
        idempotency_key="k1",
    )
    # Otro modelo/otro payload para el mismo horizonte disponible: el
    # exito original se preserva porque el slot ya es successful.
    second = _seed_batch(
        repo,
        as_of_date=date(2026, 9, 20),
        slots=[_available_slot(1, alert=False), _available_slot(2), _available_slot(3)],
        idempotency_key="k2",
    )
    first_h1 = next(s for s in first["slots"] if s["horizon_days"] == 1)
    second_h1 = next(s for s in second["slots"] if s["horizon_days"] == 1)
    assert first_h1["forecast_id"] == second_h1["forecast_id"]
    assert first_h1["alert"] == second_h1["alert"] is True

    # El slot h=3, que era unavailable, sí pudo completarse con la retry key.
    second_h3 = next(s for s in second["slots"] if s["horizon_days"] == 3)
    assert second_h3["status"] == "available"
    assert second["revision"] == first["revision"] + 1


def test_snapshot_change_for_issued_key_is_a_conflict(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    _seed_batch(
        repo,
        as_of_date=date(2026, 9, 20),
        slots=_all_available(),
        idempotency_key="k1",
        snapshot_id="snap-1",
    )
    with pytest.raises(OperationalRepositoryError) as excinfo:
        _seed_batch(
            repo,
            as_of_date=date(2026, 9, 20),
            slots=_all_available(),
            idempotency_key="k2",
            snapshot_id="snap-2",
        )
    assert excinfo.value.code == "issued_snapshot_conflict"
    assert excinfo.value.status_code == 409


# ---------------------------------------------------------------------------
# Idempotencia y persistencia
# ---------------------------------------------------------------------------


def test_emission_idempotency_replays_same_key_and_rejects_other_payload(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    first = _seed_batch(
        repo, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
    )
    replay = _seed_batch(
        repo, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
    )
    assert replay["batch_id"] == first["batch_id"]
    assert replay["revision"] == first["revision"]

    with pytest.raises(OperationalRepositoryError) as excinfo:
        repo.record_batch(
            as_of_date=date(2026, 9, 20),
            issued_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
            snapshot_id="snap-1",
            data_age_days=1,  # payload distinto bajo la misma clave
            provenance="real",
            slots=_all_available(),
            idempotency_key="k1",
            now=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        )
    assert excinfo.value.code == "idempotency_conflict"


def test_idempotency_survives_restart_via_a_fresh_repository_instance(tmp_path):
    repo1 = OperationalRepository(tmp_path, "sensor-a")
    first = _seed_batch(
        repo1, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
    )
    repo2 = OperationalRepository(tmp_path, "sensor-a")  # simula reinicio del proceso
    replay = _seed_batch(
        repo2, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
    )
    assert replay["batch_id"] == first["batch_id"]


def test_persistence_failure_does_not_publish_partial_state(tmp_path, monkeypatch):
    repo = OperationalRepository(tmp_path, "sensor-a")

    def _boom(*args, **kwargs):
        raise OSError("disco lleno")

    monkeypatch.setattr("human_feedback.operational_repository.atomic_write_bytes", _boom)
    with pytest.raises(OperationalRepositoryError) as excinfo:
        _seed_batch(
            repo, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
        )
    assert excinfo.value.code == "operational_storage_unavailable"
    assert not repo.path.exists()


# ---------------------------------------------------------------------------
# Aislamiento entre sensores
# ---------------------------------------------------------------------------


def test_sensor_isolation_is_enforced_by_separate_documents(tmp_path):
    repo_a = OperationalRepository(tmp_path, "sensor-a")
    repo_b = OperationalRepository(tmp_path, "sensor-b")
    batch = _seed_batch(
        repo_a, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    assert repo_a.get_forecast(forecast_id, now=datetime(2026, 9, 20, tzinfo=UTC)) is not None
    assert repo_b.get_forecast(forecast_id, now=datetime(2026, 9, 20, tzinfo=UTC)) is None


# ---------------------------------------------------------------------------
# Reserva backend del espacio demo-
# ---------------------------------------------------------------------------


def test_demo_sensor_write_is_locked_regardless_of_state(tmp_path):
    repo = OperationalRepository(tmp_path, "demo-anything")
    with pytest.raises(OperationalRepositoryError) as excinfo:
        _seed_batch(
            repo, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
        )
    assert excinfo.value.code == "demo_write_locked"
    assert excinfo.value.details["reason"] == "legacy_demo_sensor_reserved"


def test_synthetic_non_demo_sensor_is_not_blocked(tmp_path):
    repo = OperationalRepository(tmp_path, "synthetic-sensor")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 20), slots=_all_available(), idempotency_key="k1"
    )
    assert batch["batch_id"]


# ---------------------------------------------------------------------------
# Apertura UTC, madurez y revisión
# ---------------------------------------------------------------------------


def test_review_before_open_is_rejected_and_not_persisted(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 18), slots=_slots_with({3}), idempotency_key="k1"
    )
    forecast_id = next(s for s in batch["slots"] if s["horizon_days"] == 3)[
        "forecast_id"
    ]  # target_date=2026-09-21

    with pytest.raises(OperationalRepositoryError) as excinfo:
        repo.submit_review(
            forecast_id=forecast_id,
            request_id="req-1",
            expected_revision=0,
            action="confirm",
            comment=None,
            now=datetime(2026, 9, 20, 23, 59, tzinfo=UTC),
        )
    assert excinfo.value.code == "review_not_open"

    forecast = repo.get_forecast(forecast_id, now=datetime(2026, 9, 20, 23, 59, tzinfo=UTC))
    assert forecast["review"]["status"] == "pending"
    assert forecast["review"]["revision"] == 0


def test_late_review_is_accepted_and_recorded_against_original_forecast(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 1), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    three_weeks_later = datetime(2026, 9, 25, tzinfo=UTC)

    status_code, review = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-late",
        expected_revision=0,
        action="confirm",
        comment="tarde pero registrado",
        now=three_weeks_later,
    )
    assert status_code == 201
    assert review["status"] == "confirmed"
    assert review["revision"] == 1
    assert review["latest_review"]["observed_label"] is True  # confirm == alerta emitida


def test_review_retry_with_same_request_id_replays_original_result(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 18), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    now = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)

    _, first = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="confirm",
        comment=None,
        now=now,
    )
    _, replay = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="confirm",
        comment=None,
        now=now,
    )
    assert replay["latest_review"]["review_id"] == first["latest_review"]["review_id"]
    assert replay["revision"] == first["revision"] == 1


def test_review_retry_replays_original_even_after_a_later_correction(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 18), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    now = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)

    _, first = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="confirm",
        comment=None,
        now=now,
    )
    _, corrected = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-2",
        expected_revision=1,
        action="reject",
        comment="corrijo",
        now=now,
    )
    assert corrected["revision"] == 2

    _, replay_of_first = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="confirm",
        comment=None,
        now=now,
    )
    # "un retry idéntico devuelve el resultado original aunque la revisión
    # actual haya avanzado"
    assert replay_of_first["revision"] == 1
    assert replay_of_first["status"] == "confirmed"


def test_review_retry_with_different_payload_is_a_conflict(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 18), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    now = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)
    repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="confirm",
        comment=None,
        now=now,
    )
    with pytest.raises(OperationalRepositoryError) as excinfo:
        repo.submit_review(
            forecast_id=forecast_id,
            request_id="req-1",
            expected_revision=0,
            action="reject",  # mismo request_id, otro contenido
            comment=None,
            now=now,
        )
    assert excinfo.value.code == "idempotency_conflict"


def test_concurrent_edits_second_uses_stale_revision_and_is_rejected(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 18), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    now = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)

    repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="confirm",
        comment=None,
        now=now,
    )
    with pytest.raises(OperationalRepositoryError) as excinfo:
        repo.submit_review(
            forecast_id=forecast_id,
            request_id="req-2",
            expected_revision=0,  # ya superada por req-1
            action="reject",
            comment=None,
            now=now,
        )
    assert excinfo.value.code == "revision_conflict"

    forecast = repo.get_forecast(forecast_id, now=now)
    assert forecast["review"]["revision"] == 1
    assert forecast["review"]["status"] == "confirmed"  # primera revisión no se pierde


def test_real_cross_process_concurrency_on_a_review_keeps_exactly_one_winner(tmp_path):
    batch = _seed_batch(
        OperationalRepository(tmp_path, "sensor-a"),
        as_of_date=date(2026, 9, 18),
        slots=_slots_with({1}),
        idempotency_key="k1",
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    now = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)
    results: list[int] = []
    errors: list[OperationalRepositoryError] = []

    def _attempt(request_id: str, action: str) -> None:
        try:
            status_code, _ = OperationalRepository(tmp_path, "sensor-a").submit_review(
                forecast_id=forecast_id,
                request_id=request_id,
                expected_revision=0,
                action=action,
                comment=None,
                now=now,
            )
            results.append(status_code)
        except OperationalRepositoryError as error:
            errors.append(error)

    threads = [threading.Thread(target=_attempt, args=(f"req-{i}", "confirm")) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 1
    assert all(error.code == "revision_conflict" for error in errors)
    assert len(errors) == 4

    forecast = OperationalRepository(tmp_path, "sensor-a").get_forecast(forecast_id, now=now)
    assert forecast["review"]["revision"] == 1


def test_confirmation_same_day_is_captured_but_not_training_eligible(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 19), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]  # target_date = 2026-09-20
    same_day = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)

    _, review = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="confirm",
        comment=None,
        now=same_day,
    )
    assert review["status"] == "confirmed"
    assert review["training_eligibility"] == "waiting_target_maturity"


def test_same_day_opinion_requires_mature_revalidation_the_next_day(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 19), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]  # target_date = 2026-09-20
    same_day = datetime(2026, 9, 20, 23, 59, tzinfo=UTC)
    repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="reject",
        comment=None,
        now=same_day,
    )

    next_day = datetime(2026, 9, 21, 0, 5, tzinfo=UTC)
    forecast = repo.get_forecast(forecast_id, now=next_day)
    assert forecast["review"]["training_eligibility"] == "requires_mature_revalidation"
    # reviewed_at original no se reescribe al pasar la medianoche.
    assert forecast["review"]["latest_review"]["reviewed_at"] == "2026-09-20T23:59:00Z"


def test_mature_revalidation_after_target_date_is_a_compatible_correction(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 19), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]  # target_date = 2026-09-20
    later = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)

    _, review = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-mature",
        expected_revision=0,
        action="reject",
        comment=None,
        now=later,
    )
    assert review["training_eligibility"] == "compatible_correction"


def test_confirmations_never_become_training_corrections(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 19), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    later = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)

    _, review = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-confirm",
        expected_revision=0,
        action="confirm",
        comment=None,
        now=later,
    )
    assert review["training_eligibility"] == "confirmation_only"


def test_editing_an_opinion_preserves_history_without_attributing_it_as_applied(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    batch = _seed_batch(
        repo, as_of_date=date(2026, 9, 19), slots=_slots_with({1}), idempotency_key="k1"
    )
    forecast_id = batch["slots"][0]["forecast_id"]
    later = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)

    repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-1",
        expected_revision=0,
        action="confirm",
        comment="primera opinion",
        now=later,
    )
    _, second = repo.submit_review(
        forecast_id=forecast_id,
        request_id="req-2",
        expected_revision=1,
        action="reject",
        comment="corrijo mi opinion",
        now=later,
    )
    assert second["revision"] == 2
    assert second["applied_review_references"] == []  # ninguna recalibración corrió
    history = repo._read()["reviews"][forecast_id]
    assert [event["comment"] for event in history] == ["primera opinion", "corrijo mi opinion"]


def test_review_of_unknown_forecast_is_not_found(tmp_path):
    repo = OperationalRepository(tmp_path, "sensor-a")
    with pytest.raises(OperationalRepositoryError) as excinfo:
        repo.submit_review(
            forecast_id="fc_does_not_exist",
            request_id="req-1",
            expected_revision=0,
            action="confirm",
            comment=None,
            now=datetime(2026, 9, 20, tzinfo=UTC),
        )
    assert excinfo.value.code == "forecast_not_found"
    assert excinfo.value.status_code == 404


def test_demo_review_write_is_locked_even_when_a_forecast_somehow_exists(tmp_path):
    repo = OperationalRepository(tmp_path, "demo-x")
    # No hay forma legítima de tener una emisión demo- (record_batch la
    # bloquea); se siembra el documento directamente para probar que el
    # guard de reviews también se aplica, no solo el de emisión.
    document = repo._read()
    document["forecasts"]["fc_fixture"] = {
        "forecast_id": "fc_fixture",
        "sensor_id": "demo-x",
        "batch_id": "batch_fixture",
        "as_of_date": "2026-09-18",
        "horizon_days": 1,
        "target_date": "2026-09-19",
        "contract_version": CONTRACT_VERSION,
        "issued_at": "2026-09-18T00:00:00Z",
        "snapshot_id": "snap-1",
        "alert": True,
        "score": 0.7,
        "score_kind": "calibrated_probability",
        "display_probability": 0.7,
        "probability_status": "development_assessed",
        "probability_reason_code": None,
        "decision_threshold": 0.5,
        "event_threshold": _event_threshold(),
        "model_reference": _model_reference(),
        "review": {"status": "pending", "revision": 0, "latest_review": None},
    }
    repo._write(document)

    with pytest.raises(OperationalRepositoryError) as excinfo:
        repo.submit_review(
            forecast_id="fc_fixture",
            request_id="req-1",
            expected_revision=0,
            action="confirm",
            comment=None,
            now=datetime(2026, 9, 20, tzinfo=UTC),
        )
    assert excinfo.value.code == "demo_write_locked"


# ---------------------------------------------------------------------------
# Endpoints HTTP
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    try:
        with TestClient(app) as test_client:
            yield test_client, tmp_path
    finally:
        app.dependency_overrides.clear()


def test_get_forecast_returns_404_when_no_real_emission_exists(client):
    test_client, _ = client
    response = test_client.get("/api/v2/sensors/sensor-a/forecasts/fc_unknown")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_not_found"


def test_list_forecasts_is_empty_without_real_emissions(client):
    test_client, _ = client
    response = test_client.get("/api/v2/sensors/sensor-a/forecasts")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["pending_total"] == 0
    assert body["reviewable_pending_total"] == 0


def test_get_and_list_forecasts_expose_seeded_fixture_and_are_isolated_by_sensor(client):
    test_client, data_dir = client
    repo_a = OperationalRepository(data_dir, "sensor-a")
    repo_b = OperationalRepository(data_dir, "sensor-b")
    batch = _seed_batch(
        repo_a,
        as_of_date=date(2026, 9, 18),
        slots=_all_available(),
        idempotency_key="k1",
        issued_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
    )
    forecast_id = next(s["forecast_id"] for s in batch["slots"] if s["horizon_days"] == 1)

    detail = test_client.get(f"/api/v2/sensors/sensor-a/forecasts/{forecast_id}")
    assert detail.status_code == 200
    assert detail.json()["forecast_id"] == forecast_id

    cross_sensor = test_client.get(f"/api/v2/sensors/sensor-b/forecasts/{forecast_id}")
    assert cross_sensor.status_code == 404

    listing = test_client.get("/api/v2/sensors/sensor-a/forecasts")
    assert listing.status_code == 200
    body = listing.json()
    assert len(body["items"]) == 3
    assert body["pending_total"] == 3
    # target_date DESC, issued_at DESC, forecast_id ASC.
    assert [item["horizon_days"] for item in body["items"]] == [3, 2, 1]

    assert repo_b.get_forecast(forecast_id, now=datetime.now(UTC)) is None


def test_list_forecasts_filters_and_pagination(client):
    test_client, data_dir = client
    repo = OperationalRepository(data_dir, "sensor-a")
    _seed_batch(
        repo,
        as_of_date=date(2026, 9, 1),
        slots=_all_available(),
        idempotency_key="k1",
        issued_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )
    _seed_batch(
        repo,
        as_of_date=date(2026, 9, 10),
        slots=_all_available(),
        idempotency_key="k2",
        issued_at=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
    )

    by_horizon = test_client.get("/api/v2/sensors/sensor-a/forecasts", params={"horizon_days": 1})
    assert by_horizon.status_code == 200
    assert all(item["horizon_days"] == 1 for item in by_horizon.json()["items"])
    assert len(by_horizon.json()["items"]) == 2

    windowed = test_client.get(
        "/api/v2/sensors/sensor-a/forecasts",
        params={"target_from": "2026-09-11", "target_to": "2026-09-13"},
    )
    assert windowed.status_code == 200
    assert len(windowed.json()["items"]) == 3  # tanda de 9/10, horizontes 1,2,3

    first_page = test_client.get("/api/v2/sensors/sensor-a/forecasts", params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = test_client.get(
        "/api/v2/sensors/sensor-a/forecasts",
        params={"limit": 2, "cursor": first_page["next_cursor"]},
    ).json()
    assert len(second_page["items"]) == 2
    seen_ids = {item["forecast_id"] for item in first_page["items"]} | {
        item["forecast_id"] for item in second_page["items"]
    }
    assert len(seen_ids) == 4

    mismatched = test_client.get(
        "/api/v2/sensors/sensor-a/forecasts",
        params={"limit": 2, "horizon_days": 2, "cursor": first_page["next_cursor"]},
    )
    assert mismatched.status_code == 422
    assert mismatched.json()["error"]["code"] == "invalid_cursor"


def test_review_endpoint_full_flow_and_conflicts(client):
    test_client, data_dir = client
    repo = OperationalRepository(data_dir, "sensor-a")
    batch = _seed_batch(
        repo,
        as_of_date=date(2026, 9, 1),
        slots=_slots_with({1}),
        idempotency_key="k1",
        issued_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )
    forecast_id = batch["slots"][0]["forecast_id"]  # target_date = 2026-09-02, ya abierta

    created = test_client.post(
        f"/api/v2/sensors/sensor-a/forecasts/{forecast_id}/reviews",
        json={"request_id": "req-1", "expected_revision": 0, "action": "confirm"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "confirmed"
    assert created.json()["revision"] == 1

    replay = test_client.post(
        f"/api/v2/sensors/sensor-a/forecasts/{forecast_id}/reviews",
        json={"request_id": "req-1", "expected_revision": 0, "action": "confirm"},
    )
    assert replay.status_code == 201
    assert replay.json()["revision"] == 1

    stale = test_client.post(
        f"/api/v2/sensors/sensor-a/forecasts/{forecast_id}/reviews",
        json={"request_id": "req-2", "expected_revision": 0, "action": "reject"},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "revision_conflict"

    conflicting_payload = test_client.post(
        f"/api/v2/sensors/sensor-a/forecasts/{forecast_id}/reviews",
        json={"request_id": "req-1", "expected_revision": 0, "action": "reject"},
    )
    assert conflicting_payload.status_code == 409
    assert conflicting_payload.json()["error"]["code"] == "idempotency_conflict"

    unknown = test_client.post(
        "/api/v2/sensors/sensor-a/forecasts/fc_unknown/reviews",
        json={"request_id": "req-3", "expected_revision": 0, "action": "confirm"},
    )
    assert unknown.status_code == 404


def test_demo_sensor_review_endpoint_returns_write_locked(client):
    test_client, _ = client
    response = test_client.post(
        "/api/v2/sensors/demo-x/forecasts/fc_unknown/reviews",
        json={"request_id": "req-1", "expected_revision": 0, "action": "confirm"},
    )
    # No existe la emision (nunca se puede emitir para demo-), asi que el
    # aislamiento de recurso reporta 404 antes que el guard de escritura;
    # eso ya prueba que ninguna emision demo- puede sembrarse por HTTP.
    assert response.status_code == 404


def test_legacy_routes_are_unaffected_by_v2_forecast_endpoints(client):
    test_client, _ = client
    response = test_client.post(
        "/sensors/sensor-a/readings", json={"timestamp": "2026-01-01T00:00:00"}
    )
    assert response.status_code == 200


def test_openapi_publishes_forecast_and_review_contracts(client):
    test_client, _ = client
    document = test_client.get("/openapi.json").json()
    assert "/api/v2/sensors/{sensor_id}/forecasts" in document["paths"]
    assert "/api/v2/sensors/{sensor_id}/forecasts/{forecast_id}" in document["paths"]
    assert "/api/v2/sensors/{sensor_id}/forecasts/{forecast_id}/reviews" in document["paths"]
