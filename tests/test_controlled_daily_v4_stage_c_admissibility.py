"""Tests de admisibilidad de un veredicto de la Etapa B como habilitación de
una ejecución concreta de la Etapa C (`admissibility.check_stage_c_admissibility`).

Nunca abre CSV crudos ni entrena nada: solo lee artefactos ya persistidos de
A (`producer_dir`) y B (`stage_b_dir`), escritos aquí directamente como JSON
mínimo (mismo estilo que `test_controlled_daily_v4_admissibility.py`)."""

from __future__ import annotations

import json

import pytest

from experiment_runner.controlled_daily_v4.admissibility import (
    StageCAdmissibilityError,
    check_stage_c_admissibility,
)
from experiment_runner.controlled_daily_v4.artifacts import STAGE_B_ARTIFACT_SCHEMA_VERSION
from experiment_runner.controlled_daily_v4.config import (
    BOOTSTRAP_BLOCK_DAYS,
    BOOTSTRAP_REPLICAS_DEFAULT,
    BOOTSTRAP_SEED,
    DEPTH_ROLE_PRIMARY,
    DEPTH_ROLE_SENSITIVITY_ONLY,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
)
from experiment_runner.controlled_daily_v4.dataset_fingerprint import (
    DATASET_FINGERPRINT_FORMAT_VERSION,
    FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS,
)
from experiment_runner.controlled_daily_v4.transfer_contract import FrozenConfigContract

_VALID_B_TRAINING_FINGERPRINT = {
    "schema_version": DATASET_FINGERPRINT_FORMAT_VERSION,
    "sha256": "b" * 64,
    "n_rows": 100,
    "scope": FINGERPRINT_SCOPE_STAGE_A_ELIGIBLE_ROWS,
}

_VALID_CODE_IDENTITY = {
    "available": True,
    "source": "git",
    "commit": "a" * 40,
    "dirty": False,
    "reason": None,
}
_CONSUMER_CODE_IDENTITY = {
    "available": True,
    "source": "git",
    "commit": "a" * 40,  # mismo commit que B: caso normal
    "dirty": False,
    "reason": None,
}


def _build_valid_environment_payload() -> dict:
    from experiment_runner.controlled_daily_v4.environment import (
        TRACKED_PACKAGES,
        capture_constraints_identity,
        load_environment_reference,
    )

    reference = load_environment_reference()
    module_to_display = {module: display for display, module in TRACKED_PACKAGES}
    packages = {
        module_to_display[module]: version for module, version in reference.packages.items()
    }
    return {
        "python_version": reference.python_version,
        "packages": packages,
        "validated_before_training": True,
        "validation_issues": [],
        "constraints_identity": capture_constraints_identity(),
    }


_VALID_ENVIRONMENT = _build_valid_environment_payload()

_FROZEN_CONFIG_RAW = {
    "schema_version": "controlled_daily_v4_transfer_contract.v1",
    "input_mode": "scientific",
    "scientific_run": True,
    "candidate_produced": True,
    "selected_family": "logistic_regression",
}


def _contract(
    *,
    depth_role=DEPTH_ROLE_PRIMARY,
    input_mode="scientific",
    scientific_run=True,
    producer_code_identity=None,
    producer_dataset_fingerprint_ref=None,
):
    return FrozenConfigContract(
        schema_version="controlled_daily_v4_transfer_contract.v1",
        input_mode=input_mode,
        scientific_run=scientific_run,
        depth_column="soil_moisture_0_to_7cm",
        depth_role=depth_role,
        candidate_produced=True,
        selected_family="logistic_regression",
        single_family=None,
        soft_voting_bases=None,
        soft_voting_combination_weights=None,
        final_p20_train=0.3,
        final_estimator_details={},
        producer_code_identity=(
            producer_code_identity
            if producer_code_identity is not None
            else dict(_VALID_CODE_IDENTITY)
        ),
        producer_dataset_fingerprint_ref=(
            producer_dataset_fingerprint_ref
            if producer_dataset_fingerprint_ref is not None
            else dict(_VALID_B_TRAINING_FINGERPRINT)
        ),
        raw=dict(_FROZEN_CONFIG_RAW),
    )


def _write_producer_a_evidence(
    producer_dir,
    *,
    code_identity=None,
    dataset_fingerprint=None,
    validation_issues=None,
):
    """Evidencia REAL de A persistida en `producer_dir` (`code_version.json`,
    `environment.json`, `dataset_fingerprint.json`) -- requerida desde la
    revalidación histórica A→B que `check_stage_c_admissibility` ahora
    reutiliza (`check_stage_b_admissibility`, revisión dirigida, hallazgo 2,
    tercera ronda). Por defecto coincide exactamente con
    `_VALID_CODE_IDENTITY`/`_VALID_B_TRAINING_FINGERPRINT`, de modo que el
    camino científico feliz sea admisible sin ningún motivo de rechazo."""
    producer_dir.mkdir(parents=True, exist_ok=True)
    (producer_dir / "code_version.json").write_text(
        json.dumps(code_identity if code_identity is not None else _VALID_CODE_IDENTITY),
        encoding="utf-8",
    )
    environment_payload = {**_VALID_ENVIRONMENT, "validation_issues": validation_issues or []}
    (producer_dir / "environment.json").write_text(
        json.dumps(environment_payload), encoding="utf-8"
    )
    (producer_dir / "dataset_fingerprint.json").write_text(
        json.dumps(
            dataset_fingerprint
            if dataset_fingerprint is not None
            else dict(_VALID_B_TRAINING_FINGERPRINT)
        ),
        encoding="utf-8",
    )


def _valid_diagnostics(
    *,
    replicas_valid=BOOTSTRAP_REPLICAS_DEFAULT,
    replicas_requested=BOOTSTRAP_REPLICAS_DEFAULT,
    replicas_discarded=0,
    normative=True,
    seed=BOOTSTRAP_SEED,
    block_length=BOOTSTRAP_BLOCK_DAYS,
):
    """Diagnostics NORMATIVOS reales por defecto (revisión dirigida, hallazgo
    1, tercera ronda): `replicas_requested`/`seed`/`block_length` coinciden
    con la configuración normativa del protocolo, de modo que
    `compute_is_normative_configuration` recalculada por
    `check_stage_c_admissibility` sobre estos valores efectivamente coincide
    con `normative=True` -- ya no basta con declarar la bandera sola."""
    return {
        "replicas_valid": replicas_valid,
        "replicas_requested": replicas_requested,
        "replicas_discarded": replicas_discarded,
        "normative": normative,
        "seed": seed,
        "block_length": block_length,
    }


def _write_stage_b_evidence(
    stage_b_dir,
    producer_dir,
    *,
    verdict="CANDIDATE_VALIDATED",
    predictions_available=True,
    mcc_candidate=0.4,
    interval_lower=0.0,
    interval_upper=0.4,
    diagnostics=None,
    bootstrap_executed=True,
    scientific_run=True,
    input_mode=None,
    code_identity=None,
    validation_issues=None,
    embedded_frozen_config_raw=None,
    referenced_producer_dir=None,
    training_dataset_fingerprint=None,
    omit_training_dataset_fingerprint=False,
    write_producer_evidence=True,
    resolved_config_extra=None,
):
    resolved_input_mode = (
        input_mode
        if input_mode is not None
        else (INPUT_MODE_SCIENTIFIC if scientific_run else INPUT_MODE_SYNTHETIC)
    )
    if write_producer_evidence:
        _write_producer_a_evidence(producer_dir)
    stage_b_dir.mkdir(parents=True, exist_ok=True)
    (stage_b_dir / "schema_version.json").write_text(
        json.dumps({"schema_version": STAGE_B_ARTIFACT_SCHEMA_VERSION}), encoding="utf-8"
    )
    (stage_b_dir / "resolved_config.json").write_text(
        json.dumps(
            {
                "scientific_run": scientific_run,
                "input_mode": resolved_input_mode,
                **(resolved_config_extra or {}),
            }
        ),
        encoding="utf-8",
    )
    (stage_b_dir / "decision.json").write_text(
        json.dumps({"verdict": verdict, "predictions_available": predictions_available}),
        encoding="utf-8",
    )
    (stage_b_dir / "metrics.json").write_text(
        json.dumps({"mcc_candidate": {"value": mcc_candidate, "status": "defined"}}),
        encoding="utf-8",
    )
    (stage_b_dir / "bootstrap.json").write_text(
        json.dumps(
            {
                "bootstrap_executed": bootstrap_executed,
                "interval_lower": interval_lower,
                "interval_upper": interval_upper,
                "diagnostics": diagnostics if diagnostics is not None else _valid_diagnostics(),
            }
        ),
        encoding="utf-8",
    )
    (stage_b_dir / "code_version.json").write_text(
        json.dumps(code_identity if code_identity is not None else _VALID_CODE_IDENTITY),
        encoding="utf-8",
    )
    environment_payload = {**_VALID_ENVIRONMENT, "validation_issues": validation_issues or []}
    (stage_b_dir / "environment.json").write_text(json.dumps(environment_payload), encoding="utf-8")
    (stage_b_dir / "producer_reference.json").write_text(
        json.dumps(
            {
                "producer_dir": str(
                    referenced_producer_dir if referenced_producer_dir is not None else producer_dir
                ),
                "producer_frozen_config": (
                    embedded_frozen_config_raw
                    if embedded_frozen_config_raw is not None
                    else dict(_FROZEN_CONFIG_RAW)
                ),
            }
        ),
        encoding="utf-8",
    )
    if not omit_training_dataset_fingerprint:
        (stage_b_dir / "training_dataset_fingerprint.json").write_text(
            json.dumps(
                training_dataset_fingerprint
                if training_dataset_fingerprint is not None
                else dict(_VALID_B_TRAINING_FINGERPRINT)
            ),
            encoding="utf-8",
        )


def test_happy_path_scientific_is_admitted(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)

    check_stage_c_admissibility(
        _contract(),
        stage_b_dir=stage_b_dir,
        producer_dir=producer_dir,
        consumer_input_mode=INPUT_MODE_SCIENTIFIC,
        consumer_code_identity=_CONSUMER_CODE_IDENTITY,
        consumer_environment_issues=[],
    )  # no debe lanzar


def test_synthetic_flow_admitted_without_full_evidence(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    stage_b_dir.mkdir(parents=True)
    (stage_b_dir / "producer_reference.json").write_text(
        json.dumps(
            {"producer_dir": str(producer_dir), "producer_frozen_config": dict(_FROZEN_CONFIG_RAW)}
        ),
        encoding="utf-8",
    )
    (stage_b_dir / "schema_version.json").write_text(
        json.dumps({"schema_version": STAGE_B_ARTIFACT_SCHEMA_VERSION}), encoding="utf-8"
    )
    (stage_b_dir / "resolved_config.json").write_text(
        json.dumps({"scientific_run": False, "input_mode": "synthetic"}), encoding="utf-8"
    )
    (stage_b_dir / "decision.json").write_text(
        json.dumps({"verdict": "CANDIDATE_VALIDATED", "predictions_available": True}),
        encoding="utf-8",
    )
    (stage_b_dir / "metrics.json").write_text(
        json.dumps({"mcc_candidate": {"value": 0.4, "status": "defined"}}), encoding="utf-8"
    )
    (stage_b_dir / "bootstrap.json").write_text(
        json.dumps(
            {
                "bootstrap_executed": True,
                "interval_lower": 0.0,
                "interval_upper": 0.4,
                "diagnostics": _valid_diagnostics(),
            }
        ),
        encoding="utf-8",
    )

    check_stage_c_admissibility(
        _contract(input_mode="synthetic", scientific_run=False),
        stage_b_dir=stage_b_dir,
        producer_dir=producer_dir,
        consumer_input_mode=INPUT_MODE_SYNTHETIC,
    )  # no debe lanzar


def test_synthetic_approval_never_enables_scientific_c(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, scientific_run=False)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(input_mode="synthetic", scientific_run=False),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("aprobación sintética" in reason for reason in exc.value.reasons)


def test_sensitivity_depth_role_always_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(depth_role=DEPTH_ROLE_SENSITIVITY_ONLY),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("depth_role" in reason for reason in exc.value.reasons)


def test_non_validated_verdict_is_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir, producer_dir, verdict="CANDIDATE_NOT_VALIDATED", predictions_available=False
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("CANDIDATE_VALIDATED" in reason for reason in exc.value.reasons)


def test_isolated_decision_json_is_not_sufficient_mcc_mismatch(tmp_path):
    """decision.json dice CANDIDATE_VALIDATED, pero metrics.json no lo
    sustenta (MCC <= 0): se rechaza -- nunca se confía únicamente en 'verdict'."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, mcc_candidate=-0.1)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("mcc_candidate" in reason for reason in exc.value.reasons)


def test_isolated_decision_json_is_not_sufficient_bootstrap_mismatch(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, interval_lower=-0.5)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("interval_lower" in reason for reason in exc.value.reasons)


def test_incomplete_evidence_missing_bootstrap_json_is_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)
    (stage_b_dir / "bootstrap.json").unlink()

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("bootstrap.json" in reason for reason in exc.value.reasons)


def test_lineage_to_a_broken_by_wrong_producer_dir_reference(tmp_path):
    producer_dir = tmp_path / "producer_a"
    other_dir = tmp_path / "some_other_dir"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, referenced_producer_dir=other_dir)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("linaje" in reason for reason in exc.value.reasons)


def test_lineage_to_a_broken_by_drifted_embedded_frozen_config(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    drifted = {**_FROZEN_CONFIG_RAW, "selected_family": "random_forest"}
    _write_stage_b_evidence(stage_b_dir, producer_dir, embedded_frozen_config_raw=drifted)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("producer_frozen_config" in reason for reason in exc.value.reasons)


def test_code_identity_mismatch_without_documented_policy_is_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)
    different_commit_consumer = {**_CONSUMER_CODE_IDENTITY, "commit": "b" * 40}

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=different_commit_consumer,
            consumer_environment_issues=[],
        )
    assert any("compatibilidad no acreditada" in reason for reason in exc.value.reasons)


def test_missing_consumer_code_identity_is_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=None,
            consumer_environment_issues=[],
        )
    assert any("identidad de código" in reason for reason in exc.value.reasons)


def test_inconsistent_input_mode_scientific_run_is_rejected(tmp_path):
    """Revisión dirigida (hallazgo 1): B con input_mode='synthetic' y
    scientific_run=True es internamente incoherente -- nunca es admisible
    como antecedente científico, aunque scientific_run diga True."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, scientific_run=True, input_mode="synthetic")

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("input_mode" in reason for reason in exc.value.reasons)


def test_infinite_mcc_is_rejected(tmp_path):
    """Revisión dirigida (hallazgo 1): un MCC no finito nunca sustenta
    CANDIDATE_VALIDATED, aunque sea > 0 en apariencia (inf > 0 es True)."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, mcc_candidate=float("inf"))

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("no es finito" in reason for reason in exc.value.reasons)


def test_boolean_mcc_is_rejected(tmp_path):
    """Revisión dirigida (hallazgo 1): un booleano nunca es una métrica MCC
    válida, aunque `isinstance(True, (int, float))` sea verdadero en Python."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, mcc_candidate=True)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("no es un valor numérico válido" in reason for reason in exc.value.reasons)


def test_inverted_bootstrap_interval_is_rejected(tmp_path):
    """Revisión dirigida (hallazgo 1): interval_lower > interval_upper es un
    intervalo invertido, sin importar que interval_lower solo cumpla >= -0.05."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, interval_lower=0.5, interval_upper=0.1)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("invertido" in reason for reason in exc.value.reasons)


def test_zero_valid_bootstrap_replicas_is_rejected(tmp_path):
    """Revisión dirigida (hallazgo 1): diagnostics.replicas_valid=0 nunca
    sustenta un intervalo bootstrap, aunque bootstrap_executed sea True y el
    intervalo persistido tenga forma numérica válida."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        diagnostics=_valid_diagnostics(
            replicas_valid=0, replicas_requested=200, replicas_discarded=200
        ),
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("replicas_valid" in reason for reason in exc.value.reasons)


def test_bootstrap_support_below_eighty_percent_is_rejected(tmp_path):
    """La compuerta B->C aplica el mismo piso de soporte que el propio
    bootstrap (>= 80 % de replicas validas): 3999/5000 se rechaza aunque el
    intervalo persistido tenga forma numerica valida y replicas_valid > 0."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        diagnostics=_valid_diagnostics(
            replicas_valid=3999,
            replicas_requested=BOOTSTRAP_REPLICAS_DEFAULT,
            replicas_discarded=BOOTSTRAP_REPLICAS_DEFAULT - 3999,
        ),
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("replicas_valid" in reason for reason in exc.value.reasons)


def test_bootstrap_support_at_exactly_eighty_percent_is_admissible(tmp_path):
    """Contraparte exacta del piso: 4000/5000 satisface el soporte y no
    aporta ninguna razon de rechazo por replicas."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        diagnostics=_valid_diagnostics(
            replicas_valid=4000,
            replicas_requested=BOOTSTRAP_REPLICAS_DEFAULT,
            replicas_discarded=BOOTSTRAP_REPLICAS_DEFAULT - 4000,
        ),
    )

    check_stage_c_admissibility(
        _contract(),
        stage_b_dir=stage_b_dir,
        producer_dir=producer_dir,
        consumer_input_mode=INPUT_MODE_SCIENTIFIC,
        consumer_code_identity=_CONSUMER_CODE_IDENTITY,
        consumer_environment_issues=[],
    )


def test_rejected_stage_c_case_never_touches_holdout(tmp_path, monkeypatch):
    """Spy: ningún caso rechazado por `check_stage_c_admissibility` reserva el
    ledger ni accede a datos del holdout -- esta función nunca debe llamar a
    `holdout_ledger.reserve_holdout` ni a ninguna función de carga/hash/
    agregación del holdout por sí misma."""
    import experiment_runner.controlled_daily_v4.holdout_ledger as holdout_ledger_module
    import experiment_runner.controlled_daily_v4.ingestion as ingestion_module

    spy_calls: list[str] = []
    for name in ("reserve_holdout", "confirm_holdout_open"):
        monkeypatch.setattr(
            holdout_ledger_module,
            name,
            lambda *a, __n=name, **k: spy_calls.append(__n),
        )
    for name in ("load_era5_hourly_raw", "load_nasa_power_daily_raw", "aggregate_era5_daily"):
        monkeypatch.setattr(ingestion_module, name, lambda *a, __n=name, **k: spy_calls.append(__n))

    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir, mcc_candidate=float("inf"))

    with pytest.raises(StageCAdmissibilityError):
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )

    assert spy_calls == []


def test_consumer_environment_issues_present_is_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=["python_version mismatch"],
        )
    assert any("fallas de validación de entorno" in reason for reason in exc.value.reasons)


# --- Revisión dirigida, tercera ronda -------------------------------------
#
# Punto 1: la bandera `diagnostics.normative=True` declarada nunca basta por
# sí sola -- se recalcula sobre los parámetros efectivamente persistidos.
# Punto 2: revalidación del vínculo HISTÓRICO A→B (reutiliza
# `check_stage_b_admissibility` contra la evidencia REAL de `producer_dir`).


def test_trivial_bootstrap_params_with_normative_flag_true_is_rejected(tmp_path):
    """Reproducción EXACTA de la revisión dirigida (hallazgo 1, tercera
    ronda): `replicas_requested=1, replicas_valid=1, replicas_discarded=0,
    seed=0, block_length=1, normative=True` -- la bandera sola no constituye
    evidencia suficiente, aunque los tres contadores sean formalmente
    consistentes entre sí (1 + 0 == 1)."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        diagnostics={
            "replicas_valid": 1,
            "replicas_requested": 1,
            "replicas_discarded": 0,
            "normative": True,
            "seed": 0,
            "block_length": 1,
        },
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "no corresponde a la configuración normativa real" in reason for reason in exc.value.reasons
    )


def test_missing_bootstrap_seed_and_block_length_is_rejected(tmp_path):
    """`diagnostics` sin `seed`/`block_length` (ausentes, no solo con valor
    trivial) nunca permite verificar la configuración normativa real: se
    rechaza explícitamente, sin asumir un valor por defecto."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        diagnostics={
            "replicas_valid": BOOTSTRAP_REPLICAS_DEFAULT,
            "replicas_requested": BOOTSTRAP_REPLICAS_DEFAULT,
            "replicas_discarded": 0,
            "normative": True,
        },
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "no se puede verificar la configuración normativa real" in reason
        for reason in exc.value.reasons
    )


def test_boolean_bootstrap_seed_is_rejected(tmp_path):
    """Un booleano donde se requiere un entero (`seed=True`) nunca se acepta
    como configuración normativa válida, aunque `isinstance(True, int)` sea
    verdadero en Python."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        diagnostics=_valid_diagnostics(seed=True),
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "no se puede verificar la configuración normativa real" in reason
        for reason in exc.value.reasons
    )


def test_bootstrap_declared_reduced_config_with_normative_false_still_rejected_as_synthetic_like(
    tmp_path,
):
    """Una configuración reducida y declarada honestamente como
    `normative=False` tampoco habilita C científica (el camino científico
    exige la normativa real, no solo coherencia consigo misma)."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        diagnostics=_valid_diagnostics(
            replicas_valid=1,
            replicas_requested=1,
            replicas_discarded=0,
            seed=0,
            block_length=1,
            normative=False,
        ),
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "no corresponde a la configuración normativa real" in reason for reason in exc.value.reasons
    )


def test_resolved_config_seed_contradicts_bootstrap_diagnostics_is_rejected(tmp_path):
    """`resolved_config.json.seed` distinto del `seed` efectivamente
    consumido por el bootstrap (`diagnostics.seed`) es indicio de artefactos
    mezclados de corridas distintas -- se rechaza aunque ambos, por separado,
    luzcan normativos."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        resolved_config_extra={
            "seed": BOOTSTRAP_SEED + 1,
            "bootstrap_replicas": BOOTSTRAP_REPLICAS_DEFAULT,
        },
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("resolved_config.json'.seed" in reason for reason in exc.value.reasons)


def test_resolved_config_bootstrap_replicas_contradicts_diagnostics_is_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        resolved_config_extra={"seed": BOOTSTRAP_SEED, "bootstrap_replicas": 1},
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("resolved_config.json'.bootstrap_replicas" in reason for reason in exc.value.reasons)


def test_full_normative_antecedent_is_admitted(tmp_path):
    """Antecedente científico COMPLETO y normativo (contadores, seed, bloque
    y `resolved_config.json` todos coherentes con el protocolo): se admite."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        resolved_config_extra={
            "seed": BOOTSTRAP_SEED,
            "bootstrap_replicas": BOOTSTRAP_REPLICAS_DEFAULT,
        },
    )

    check_stage_c_admissibility(
        _contract(),
        stage_b_dir=stage_b_dir,
        producer_dir=producer_dir,
        consumer_input_mode=INPUT_MODE_SCIENTIFIC,
        consumer_code_identity=_CONSUMER_CODE_IDENTITY,
        consumer_environment_issues=[],
    )  # no debe lanzar


def test_b_training_fingerprint_sha256_different_from_a_is_rejected(tmp_path):
    """Reproducción EXACTA de la revisión dirigida (hallazgo 2, tercera
    ronda): `training_dataset_fingerprint.json` de B estructuralmente válido,
    pero con `sha256` distinto del de A -- se rechaza, aunque el formato sea
    válido en ambos casos."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    drifted_b_fingerprint = {**_VALID_B_TRAINING_FINGERPRINT, "sha256": "c" * 64}
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        training_dataset_fingerprint=drifted_b_fingerprint,
    )

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any("Revalidación histórica A→B" in reason for reason in exc.value.reasons)
    assert any("sha256" in reason for reason in exc.value.reasons)


def test_missing_a_code_version_evidence_is_rejected(tmp_path):
    """Reproducción EXACTA de la revisión dirigida (hallazgo 2, tercera
    ronda): tras eliminar `code_version.json` del directorio de A, el
    antecedente deja de ser admisible (antes, `check_stage_c_admissibility`
    nunca releía la evidencia real de A)."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)
    (producer_dir / "code_version.json").unlink()

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "Revalidación histórica A→B" in reason and "code_version.json" in reason
        for reason in exc.value.reasons
    )


def test_missing_a_environment_evidence_is_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)
    (producer_dir / "environment.json").unlink()

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "Revalidación histórica A→B" in reason and "environment.json" in reason
        for reason in exc.value.reasons
    )


def test_missing_a_dataset_fingerprint_evidence_is_rejected(tmp_path):
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(stage_b_dir, producer_dir)
    (producer_dir / "dataset_fingerprint.json").unlink()

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "Revalidación histórica A→B" in reason and "dataset_fingerprint.json" in reason
        for reason in exc.value.reasons
    )


def test_historical_code_identity_dirty_is_rejected(tmp_path):
    """Identidad de código HISTÓRICA incoherente (árbol de A sucio en su
    momento): la revalidación histórica A→B lo rechaza, aunque la ejecución
    consumidora actual de C tenga un árbol limpio."""
    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    dirty_identity = {**_VALID_CODE_IDENTITY, "dirty": True}
    _write_stage_b_evidence(stage_b_dir, producer_dir)
    (producer_dir / "code_version.json").write_text(json.dumps(dirty_identity), encoding="utf-8")

    with pytest.raises(StageCAdmissibilityError) as exc:
        check_stage_c_admissibility(
            _contract(producer_code_identity=dirty_identity),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "Revalidación histórica A→B" in reason and "dirty=False" in reason
        for reason in exc.value.reasons
    )


def test_third_round_rejections_never_reserve_holdout_or_touch_data(tmp_path, monkeypatch):
    """Spy (revisión dirigida, tercera ronda): ninguno de los rechazos nuevos
    (configuración normativa recalculada, revalidación histórica A→B) reserva
    el ledger ni accede a datos del holdout -- se ejercitan ambos motivos de
    rechazo en la misma corrida."""
    import experiment_runner.controlled_daily_v4.holdout_ledger as holdout_ledger_module
    import experiment_runner.controlled_daily_v4.ingestion as ingestion_module

    spy_calls: list[str] = []
    for name in ("reserve_holdout", "confirm_holdout_open"):
        monkeypatch.setattr(
            holdout_ledger_module,
            name,
            lambda *a, __n=name, **k: spy_calls.append(__n),
        )
    for name in ("load_era5_hourly_raw", "load_nasa_power_daily_raw", "aggregate_era5_daily"):
        monkeypatch.setattr(ingestion_module, name, lambda *a, __n=name, **k: spy_calls.append(__n))

    producer_dir = tmp_path / "producer_a"
    stage_b_dir = tmp_path / "stage_b"
    _write_stage_b_evidence(
        stage_b_dir,
        producer_dir,
        diagnostics={
            "replicas_valid": 1,
            "replicas_requested": 1,
            "replicas_discarded": 0,
            "normative": True,
            "seed": 0,
            "block_length": 1,
        },
    )
    (producer_dir / "code_version.json").unlink()

    with pytest.raises(StageCAdmissibilityError):
        check_stage_c_admissibility(
            _contract(),
            stage_b_dir=stage_b_dir,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_CONSUMER_CODE_IDENTITY,
            consumer_environment_issues=[],
        )

    assert spy_calls == []
