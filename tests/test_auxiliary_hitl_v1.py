"""Pruebas del complemento auxiliar H (`auxiliary_hitl_v1`).

Cubren las tres clases de evidencia que el runner distingue —intervención
humana controlada, simulación y fixture— y, sobre todo, que **falle de forma
cerrada** ante cada entrada inválida prevista por el contrato predeclarado
`openspec/changes/sc-08-aux-hitl/contract-H-frozen.json`.

Todo lo que se construye aquí es `feedback_origin == "fixture"` salvo cuando
la prueba verifica justamente que un fixture no puede pasar por evidencia
científica. Ninguna de estas pruebas es evidencia científica: verifican el
software, no la validez de ningún resultado.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.config import PRIMARY_DEPTH_COLUMN
from experiment_runner.controlled_daily_v4.features import FEATURE_COLUMNS
from experiment_runner.scientific_auxiliary import auxiliary_hitl_v1 as h
from tests.controlled_daily_v4_fixtures import make_synthetic_daily_frame

# 2015-01-01 .. 2022-12-31 inclusive: la ventana completa del complemento H.
N_DAYS_2015_2022 = (pd.Timestamp("2022-12-31") - pd.Timestamp("2015-01-01")).days + 1
FIXTURE_SEED = 0
EXECUTION_INSTANT = datetime(2023, 1, 15, tzinfo=timezone.utc)
VALIDATED_AT = datetime(2022, 1, 5, tzinfo=timezone.utc)
FIXTURE_DATASET_SHA256 = "a" * 64


_DAILY_SERIES_HOLDER: dict[str, pd.DataFrame] = {}


@pytest.fixture(scope="module")
def daily_series() -> pd.DataFrame:
    """Serie diaria sintética 2015-2022. Ejemplo de integración de software,
    nunca evidencia de desempeño científico."""
    if "value" not in _DAILY_SERIES_HOLDER:
        _DAILY_SERIES_HOLDER["value"] = make_synthetic_daily_frame(
            n_days=N_DAYS_2015_2022, seed=23, supported=True
        )
    return _DAILY_SERIES_HOLDER["value"]


@pytest.fixture(scope="module")
def frames(daily_series: pd.DataFrame) -> h.HitlFrames:
    return h.build_hitl_frames(daily_series, PRIMARY_DEPTH_COLUMN)


@pytest.fixture(scope="module")
def prepared(frames: h.HitlFrames) -> dict:
    """Modelo congelado, etiquetas registradas y los 20 eventos del presupuesto."""
    model = h.fit_hitl_model(
        frames.train_initial, frames.train_initial["stress_label"], FIXTURE_SEED
    )
    _, alerts = h._predict(model, frames.feedback)
    recorded, positions = h.corrupt_training_labels(frames.feedback, FIXTURE_SEED)
    events_frame = h.select_review_events(frames.feedback, alerts)
    train_fingerprint = h.content_sha256(
        [pd.Timestamp(d).isoformat() for d in frames.train_initial["feature_timestamp"]]
    )
    model_id = h.deterministic_model_id(
        arm=h.ARM_FROZEN,
        seed=FIXTURE_SEED,
        track="shared",
        training_fingerprint=train_fingerprint,
        label_fingerprint=h._label_fingerprint(
            frames.train_initial["feature_timestamp"], frames.train_initial["stress_label"]
        ),
    )
    return {
        "model_id": model_id,
        "alerts": alerts,
        "recorded": recorded,
        "corrupted_positions": positions,
        "clean": frames.feedback["stress_label"].astype(int),
        "events_frame": events_frame,
    }


def _role_for(origin: str) -> str:
    """El rol admisible depende del origen: el oráculo simulado nunca lleva el
    rol reservado al operador humano autorizado."""
    return (
        h.SIMULATED_REVIEWER_ROLE
        if origin == h.ORIGIN_SIMULATED
        else (h.AUTHORIZED_OPERATOR_ROLES[0])
    )


def _decisions(prepared: dict, frames: h.HitlFrames) -> list[dict]:
    return h.simulated_reviewer_decisions(
        prepared["events_frame"], prepared["recorded"], prepared["clean"]
    )


def _events(
    prepared: dict,
    frames: h.HitlFrames,
    *,
    decisions: list[dict] | None = None,
    origin: str = h.ORIGIN_FIXTURE,
    operator_id: str = "fixture_operator",
    operator_role: str | None = None,
    package_sha256: str = "b" * 64,
    model_version: str | None = None,
) -> list[dict]:
    return h.build_feedback_events(
        events=prepared["events_frame"],
        recorded_labels=prepared["recorded"],
        clean_labels=prepared["clean"],
        decisions=decisions if decisions is not None else _decisions(prepared, frames),
        origin=origin,
        operator_id=operator_id,
        operator_role=operator_role or _role_for(origin),
        model_version=model_version or prepared["model_id"],
        package_id="fixture-package",
        package_sha256=package_sha256,
        validated_at=VALIDATED_AT,
    )


def _validate(events: list[dict], frames: h.HitlFrames, prepared: dict, **overrides):
    kwargs = {
        "admissible_emissions": {pd.Timestamp(d) for d in frames.feedback["feature_timestamp"]},
        "expected_package_sha256": "b" * 64,
        "expected_model_version": prepared["model_id"],
        "successor_model_id": "successor-" + "0" * 20,
        "expected_feature_contract": {
            "version": "pergamino_features.v1",
            "model_features": list(FEATURE_COLUMNS),
        },
        "execution_instant": EXECUTION_INSTANT,
        "allow_fixture": True,
    }
    kwargs.update(overrides)
    return h.validate_feedback_events(events, **kwargs)


def _rules(error: h.HitlValidationError) -> set[str]:
    return {v.split("]")[0].lstrip("[") for v in error.violations}


# --------------------------------------------------------------------------
# Fronteras temporales y estructura del diseño congelado
# --------------------------------------------------------------------------


def test_frozen_design_windows_are_disjoint_and_end_in_2022(frames: h.HitlFrames) -> None:
    """Train <= 2020, feedback en 2021, evaluación en 2022, sin solapamiento."""
    train_max = pd.to_datetime(frames.train_initial["target_timestamp"]).max()
    feedback_min = pd.to_datetime(frames.feedback["target_timestamp"]).min()
    feedback_max = pd.to_datetime(frames.feedback["target_timestamp"]).max()
    eval_min = pd.to_datetime(frames.evaluation["target_timestamp"]).min()
    eval_max = pd.to_datetime(frames.evaluation["target_timestamp"]).max()

    assert train_max <= pd.Timestamp("2020-12-31")
    assert feedback_min > train_max
    assert feedback_max <= pd.Timestamp("2021-12-31")
    assert eval_min > feedback_max
    assert eval_max <= pd.Timestamp(h.HITL_MAX_TARGET_DATE)


def test_no_row_after_the_hard_boundary_reaches_the_runner(frames: h.HitlFrames) -> None:
    """INV-01: 2023 (Etapa B) y 2024-2025 (holdout) quedan fuera por construcción."""
    assert pd.to_datetime(frames.eligible["target_timestamp"]).max() <= pd.Timestamp(
        h.HITL_MAX_TARGET_DATE
    )


def test_future_rows_abort_instead_of_being_silently_trimmed() -> None:
    """Una fila posterior a 2022-12-31 aborta: nunca se recorta en silencio."""
    frame = pd.DataFrame(
        {"target_timestamp": [pd.Timestamp("2024-06-01")], "feature_timestamp": [pd.NaT]}
    )
    with pytest.raises(h.HitlValidationError):
        h._assert_no_future_data(frame, "prueba")


def test_p20_is_computed_once_from_the_initial_train(frames: h.HitlFrames) -> None:
    """INV-04: el P20 sale del train inicial y no se recalcula por ventana."""
    from experiment_runner.controlled_daily_v4.features import compute_p20_threshold

    assert frames.p20_frozen == pytest.approx(
        compute_p20_threshold(frames.train_initial["future_soil_moisture"])
    )
    # El P20 de la ventana de feedback sería otro número; el diseño exige usar
    # el congelado, no este. Se calcula solo para dejar constancia de que son
    # distintos y de que el runner no usa el de la ventana.
    recomputed_on_feedback = compute_p20_threshold(frames.feedback["future_soil_moisture"])
    labels_with_frozen = (frames.feedback["future_soil_moisture"] < frames.p20_frozen).astype(int)
    assert labels_with_frozen.equals(frames.feedback["stress_label"].astype(int))
    assert isinstance(recomputed_on_feedback, float)


def test_event_budget_is_twenty_with_ten_alerts_and_ten_non_alerts(prepared: dict) -> None:
    events = prepared["events_frame"]
    assert len(events) == h.EVENT_BUDGET_PER_SEED
    assert int((events["model_alert"] == 1).sum()) == h.EVENTS_PER_STRATUM
    assert int((events["model_alert"] == 0).sum()) == h.EVENTS_PER_STRATUM


def test_event_selection_is_deterministic(frames: h.HitlFrames, prepared: dict) -> None:
    again = h.select_review_events(frames.feedback, prepared["alerts"])
    assert list(again["feature_timestamp"]) == list(prepared["events_frame"]["feature_timestamp"])


def test_insufficient_stratum_reports_not_evaluable(frames: h.HitlFrames) -> None:
    """El diseño prohíbe completar el presupuesto mirando 2022."""
    all_zero = np.zeros(len(frames.feedback), dtype=int)
    with pytest.raises(h.HitlNotEvaluableError):
        h.select_review_events(frames.feedback, all_zero)


def test_corruption_flips_ten_percent_with_an_independent_stream(frames: h.HitlFrames) -> None:
    recorded, positions = h.corrupt_training_labels(frames.feedback, FIXTURE_SEED)
    clean = frames.feedback["stress_label"].astype(int)
    assert len(positions) == int(np.floor(h.CORRUPTION_FRACTION * len(clean)))
    assert int((recorded.to_numpy() != clean.to_numpy()).sum()) == len(positions)
    other, other_positions = h.corrupt_training_labels(frames.feedback, FIXTURE_SEED + 1)
    assert not np.array_equal(positions, other_positions)


def test_seeds_match_the_frozen_design() -> None:
    """El bloque padre del diseño congelado fija Seeds [0,1,2,3,4]."""
    assert h.DEFAULT_SEEDS == (0, 1, 2, 3, 4)
    assert h.PRIMARY_SEED_FOR_HUMAN_PACKAGE in h.DEFAULT_SEEDS


# --------------------------------------------------------------------------
# Evento válido y validaciones cerradas
# --------------------------------------------------------------------------


def test_valid_human_event_package_is_accepted(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(
        prepared,
        frames,
        origin=h.ORIGIN_HUMAN,
        operator_id=h.EXPECTED_OPERATOR_ID,
    )
    assert _validate(events, frames, prepared, allow_fixture=False) == {}


def test_missing_identity_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    events[3]["operator_id"] = "   "
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R01-identity" in _rules(error.value)


def test_unauthorized_role_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    events[0]["operator_role"] = "agronomist"
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R02-role" in _rules(error.value)


def test_simulated_reviewer_cannot_wear_the_human_operator_role(
    frames: h.HitlFrames, prepared: dict
) -> None:
    """Hallazgo C-08: el oráculo no puede llevar el rol reservado a la persona."""
    events = _events(
        prepared,
        frames,
        origin=h.ORIGIN_SIMULATED,
        operator_role=h.AUTHORIZED_OPERATOR_ROLES[0],
    )
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared, allow_fixture=False)
    assert "R02-role" in _rules(error.value)


def test_human_event_cannot_wear_the_simulated_reviewer_role(
    frames: h.HitlFrames, prepared: dict
) -> None:
    events = _events(
        prepared,
        frames,
        origin=h.ORIGIN_HUMAN,
        operator_id=h.EXPECTED_OPERATOR_ID,
        operator_role=h.SIMULATED_REVIEWER_ROLE,
    )
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared, allow_fixture=False)
    assert "R02-role" in _rules(error.value)


def test_duplicate_feedback_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    events.append(copy.deepcopy(events[0]))
    events[-1]["scenario_id"] = "H-SC-021"
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R16-duplicate" in _rules(error.value)


def test_contradictory_feedback_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    clone = copy.deepcopy(events[0])
    clone["scenario_id"] = "H-SC-021"
    clone["decision"] = h.DECISION_CORRECT
    clone["corrected_label"] = 1 - int(clone["recorded_label"])
    events.append(clone)
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R17-contradictory" in _rules(error.value)


def test_nonexistent_reference_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    events[2]["fecha"] = pd.Timestamp("2021-06-15").isoformat()
    events[2]["target_timestamp"] = pd.Timestamp("2021-06-18").isoformat()
    with pytest.raises(h.HitlValidationError) as error:
        _validate(
            events,
            frames,
            prepared,
            admissible_emissions={pd.Timestamp("2021-01-04")},
        )
    assert "R09-reference" in _rules(error.value)


def test_wrong_package_hash_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames, package_sha256="c" * 64)
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R10-package-hash" in _rules(error.value)


def test_invalid_timestamp_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    events[1]["validated_at"] = "no-es-una-fecha"
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R11-timestamp" in _rules(error.value)


def test_temporal_leak_before_maturation_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    """Validar antes de que cierre el día objetivo es fuga temporal."""
    events = _events(prepared, frames)
    target = pd.Timestamp(events[0]["target_timestamp"])
    events[0]["validated_at"] = (target - pd.Timedelta(days=1)).isoformat()
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R13-maturation" in _rules(error.value)


def test_event_outside_the_acquisition_window_is_rejected(
    frames: h.HitlFrames, prepared: dict
) -> None:
    events = _events(prepared, frames)
    events[0]["fecha"] = pd.Timestamp("2022-06-01").isoformat()
    events[0]["target_timestamp"] = pd.Timestamp("2022-06-04").isoformat()
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R15-temporal-leak" in _rules(error.value)


def test_incompatible_feature_contract_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    with pytest.raises(h.HitlValidationError) as error:
        _validate(
            events,
            frames,
            prepared,
            expected_feature_contract={
                "version": "pergamino_features.v1",
                "model_features": list(FEATURE_COLUMNS)[:-1],
            },
        )
    assert "R18-feature-contract" in _rules(error.value)


def test_wrong_model_reference_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames, model_version="otro-predictor")
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R19-model-reference" in _rules(error.value)


def test_self_reference_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared, successor_model_id=prepared["model_id"])
    assert "R20-self-reference" in _rules(error.value)


def test_missing_reason_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    events[4]["reason"] = ""
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R08-reason" in _rules(error.value)


def test_missing_schema_field_is_rejected(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames)
    del events[0]["target_timestamp"]
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R05-schema" in _rules(error.value)


def test_correction_without_a_different_label_is_rejected(
    frames: h.HitlFrames, prepared: dict
) -> None:
    events = _events(prepared, frames)
    events[0]["decision"] = h.DECISION_CORRECT
    events[0]["corrected_label"] = int(events[0]["recorded_label"])
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R07-decision-payload" in _rules(error.value)


def test_accept_carrying_a_corrected_label_is_rejected(
    frames: h.HitlFrames, prepared: dict
) -> None:
    events = _events(prepared, frames)
    events[0]["decision"] = h.DECISION_ACCEPT
    events[0]["corrected_label"] = 1
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert "R07-decision-payload" in _rules(error.value)


def test_all_violations_are_reported_together(frames: h.HitlFrames, prepared: dict) -> None:
    """Falla cerrada con diagnóstico completo, no al primer error."""
    events = _events(prepared, frames)
    events[0]["operator_id"] = ""
    events[1]["operator_role"] = "agronomist"
    events[2]["reason"] = ""
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared)
    assert {"R01-identity", "R02-role", "R08-reason"} <= _rules(error.value)


# --------------------------------------------------------------------------
# Separación entre intervención humana, simulación y fixture
# --------------------------------------------------------------------------


def test_fixture_cannot_be_presented_as_scientific_evidence(
    frames: h.HitlFrames, prepared: dict
) -> None:
    events = _events(prepared, frames, origin=h.ORIGIN_FIXTURE)
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared, allow_fixture=False)
    assert "R04-fixture-as-evidence" in _rules(error.value)


def test_simulated_feedback_cannot_be_mixed_with_human_feedback(
    frames: h.HitlFrames, prepared: dict
) -> None:
    """Un evento simulado infiltrado en un paquete humano se rechaza."""
    events = _events(prepared, frames, origin=h.ORIGIN_HUMAN)
    events[5]["feedback_origin"] = h.ORIGIN_SIMULATED
    with pytest.raises(h.HitlValidationError) as error:
        _validate(events, frames, prepared, allow_fixture=False)
    assert "R04-mixed-origins" in _rules(error.value)


def test_every_event_declares_its_origin_and_track(frames: h.HitlFrames, prepared: dict) -> None:
    for origin, track in h.TRACK_BY_ORIGIN.items():
        events = _events(prepared, frames, origin=origin, operator_role=_role_for(origin))
        assert all(e["feedback_origin"] == origin for e in events)
        assert all(e["track"] == track for e in events)


def test_the_forbidden_agronomic_label_is_never_a_track() -> None:
    assert h.FORBIDDEN_EVIDENCE_CLASS not in h.TRACK_BY_ORIGIN.values()
    assert h.TRACK_HUMAN != h.FORBIDDEN_EVIDENCE_CLASS
    assert "agronomist" in h.OPERATOR_ROLE_IS_NOT
    assert "agronomist" not in h.AUTHORIZED_OPERATOR_ROLES


# --------------------------------------------------------------------------
# Aplicación de decisiones
# --------------------------------------------------------------------------


def _uniform_decisions(prepared: dict, decision: str, corrected=None) -> list[dict]:
    out = []
    for position, (_, row) in enumerate(prepared["events_frame"].iterrows(), start=1):
        recorded = int(prepared["recorded"].loc[row.name])
        out.append(
            {
                "scenario_id": h.scenario_identifier(position),
                "decision": decision,
                "corrected_label": (1 - recorded) if decision == h.DECISION_CORRECT else None,
                "reason": "fixture",
            }
        )
    return out


def test_accept_changes_nothing(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames, decisions=_uniform_decisions(prepared, h.DECISION_ACCEPT))
    applied = h.apply_feedback(
        feedback=frames.feedback, recorded_labels=prepared["recorded"], events=events
    )
    assert applied.n_accept == h.EVENT_BUDGET_PER_SEED
    assert applied.n_effective_changes == 0
    assert applied.labels.equals(prepared["recorded"].astype(int))


def test_reject_excludes_the_row_without_inventing_a_label(
    frames: h.HitlFrames, prepared: dict
) -> None:
    events = _events(prepared, frames, decisions=_uniform_decisions(prepared, h.DECISION_REJECT))
    applied = h.apply_feedback(
        feedback=frames.feedback, recorded_labels=prepared["recorded"], events=events
    )
    assert applied.n_reject == h.EVENT_BUDGET_PER_SEED
    assert len(applied.excluded_positions) == h.EVENT_BUDGET_PER_SEED
    assert applied.labels.equals(prepared["recorded"].astype(int))


def test_correct_replaces_the_label(frames: h.HitlFrames, prepared: dict) -> None:
    events = _events(prepared, frames, decisions=_uniform_decisions(prepared, h.DECISION_CORRECT))
    applied = h.apply_feedback(
        feedback=frames.feedback, recorded_labels=prepared["recorded"], events=events
    )
    assert applied.n_correct == h.EVENT_BUDGET_PER_SEED
    assert applied.n_effective_changes == h.EVENT_BUDGET_PER_SEED
    for date in applied.corrected_dates:
        position = frames.feedback.index[
            frames.feedback["feature_timestamp"] == pd.Timestamp(date)
        ][0]
        assert int(applied.labels.loc[position]) != int(prepared["recorded"].loc[position])


# --------------------------------------------------------------------------
# Recalibración, linaje y preservación del predecesor
# --------------------------------------------------------------------------


def _run(frames: h.HitlFrames, prepared: dict, decisions=None, origin=h.ORIGIN_FIXTURE):
    return h.run_track_for_seed(
        frames=frames,
        seed=FIXTURE_SEED,
        origin=origin,
        operator_id="fixture_operator",
        operator_role=_role_for(origin),
        package_id="fixture-package",
        package_sha256="b" * 64,
        decisions=decisions,
        validated_at=VALIDATED_AT,
        execution_instant=EXECUTION_INSTANT,
        dataset_sha256=FIXTURE_DATASET_SHA256,
        allow_fixture=True,
    )


def test_three_arms_are_evaluated_on_the_same_rows(frames: h.HitlFrames, prepared: dict) -> None:
    result = _run(frames, prepared)
    assert set(result.arms) == set(h.ARMS)
    counts = {name: arm.metrics["n_observations"] for name, arm in result.arms.items()}
    assert len(set(counts.values())) == 1, counts


def test_valid_recalibration_produces_a_complete_lineage(
    frames: h.HitlFrames, prepared: dict
) -> None:
    result = _run(frames, prepared)
    assert result.recalibration_status == h.RECALIBRATION_APPLIED
    assert result.lineage is not None
    assert result.lineage["lineage_version"] == h.CURRENT_LINEAGE_VERSION
    assert result.lineage["dataset_sha256"] == FIXTURE_DATASET_SHA256
    assert len(result.lineage["feedback_references"]) == result.applied["n_effective_changes"]


def test_no_change_is_recorded_not_hidden(frames: h.HitlFrames, prepared: dict) -> None:
    """Ausencia de recalibración es un resultado válido y explícito."""
    result = _run(frames, prepared, decisions=_uniform_decisions(prepared, h.DECISION_ACCEPT))
    assert result.recalibration_status == h.NO_RECALIBRATION
    assert result.recalibration_reason
    assert result.lineage is None
    assert result.applied["n_effective_changes"] == 0


def test_predecessor_is_preserved(frames: h.HitlFrames, prepared: dict) -> None:
    result = _run(frames, prepared)
    assert result.predecessor_preserved
    ids = {arm.model_id for arm in result.arms.values()}
    assert len(ids) == len(h.ARMS)
    assert result.lineage["source_model_id"] != result.lineage["successor_model_id"]


def test_successive_recalibration_chains_without_losing_the_predecessor(
    frames: h.HitlFrames, prepared: dict
) -> None:
    first = _run(frames, prepared)
    successor_of_cycle_1 = first.arms[h.ARM_REFIT_WITH_CORRECTIONS].model_id
    # Un segundo ciclo HITL revisa predicciones del SUCESOR, no del modelo
    # congelado: por eso sus eventos declaran ese `model_version`. Reusar los
    # eventos del primer ciclo produciría un linaje inválido, y el propio
    # `RecalibrationLineage` lo rechaza.
    events = [dict(e, model_version=successor_of_cycle_1) for e in first.events]
    applied = h.apply_feedback(
        feedback=frames.feedback,
        recorded_labels=prepared["recorded"],
        events=events,
    )
    training = pd.concat([frames.train_initial, frames.feedback])
    labels = pd.concat([frames.train_initial["stress_label"].astype(int), applied.labels])
    _, successor_id, lineage = h.recalibrate_again(
        frames=frames,
        seed=FIXTURE_SEED,
        predecessor_model_id=successor_of_cycle_1,
        predecessor_trained_through=h.HITL_FEEDBACK_BOUNDS.target_end.isoformat(),
        training_frame=training,
        training_labels=labels,
        events=events,
        applied=applied,
        track=h.TRACK_FIXTURE,
        cycle=2,
        recalibrated_at=VALIDATED_AT,
        dataset_sha256=FIXTURE_DATASET_SHA256,
    )
    assert lineage["source_model_id"] == successor_of_cycle_1
    assert lineage["successor_model_id"] == successor_id
    assert successor_id != first.arms[h.ARM_FROZEN].model_id
    assert lineage["source_model_id"] != lineage["successor_model_id"]


def test_incomplete_lineage_is_rejected_by_construction(
    frames: h.HitlFrames, prepared: dict
) -> None:
    """Un evento de linaje sin referencias no puede materializarse."""
    from human_feedback.lineage import LineageValidationError

    result = _run(frames, prepared)
    broken = dict(result.lineage)
    broken["feedback_references"] = []
    from human_feedback.lineage import RecalibrationLineage

    with pytest.raises(LineageValidationError):
        RecalibrationLineage.from_dict(broken)


def test_lineage_rejects_self_reference(frames: h.HitlFrames, prepared: dict) -> None:
    from human_feedback.lineage import LineageValidationError, RecalibrationLineage

    result = _run(frames, prepared)
    broken = dict(result.lineage)
    broken["successor_model_id"] = broken["source_model_id"]
    with pytest.raises(LineageValidationError):
        RecalibrationLineage.from_dict(broken)


# --------------------------------------------------------------------------
# Paquete de intervención y respuesta humana
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def package(daily_series: pd.DataFrame) -> dict:
    return h.prepare_human_package(
        daily_series=daily_series,
        depth_column=PRIMARY_DEPTH_COLUMN,
        seed=FIXTURE_SEED,
        package_id="fixture-package-id",
        campaign_id="fixture-campaign",
        contract_id="fixture-contract",
        contract_sha256="d" * 64,
    )


def test_package_is_frozen_by_its_own_hash(package: dict) -> None:
    recomputed = h.content_sha256({k: v for k, v in package.items() if k != "package_sha256"})
    assert recomputed == package["package_sha256"]
    altered = copy.deepcopy(package)
    altered["scenarios"][0]["recorded_label"] = 1 - altered["scenarios"][0]["recorded_label"]
    assert (
        h.content_sha256({k: v for k, v in altered.items() if k != "package_sha256"})
        != package["package_sha256"]
    )


def test_package_hides_the_information_that_would_induce_a_response(package: dict) -> None:
    # Se inspecciona EXACTAMENTE lo que el participante ve como datos: los
    # escenarios. La lista `hidden_from_participant` nombra deliberadamente los
    # años excluidos, y contarla como fuga sería un falso positivo.
    scenarios_serialized = json.dumps(package["scenarios"], ensure_ascii=False).lower()
    for scenario in package["scenarios"]:
        assert "clean_label" not in scenario
        assert "corrupted" not in scenario
        assert "expected_decision" not in scenario
        assert set(scenario["features"]) == set(FEATURE_COLUMNS)
    for year in ("2023", "2024", "2025"):
        assert year not in scenarios_serialized
    for leak in ("mcc", "holdout", "brier", "average_precision", "delta"):
        assert leak not in scenarios_serialized


DERIVABLE_CONCEPTS = (
    "limpia",
    "corrompid",
    "proporción",
    "proporcion",
    "revisor simulado",
    "oráculo",
    "oraculo",
)
"""Conceptos que el paquete NO puede declarar ocultos, porque son derivables de
los campos que sí muestra. Hallazgos C-01, C-02 y D-01 de las críticas
independientes."""


def _false_hiding_claims(package: dict) -> list[str]:
    hidden = " ".join(package["hidden_from_participant"]).lower()
    return [concept for concept in DERIVABLE_CONCEPTS if concept in hidden]


def test_package_does_not_claim_a_blinding_it_does_not_have(package: dict) -> None:
    """Hallazgos C-01, C-02 y D-01.

    La etiqueta correcta ES determinable desde los campos visibles, y con ella
    los registros incorrectos, su proporción y lo que haría el revisor simulado.
    Una prueba léxica de ausencia de fuga daba un falso positivo: pasaba
    justamente cuando la fuga era total. Esta fija la propiedad REAL y exige que
    el paquete no afirme lo contrario.
    """
    assert _false_hiding_claims(package) == []

    # Contingente: si el paquete dejara de declarar la determinabilidad, falla.
    assert package["explicitly_not_claimed_hidden"], "falta la declaración de lo no oculto"
    declared = " ".join(package["explicitly_not_claimed_hidden"]).lower()
    assert "determinable" in declared
    assert "revisor simulado" in declared
    assert package["blinding"]["level"] == "PARCIAL"

    # La determinabilidad debe ser un hecho del paquete, no una frase: la regla
    # reproduce exactamente `build_target`, y debe haber a la vez escenarios
    # consistentes y escenarios incorrectos, o el paquete no admitiría las tres
    # decisiones del contrato.
    derived = [
        (
            s["scenario_id"],
            int(s["observed_soil_moisture_at_target"] < s["p20_threshold_frozen"]),
            int(s["recorded_label"]),
        )
        for s in package["scenarios"]
    ]
    mismatches = [sid for sid, clean, recorded in derived if clean != recorded]
    assert 0 < len(mismatches) < len(derived), (
        "el paquete debe contener a la vez registros consistentes e incorrectos: "
        f"{len(mismatches)} de {len(derived)}"
    )


def test_a_package_that_claimed_a_false_blinding_would_be_detected(package: dict) -> None:
    """Caso negativo de la prueba anterior: si fuese vacua, esto pasaría igual."""
    tampered = copy.deepcopy(package)
    tampered["hidden_from_participant"].append("cuál sería la etiqueta limpia")
    assert _false_hiding_claims(tampered) == ["limpia"]

    tampered_2 = copy.deepcopy(package)
    tampered_2["hidden_from_participant"].append(
        "qué decisión tomó el revisor simulado en el mismo escenario"
    )
    assert _false_hiding_claims(tampered_2) == ["revisor simulado"]


def test_the_blinding_level_is_declared_as_partial_in_the_contract() -> None:
    """El contrato debe declarar el cegamiento como PARCIAL y sus consecuencias."""
    import pathlib

    contract = json.loads(
        (
            pathlib.Path(__file__).resolve().parents[1]
            / "openspec/changes/sc-08-aux-hitl/contract-H-frozen.json"
        ).read_text(encoding="utf-8")
    )
    blinding = contract["human_intervention_package"]["blinding"]
    assert blinding["level"] == "PARCIAL"
    assert blinding["what_is_blinded"]
    assert blinding["what_is_NOT_blinded"]
    consequence = blinding["consequence_declared"]
    assert "PROHIBID" in consequence, "la consecuencia debe enunciarse como prohibición"
    for denied in ("NO demuestra juicio", "NO demuestra pericia", "NO demuestra cegamiento"):
        assert denied in consequence, denied
    prohibited = " ".join(contract["prohibited_assertions"])
    for item in (
        "Cegamiento de la intervencion humana",
        "Juicio humano bajo incertidumbre",
        "Criterio propio del revisor",
    ):
        assert item in prohibited, item


def test_package_contains_no_date_beyond_the_acquisition_window(package: dict) -> None:
    """Hallazgo C-07: comprobación falsable sobre el CONTENIDO publicado."""
    h.assert_package_contains_no_data_beyond_feedback_window(package)
    tampered = copy.deepcopy(package)
    tampered["scenarios"][0]["target_date"] = "2022-01-04"
    with pytest.raises(h.HitlValidationError, match="posteriores"):
        h.assert_package_contains_no_data_beyond_feedback_window(tampered)


def test_package_records_its_presentation_order(package: dict) -> None:
    assert package["presentation_order"] == [s["scenario_id"] for s in package["scenarios"]]
    dates = [pd.Timestamp(s["emission_date"]) for s in package["scenarios"]]
    assert dates == sorted(dates)


def test_package_declares_the_controlled_human_class(package: dict) -> None:
    assert package["evidence_class"] == h.TRACK_HUMAN
    assert package["evidence_class_is_not"] == h.FORBIDDEN_EVIDENCE_CLASS
    assert package["expected_operator"]["operator_role"] in h.AUTHORIZED_OPERATOR_ROLES


def _response(package: dict, **overrides) -> dict:
    payload = {
        "schema_version": h.RESPONSE_SCHEMA_VERSION,
        "package_id": package["package_id"],
        "package_sha256": package["package_sha256"],
        "operator_id": package["expected_operator"]["operator_id"],
        "operator_role": h.AUTHORIZED_OPERATOR_ROLES[0],
        "operator_declaration": "Actúo como responsable experimental, no como agrónomo.",
        "responded_at_utc": "2026-09-21T13:00:00Z",
        "responses": [
            {
                "scenario_id": s["scenario_id"],
                "decision": h.DECISION_ACCEPT,
                "corrected_label": None,
                "reason": "fixture",
            }
            for s in package["scenarios"]
        ],
    }
    payload.update(overrides)
    return payload


def test_valid_response_is_accepted_verbatim(package: dict) -> None:
    decisions = h.validate_human_response(_response(package), package)
    assert [d["scenario_id"] for d in decisions] == package["presentation_order"]
    assert all(d["reason"] == "fixture" for d in decisions)


def test_missing_scenario_rejects_the_whole_response(package: dict) -> None:
    payload = _response(package)
    payload["responses"] = payload["responses"][:-1]
    with pytest.raises(h.HitlValidationError, match="sin responder"):
        h.validate_human_response(payload, package)


def test_duplicate_scenario_rejects_the_whole_response(package: dict) -> None:
    payload = _response(package)
    payload["responses"].append(dict(payload["responses"][0]))
    with pytest.raises(h.HitlValidationError, match="duplicado"):
        h.validate_human_response(payload, package)


def test_altered_package_hash_rejects_the_response(package: dict) -> None:
    payload = _response(package, package_sha256="e" * 64)
    with pytest.raises(h.HitlValidationError, match="package_sha256"):
        h.validate_human_response(payload, package)


def test_missing_operator_declaration_is_rejected(package: dict) -> None:
    payload = _response(package)
    payload["operator_declaration"] = ""
    with pytest.raises(h.HitlValidationError, match="declaración"):
        h.validate_human_response(payload, package)


def test_unauthorized_role_in_the_response_is_rejected(package: dict) -> None:
    payload = _response(package, operator_role="agronomist")
    with pytest.raises(h.HitlValidationError, match="rol no autorizado"):
        h.validate_human_response(payload, package)


def test_operator_identity_must_match_the_predeclared_one(package: dict) -> None:
    """Hallazgo C-10: el paquete nombra a un operador único y predeclarado."""
    payload = _response(package, operator_id="Otra Persona")
    with pytest.raises(h.HitlValidationError, match="distinta de la predeclarada"):
        h.validate_human_response(payload, package)


def test_scenario_outside_the_package_is_rejected(package: dict) -> None:
    payload = _response(package)
    payload["responses"][0] = dict(payload["responses"][0], scenario_id="H-SC-999")
    with pytest.raises(h.HitlValidationError, match="ajeno"):
        h.validate_human_response(payload, package)


# --------------------------------------------------------------------------
# Aislamiento respecto de A/B/C y del holdout
# --------------------------------------------------------------------------


def test_the_runner_never_imports_the_holdout_ledger() -> None:
    """INV-02. Dos comprobaciones complementarias, ninguna textual.

    El docstring del módulo nombra `holdout_ledger` justamente para decir que no
    lo usa, así que buscar la cadena daría un falso positivo. Y mirar
    `sys.modules` del proceso de pruebas daría un falso NEGATIVO al revés: otros
    módulos de la suite importan el ledger, de modo que en una corrida completa
    aparecería cargado por razones ajenas a este runner. Se inspecciona el AST y
    se importa el runner en un intérprete limpio.
    """
    import ast
    import pathlib
    import subprocess
    import sys

    tree = ast.parse(pathlib.Path(h.__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(f"{node.module}.{a.name}" for a in node.names)
    assert not any("holdout_ledger" in name for name in imported), imported

    repo_root = pathlib.Path(h.__file__).resolve().parents[3]
    probe = (
        "import sys;"
        "import experiment_runner.scientific_auxiliary.auxiliary_hitl_v1;"
        "print([n for n in sys.modules if n.endswith('holdout_ledger')])"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(repo_root),
        env={"PYTHONPATH": str(repo_root / "src"), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "[]", completed.stdout


def test_the_runner_never_references_abc_stage_runners() -> None:
    """Ningún símbolo de las Etapas A/B/C entra al runner de H."""
    import ast
    import pathlib

    tree = ast.parse(pathlib.Path(h.__file__).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    for forbidden in (
        "stage_a_runner",
        "stage_b_runner",
        "stage_c_runner",
        "stage_b_custody",
        "STAGE_B_BOUNDS",
        "STAGE_C_BOUNDS",
        "STAGE_C_TRAINING_BOUNDS",
        "write_stage_c_artifacts",
        "verify_stage_c_recovery",
        "run_stage_a",
        "run_stage_b",
        "run_stage_c",
    ):
        assert not any(forbidden in name for name in names), forbidden


def test_hitl_bounds_exclude_the_stage_b_and_c_periods() -> None:
    assert h.HITL_MAX_TARGET_DATE.year == 2022
    assert h.HITL_EVALUATION_BOUNDS.target_end.year == 2022
    assert h.HITL_WINDOW_BOUNDS.target_end == h.HITL_MAX_TARGET_DATE


# --------------------------------------------------------------------------
# Reproducibilidad
# --------------------------------------------------------------------------


def test_invariants_are_measured_not_declared(frames: h.HitlFrames, package: dict) -> None:
    """Hallazgo C-05: ningún invariante puede publicarse como constante True."""
    response = _response(package)
    outcome = h.run_complement_h(
        daily_series=_DAILY_SERIES_HOLDER["value"],
        depth_column=PRIMARY_DEPTH_COLUMN,
        seeds=(FIXTURE_SEED,),
        package=package,
        human_response=response,
        simulated_validated_at=h.SIMULATED_VALIDATED_AT_DEFAULT,
        human_validated_at=datetime(2026, 9, 21, 13, tzinfo=timezone.utc),
        execution_instant=datetime(2026, 9, 21, 14, tzinfo=timezone.utc),
        dataset_sha256=FIXTURE_DATASET_SHA256,
    )
    inv = outcome["invariants"]
    assert set(inv) == {
        "INV-01_no_data_after_2022_12_31",
        "INV-02_holdout_ledger_untouched",
        "INV-03_abc_artifacts_untouched",
        "INV-04_p20_frozen_once",
        "INV-05_same_evaluation_rows_all_arms",
        "INV-06_no_reviewed_row_in_evaluation",
        "INV-07_bitwise_reproducible",
        "INV-08_origin_recorded_no_mixing",
        "INV-09_no_self_reference",
        "INV-10_closed_failure_on_invalid_inputs",
    }
    import sys

    for name, body in inv.items():
        assert isinstance(body, dict), name
        assert body["kind"] in {
            "contingent_measurement",
            "structural_guard",
            "not_measured_in_run",
        }, name
        if body["kind"] == "structural_guard":
            assert body["guaranteed_by"], name
            assert body["would_break_if"], name
            assert body["holds"] is True, name
        elif body["kind"] == "contingent_measurement":
            assert "holds" in body, name
        else:
            assert body["measured_where"], name
            assert "holds" not in body, name
    # Un solo invariante es contingente, seis son guardas estructurales y tres
    # no son medibles dentro de una corrida única. Publicar una tautología como
    # medición satisfecha está prohibido por el contrato (hallazgo D-04).
    kinds = [b["kind"] for b in inv.values()]
    assert kinds.count("contingent_measurement") == 1
    assert kinds.count("structural_guard") == 6
    assert kinds.count("not_measured_in_run") == 3

    # INV-02 mide el proceso, no el runner: en la suite completa otros módulos
    # importan el ledger y la medición debe reflejarlo con fidelidad en vez de
    # devolver un True complaciente. Lo que se verifica es la FIDELIDAD de la
    # medición, no que el proceso de pruebas esté limpio.
    ambient = sorted(n for n in sys.modules if n.endswith("holdout_ledger"))
    inv_02 = inv["INV-02_holdout_ledger_untouched"]
    assert inv_02["kind"] == "contingent_measurement"
    assert sorted(inv_02["observed"]) == ambient
    assert inv_02["holds"] == (ambient == [])

    mech = outcome["mechanism"]
    assert mech["holdout_ledger_modules_loaded"] == len(ambient)
    assert mech["n_reviewed_dates_inside_evaluation"] == 0
    assert mech["n_evaluation_rows"] > 0


def test_human_track_uses_the_real_response_instant(frames: h.HitlFrames, package: dict) -> None:
    """Hallazgo C-09: retrofechar una decisión humana es un registro falso."""
    human_instant = datetime(2026, 9, 21, 13, tzinfo=timezone.utc)
    outcome = h.run_complement_h(
        daily_series=_DAILY_SERIES_HOLDER["value"],
        depth_column=PRIMARY_DEPTH_COLUMN,
        seeds=(FIXTURE_SEED,),
        package=package,
        human_response=_response(package),
        simulated_validated_at=h.SIMULATED_VALIDATED_AT_DEFAULT,
        human_validated_at=human_instant,
        execution_instant=datetime(2026, 9, 21, 14, tzinfo=timezone.utc),
        dataset_sha256=FIXTURE_DATASET_SHA256,
    )
    human_events = outcome["human_result"].events
    sim_events = outcome["sim_results"][0].events
    assert all(e["validated_at"].startswith("2026-09-21") for e in human_events)
    assert all(e["validated_at"].startswith("2022-01-01") for e in sim_events)
    assert all(e["operator_role"] == h.SIMULATED_REVIEWER_ROLE for e in sim_events)
    assert all(e["operator_role"] in h.AUTHORIZED_OPERATOR_ROLES for e in human_events)


def test_reserved_abc_and_holdout_paths_are_rejected() -> None:
    """Comprobación real de configuración, no una constante `abc_artifacts_touched: 0`."""
    assert h.assert_no_reserved_paths({"a": "/runtime/inputs/x.csv"}) == []
    # La cadena cruda también se comprueba: un enlace roto que `resolve()` no
    # puede seguir no debe evadir la guarda (hallazgo E-08).
    assert h.assert_no_reserved_paths({"a": "/no/existe/evidence/A/x.json"})
    offending = h.assert_no_reserved_paths(
        {
            "output_dir": "/runtime/evidence/A",
            "ledger": "/runtime/ledger/holdout.sqlite",
            "ok": None,
        }
    )
    assert len(offending) == 2


def test_the_contract_declares_the_invariant_classification_policy() -> None:
    """Hallazgo D-04: el contrato debe prohibir publicar tautologías como medición."""
    import pathlib

    contract = json.loads(
        (
            pathlib.Path(__file__).resolve().parents[1]
            / "openspec/changes/sc-08-aux-hitl/contract-H-frozen.json"
        ).read_text(encoding="utf-8")
    )
    policy = contract["technical_metrics"]["invariants_measurement_policy"]
    for token in ("contingent_measurement", "structural_guard", "not_measured_in_run", "PROHIBIDO"):
        assert token in policy, token
    decisive = contract["technical_metrics"]["mechanism_metrics_decisive"]
    assert not any(
        "abc_paths_opened" in m for m in decisive
    ), "una métrica declarada decisiva debe existir en el runner"
    guards = contract["technical_metrics"]["mechanism_metrics_structural_guards"]["metrics"]
    assert any("abc_paths_referenced_in_configuration" in m for m in guards)


def test_unknown_decision_is_a_closed_rejection_not_a_typeerror(
    frames: h.HitlFrames, prepared: dict
) -> None:
    """Hallazgo D-07: vocabulario desconocido con motivo, no un TypeError."""
    events = _events(prepared, frames)
    events[0]["decision"] = "DECISION_INVENTADA"
    events[0]["corrected_label"] = None
    with pytest.raises(h.HitlValidationError) as error:
        h.apply_feedback(
            feedback=frames.feedback, recorded_labels=prepared["recorded"], events=events
        )
    assert "R06-decision-vocabulary" in _rules(error.value)


def test_reserved_paths_are_detected_through_a_symlink(tmp_path) -> None:
    """Hallazgo D-13: comparar la cadena cruda dejaría pasar un enlace inocuo."""
    target = tmp_path / "evidence" / "A"
    target.mkdir(parents=True)
    link = tmp_path / "entrada-inocua"
    link.symlink_to(target)
    assert h.assert_no_reserved_paths({"output_dir": link})


def test_model_identifiers_are_deterministic() -> None:
    kwargs = dict(
        arm=h.ARM_FROZEN,
        seed=0,
        track="shared",
        training_fingerprint="f" * 64,
        label_fingerprint="0" * 64,
    )
    assert h.deterministic_model_id(**kwargs) == h.deterministic_model_id(**kwargs)
    assert h.deterministic_model_id(**{**kwargs, "seed": 1}) != h.deterministic_model_id(**kwargs)


def test_running_a_track_twice_gives_identical_results(
    frames: h.HitlFrames, prepared: dict
) -> None:
    """Reproducibilidad bit a bit de la evidencia derivada de entradas fijas."""
    first = _run(frames, prepared)
    second = _run(frames, prepared)
    assert h.canonical_json(h._track_to_json(first)) == h.canonical_json(h._track_to_json(second))


def test_canonical_json_is_stable_under_key_order() -> None:
    assert h.content_sha256({"a": 1, "b": 2}) == h.content_sha256({"b": 2, "a": 1})


# --------------------------------------------------------------------------
# Artefactos
# --------------------------------------------------------------------------


def test_artifacts_close_with_an_integrity_manifest(tmp_path) -> None:
    written = h.write_hitl_artifacts(
        tmp_path / "evidence",
        payloads={"schema_version": {"schema_version": h.ARTIFACT_SCHEMA_VERSION}},
        overwrite=False,
    )
    manifest = json.loads(written["integrity_manifest"].read_text(encoding="utf-8"))
    assert manifest["auxiliary"] == h.AUXILIARY_ID
    assert set(manifest["files"]) == {"schema_version.json"}

    import hashlib

    recomputed = hashlib.sha256(written["schema_version"].read_bytes()).hexdigest()
    assert manifest["files"]["schema_version.json"] == recomputed


def test_artifacts_refuse_to_overwrite_silently(tmp_path) -> None:
    from experiment_runner.controlled_daily_v4.artifacts import OutputDirectoryNotEmptyError

    payloads = {"schema_version": {"schema_version": h.ARTIFACT_SCHEMA_VERSION}}
    h.write_hitl_artifacts(tmp_path / "evidence", payloads=payloads)
    with pytest.raises(OutputDirectoryNotEmptyError):
        h.write_hitl_artifacts(tmp_path / "evidence", payloads=payloads)
