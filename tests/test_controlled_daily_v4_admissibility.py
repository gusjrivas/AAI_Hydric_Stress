"""Tests de admisibilidad de un candidato congelado para una ejecución concreta
de la Etapa B (`admissibility.py`). Operación deliberadamente separada del
runner de B (que no se implementa en este *change*): recibe el contrato ya
leído estructuralmente (`transfer_contract.FrozenConfigContract`, construido
aquí directamente como fixture -- no depende de una selección estocástica
real) y el contexto explícito del consumidor. Nunca abre CSV crudos ni
entrena nada."""

from __future__ import annotations

import json

import pytest

from experiment_runner.controlled_daily_v4.admissibility import (
    StageBAdmissibilityError,
    check_stage_b_admissibility,
)
from experiment_runner.controlled_daily_v4.config import (
    DEPTH_ROLE_PRIMARY,
    DEPTH_ROLE_SENSITIVITY_ONLY,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
)
from experiment_runner.controlled_daily_v4.transfer_contract import FrozenConfigContract

_VALID_CODE_IDENTITY = {
    "available": True,
    "source": "git",
    "commit": "a" * 40,
    "dirty": False,
    "reason": None,
}
_FINGERPRINT_REF = {
    "schema_version": "controlled_daily_v4_dataset_fingerprint.v2",
    "sha256": "f" * 64,
    "n_rows": 1000,
    "scope": "stage_a_eligible_rows_only",
}


def _contract(
    *,
    input_mode=INPUT_MODE_SCIENTIFIC,
    scientific_run=True,
    depth_role=DEPTH_ROLE_PRIMARY,
    candidate_produced=True,
    selected_family="logistic_regression",
    producer_code_identity=None,
    producer_dataset_fingerprint_ref=None,
) -> FrozenConfigContract:
    return FrozenConfigContract(
        schema_version="controlled_daily_v4_transfer_contract.v1",
        input_mode=input_mode,
        scientific_run=scientific_run,
        depth_column="soil_moisture_0_to_7cm",
        depth_role=depth_role,
        candidate_produced=candidate_produced,
        selected_family=selected_family if candidate_produced else None,
        single_family=None,
        soft_voting_bases=None,
        final_p20_train=0.3 if candidate_produced else None,
        final_estimator_details={},
        producer_code_identity=producer_code_identity or dict(_VALID_CODE_IDENTITY),
        producer_dataset_fingerprint_ref=producer_dataset_fingerprint_ref or dict(_FINGERPRINT_REF),
        raw={},
    )


def _write_producer_evidence(
    producer_dir,
    *,
    code_identity=None,
    validated_before_training=True,
    validation_issues=None,
    dataset_fingerprint_sha256=_FINGERPRINT_REF["sha256"],
):
    producer_dir.mkdir(parents=True, exist_ok=True)
    (producer_dir / "code_version.json").write_text(
        json.dumps(code_identity if code_identity is not None else _VALID_CODE_IDENTITY),
        encoding="utf-8",
    )
    (producer_dir / "environment.json").write_text(
        json.dumps(
            {
                "validated_before_training": validated_before_training,
                "validation_issues": validation_issues or [],
            }
        ),
        encoding="utf-8",
    )
    (producer_dir / "dataset_fingerprint.json").write_text(
        json.dumps({"sha256": dataset_fingerprint_sha256}), encoding="utf-8"
    )


def test_synthetic_candidate_admissible_for_synthetic_consumer(tmp_path):
    """No requiere ninguno de los artefactos de evidencia del productor: el
    flujo sintético→sintético se admite sin tocar ningún registro científico."""
    contract = _contract(input_mode=INPUT_MODE_SYNTHETIC, scientific_run=False)
    producer_dir = tmp_path / "producer_never_created"

    check_stage_b_admissibility(
        contract, producer_dir=producer_dir, consumer_input_mode=INPUT_MODE_SYNTHETIC
    )  # no debe lanzar


def test_synthetic_candidate_rejected_for_scientific_consumer(tmp_path):
    contract = _contract(
        input_mode=INPUT_MODE_SYNTHETIC,
        scientific_run=False,
        producer_code_identity={
            "available": False,
            "source": "unavailable",
            "commit": None,
            "dirty": None,
        },
    )
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(
        producer_dir,
        code_identity={"available": False, "source": "unavailable", "commit": None, "dirty": None},
    )

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_training_dataset_fingerprint={"sha256": _FINGERPRINT_REF["sha256"]},
        )
    assert any("scientific_run=false" in reason for reason in exc.value.reasons)


def test_scientific_run_true_alone_is_not_sufficient(tmp_path):
    """`scientific_run=true` pero con árbol sucio (`dirty=True`): se rechaza
    igual, sin que la sola bandera baste."""
    dirty_identity = {**_VALID_CODE_IDENTITY, "dirty": True}
    contract = _contract(scientific_run=True, producer_code_identity=dirty_identity)
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir, code_identity=dirty_identity)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_training_dataset_fingerprint={"sha256": _FINGERPRINT_REF["sha256"]},
        )
    assert any("dirty" in reason for reason in exc.value.reasons)


def test_happy_path_scientific_candidate_is_admitted(tmp_path):
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    check_stage_b_admissibility(
        contract,
        producer_dir=producer_dir,
        consumer_input_mode=INPUT_MODE_SCIENTIFIC,
        consumer_training_dataset_fingerprint={"sha256": _FINGERPRINT_REF["sha256"]},
    )  # no debe lanzar


def test_commit_mismatch_between_contract_and_sibling_artifact_is_rejected(tmp_path):
    """El commit embebido en frozen_config.json (vía el contrato) y el de
    `code_version.json` en el mismo directorio deben coincidir -- si
    difieren es indicio de artefactos mezclados de corridas distintas, y sin
    política de compatibilidad documentada se rechaza."""
    contract = _contract()  # commit = 'a' * 40
    producer_dir = tmp_path / "producer"
    mismatched_identity = {**_VALID_CODE_IDENTITY, "commit": "b" * 40}
    _write_producer_evidence(producer_dir, code_identity=mismatched_identity)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_training_dataset_fingerprint={"sha256": _FINGERPRINT_REF["sha256"]},
        )
    assert any("mezcla de artefactos" in reason for reason in exc.value.reasons)


def test_matching_commits_between_contract_and_sibling_do_not_block_admission(tmp_path):
    """Caso normal: el commit del productor coincide entre ambos artefactos
    de la misma corrida -- esto nunca se compara contra el commit de la
    ejecución consumidora (Etapa B), que ni siquiera se recibe como
    parámetro de esta función."""
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)  # mismo commit que el contrato

    check_stage_b_admissibility(
        contract,
        producer_dir=producer_dir,
        consumer_input_mode=INPUT_MODE_SCIENTIFIC,
        consumer_training_dataset_fingerprint={"sha256": _FINGERPRINT_REF["sha256"]},
    )  # no debe lanzar


def test_stage_b_training_fingerprint_different_from_a_is_rejected(tmp_path):
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_training_dataset_fingerprint={"sha256": "different" * 8},
        )
    assert any("huella del entrenamiento autorizado" in reason for reason in exc.value.reasons)


def test_missing_consumer_fingerprint_is_rejected_explicitly(tmp_path):
    """El contexto de datos del consumidor debe recibirse explícitamente:
    omitirlo no se trata como 'aceptar implícitamente', se rechaza."""
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract, producer_dir=producer_dir, consumer_input_mode=INPUT_MODE_SCIENTIFIC
        )
    assert any(
        "huella del conjunto de entrenamiento autorizado" in reason for reason in exc.value.reasons
    )


def test_depth_role_sensitivity_is_always_rejected_as_hard_error(tmp_path):
    contract = _contract(depth_role=DEPTH_ROLE_SENSITIVITY_ONLY)
    producer_dir = tmp_path / "producer_never_created"

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_training_dataset_fingerprint={"sha256": _FINGERPRINT_REF["sha256"]},
        )
    assert any("sensibilidad" in reason for reason in exc.value.reasons)


def test_absence_of_candidate_blocks_admissibility(tmp_path):
    contract = _contract(candidate_produced=False)
    producer_dir = tmp_path / "producer_never_created"

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_training_dataset_fingerprint={"sha256": _FINGERPRINT_REF["sha256"]},
        )
    assert any("ausencia de candidato" in reason for reason in exc.value.reasons)


def test_unknown_consumer_input_mode_is_rejected(tmp_path):
    contract = _contract()
    with pytest.raises(StageBAdmissibilityError):
        check_stage_b_admissibility(
            contract, producer_dir=tmp_path / "producer", consumer_input_mode="not_a_real_mode"
        )


def test_check_never_trains_or_reads_raw_csv():
    """Centinela textual: la admisibilidad no debe importar ni invocar el
    runner de entrenamiento/ingesta de CSV crudos."""
    import inspect

    from experiment_runner.controlled_daily_v4 import admissibility

    source = inspect.getsource(admissibility)
    for forbidden in (
        "stage_a_runner",
        "ingestion",
        "run_stage_a",
        "fit_estimator",
        "fit_candidate",
        "read_csv",
    ):
        assert forbidden not in source, forbidden
