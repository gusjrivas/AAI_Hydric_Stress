from datetime import datetime, timezone

import pytest

from human_feedback.operational_repository import OperationalRepository, SlotSeed


def _event_threshold():
    return {"variable": "soil_moisture", "value": 0.3, "unit": "m3/m3", "comparison": "lt"}


def _model_reference(**overrides):
    ref = {
        "model_version": "x",
        "horizon_days": 1,
        "contract_version": "producer_daily_h123_v1",
        "trained_through": None,
        "calibration_version": None,
        "assessment_reference": None,
    }
    ref.update(overrides)
    return ref


def _ensemble_detail(**overrides):
    detail = {
        "policy_version": "ensemble_agreement_v1",
        "ensemble_identity_sha256": "a" * 64,
        "components": [{"family": "logistic_regression", "score": 0.51}],
        "combined_probability": 0.343333,
        "combined_alert": False,
        "positive_votes": 2,
        "agreement_category": "posible_alerta_acuerdo_parcial",
        "calibrated_through": "2026-01-20",
    }
    detail.update(overrides)
    return detail


def _base_kwargs(**overrides):
    kwargs = dict(
        horizon_days=1,
        status="available",
        alert=False,
        score=0.343333,
        score_kind="ensemble_mean_of_calibrated_components",
        decision_threshold=0.5,
        event_threshold=_event_threshold(),
        model_reference=_model_reference(),
    )
    kwargs.update(overrides)
    return kwargs


def test_slot_seed_allows_ensemble_none():
    SlotSeed(**_base_kwargs())  # no error


def test_slot_seed_requires_alert_to_match_combined_alert():
    with pytest.raises(ValueError, match="combined_alert"):
        SlotSeed(**_base_kwargs(alert=True, ensemble=_ensemble_detail(combined_alert=False)))


def test_slot_seed_requires_score_to_match_combined_probability():
    with pytest.raises(ValueError, match="combined_probability"):
        SlotSeed(
            **_base_kwargs(score=0.9, ensemble=_ensemble_detail(combined_probability=0.343333))
        )


def test_slot_seed_accepts_coherent_ensemble_detail():
    SlotSeed(**_base_kwargs(alert=False, score=0.343333, ensemble=_ensemble_detail()))


def test_ensemble_field_persists_through_record_batch_and_render(tmp_path):
    repo = OperationalRepository(tmp_path, "s1")
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    ensemble_seed = SlotSeed(**_base_kwargs(ensemble=_ensemble_detail()))
    other_seeds = [
        SlotSeed(horizon_days=2, status="unavailable", reason_code="no_readings"),
        SlotSeed(horizon_days=3, status="unavailable", reason_code="no_readings"),
    ]
    body = repo.record_batch(
        as_of_date=now.date(),
        issued_at=now,
        snapshot_id="snap1",
        data_age_days=0,
        provenance="synthetic",
        slots=[ensemble_seed, *other_seeds],
        idempotency_key="key1",
        now=now,
    )
    slot = next(s for s in body["slots"] if s["horizon_days"] == 1)
    assert slot["ensemble"]["policy_version"] == "ensemble_agreement_v1"
    assert slot["ensemble"]["agreement_category"] == "posible_alerta_acuerdo_parcial"

    forecast = repo.get_forecast(slot["forecast_id"], now=now)
    assert forecast["ensemble"]["ensemble_identity_sha256"] == "a" * 64


def test_render_forecast_handles_old_records_without_ensemble_key(tmp_path):
    repo = OperationalRepository(tmp_path, "s1")
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    seed = SlotSeed(**_base_kwargs(score_kind="calibrated_probability"))
    other_seeds = [
        SlotSeed(horizon_days=2, status="unavailable", reason_code="no_readings"),
        SlotSeed(horizon_days=3, status="unavailable", reason_code="no_readings"),
    ]
    body = repo.record_batch(
        as_of_date=now.date(),
        issued_at=now,
        snapshot_id="snap1",
        data_age_days=0,
        provenance="synthetic",
        slots=[seed, *other_seeds],
        idempotency_key="key1",
        now=now,
    )
    forecast_id = next(s for s in body["slots"] if s["horizon_days"] == 1)["forecast_id"]

    # Simulate a pre-change persisted record: strip the "ensemble" key
    # entirely (old records never had it), then read back.
    document = repo._read()
    del document["forecasts"][forecast_id]["ensemble"]
    repo._write(document)

    rendered = repo.get_forecast(forecast_id, now=now)
    assert rendered["ensemble"] is None


def test_idempotency_hash_for_a_single_model_slot_is_unaffected_by_the_ensemble_field(tmp_path):
    """A slot with ensemble=None must hash identically to how it would have
    hashed before this field existed -- the ensemble field is omitted
    entirely from the hashed payload, never added as null, so a legacy
    idempotency key retried after this change is not spuriously rejected as
    idempotency_conflict against a hash computed under the old code."""
    from human_feedback.operational_repository import _request_hash

    repo = OperationalRepository(tmp_path, "s1")
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    seed = SlotSeed(**_base_kwargs(score_kind="calibrated_probability"))
    other_seeds = [
        SlotSeed(horizon_days=2, status="unavailable", reason_code="no_readings"),
        SlotSeed(horizon_days=3, status="unavailable", reason_code="no_readings"),
    ]
    repo.record_batch(
        as_of_date=now.date(),
        issued_at=now,
        snapshot_id="snap1",
        data_age_days=0,
        provenance="synthetic",
        slots=[seed, *other_seeds],
        idempotency_key="key1",
        now=now,
    )
    document = repo._read()
    stored_hash = document["idempotency"]["emission"]["key1"]["request_hash"]

    # Reconstruct the pre-this-change payload shape by hand (no "ensemble"
    # key anywhere) and confirm it hashes to the exact same value.
    def _legacy_slot_payload(s: SlotSeed) -> dict:
        return {
            "horizon_days": s.horizon_days,
            "status": s.status,
            "reason_code": s.reason_code,
            "alert": s.alert,
            "score": s.score,
            "score_kind": s.score_kind,
            "display_probability": s.display_probability,
            "probability_status": s.probability_status,
            "probability_reason_code": s.probability_reason_code,
            "decision_threshold": s.decision_threshold,
            "event_threshold": s.event_threshold,
            "model_reference": s.model_reference,
        }

    legacy_payload = {
        "as_of_date": now.date().isoformat(),
        "snapshot_id": "snap1",
        "data_age_days": 0,
        "provenance": "synthetic",
        "slots": [
            _legacy_slot_payload(s)
            for s in sorted([seed, *other_seeds], key=lambda s: s.horizon_days)
        ],
        "contract_version": "producer_daily_h123_v1",
    }
    assert _request_hash(legacy_payload) == stored_hash
