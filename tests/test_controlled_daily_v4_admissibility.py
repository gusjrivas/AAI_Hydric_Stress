"""Tests de admisibilidad de un candidato congelado para una ejecución concreta
de la Etapa B (`admissibility.py`). Operación deliberadamente separada del
runner de B (que no se implementa en este *change*): recibe el contrato ya
leído estructuralmente y el contexto explícito del consumidor. Nunca abre CSV
crudos ni entrena nada.

Combina dos estilos de fixture, a propósito: algunos tests construyen
`FrozenConfigContract` directamente (estados puntuales, rápidos de leer);
los que reproducen los hallazgos de la revisión externa pasan por el flujo
completo escritura real (`artifacts.write_stage_a_artifacts`) -> modificación
del JSON en disco -> lectura real (`transfer_contract.load_frozen_config_contract`)
-> admisibilidad, para no depender únicamente de estados construidos a mano."""

from __future__ import annotations

import json

import pytest

from experiment_runner.controlled_daily_v4.admissibility import (
    StageBAdmissibilityError,
    check_stage_b_admissibility,
)
from experiment_runner.controlled_daily_v4.artifacts import write_stage_a_artifacts
from experiment_runner.controlled_daily_v4.config import (
    DEPTH_ROLE_PRIMARY,
    DEPTH_ROLE_SENSITIVITY_ONLY,
    FAMILY_LOGISTIC_REGRESSION,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
    PRIMARY_DEPTH_COLUMN,
    WEIGHTING_NONE,
)
from experiment_runner.controlled_daily_v4.freezing import FrozenConfig
from experiment_runner.controlled_daily_v4.models import ModelConfig
from experiment_runner.controlled_daily_v4.provenance import ProvenanceReport
from experiment_runner.controlled_daily_v4.selection import CandidateOOF
from experiment_runner.controlled_daily_v4.transfer_contract import (
    FrozenConfigContract,
    load_frozen_config_contract,
)

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
_VALID_ENVIRONMENT = {
    "validated_before_training": True,
    "validation_issues": [],
    "constraints_identity": {
        "path": "docker/experiment-v4/constraints.txt",
        "sha256": "c" * 64,
        "exists": True,
    },
    "packages": {"numpy": "1.26.4", "pandas": "2.2.2"},
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
    dataset_fingerprint_payload=None,
    environment_overrides=None,
):
    producer_dir.mkdir(parents=True, exist_ok=True)
    (producer_dir / "code_version.json").write_text(
        json.dumps(code_identity if code_identity is not None else _VALID_CODE_IDENTITY),
        encoding="utf-8",
    )
    environment_payload = {
        **_VALID_ENVIRONMENT,
        "validated_before_training": validated_before_training,
    }
    environment_payload["validation_issues"] = validation_issues or []
    if environment_overrides:
        environment_payload.update(environment_overrides)
    (producer_dir / "environment.json").write_text(
        json.dumps(environment_payload), encoding="utf-8"
    )
    if dataset_fingerprint_payload is not None:
        fingerprint_payload = dataset_fingerprint_payload
    else:
        fingerprint_payload = {**_FINGERPRINT_REF, "sha256": dataset_fingerprint_sha256}
    (producer_dir / "dataset_fingerprint.json").write_text(
        json.dumps(fingerprint_payload), encoding="utf-8"
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
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
        )
    assert any("no está marcado como científico" in reason for reason in exc.value.reasons)


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
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
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
        consumer_code_identity=_VALID_CODE_IDENTITY,
        consumer_environment_issues=[],
        consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
    )  # no debe lanzar


def test_internal_commit_mismatch_between_contract_and_sibling_artifact_is_rejected(tmp_path):
    """(a) Consistencia INTERNA del productor: el commit embebido en
    frozen_config.json (vía el contrato) y el de `code_version.json` en el
    mismo directorio deben coincidir -- si difieren es indicio de artefactos
    mezclados de corridas distintas dentro del propio productor. Distinta de
    la comparación productor-consumidor (ver los tests de compatibilidad más
    abajo)."""
    contract = _contract()  # commit = 'a' * 40
    producer_dir = tmp_path / "producer"
    mismatched_identity = {**_VALID_CODE_IDENTITY, "commit": "b" * 40}
    _write_producer_evidence(producer_dir, code_identity=mismatched_identity)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
        )
    assert any("dentro del propio productor" in reason for reason in exc.value.reasons)


def test_matching_internal_commits_do_not_block_admission_on_their_own(tmp_path):
    """Caso normal: el commit del productor coincide entre ambos artefactos
    de la misma corrida. Esto es una verificación DISTINTA e independiente
    de la compatibilidad productor-consumidor (que también debe pasar, y que
    se ejercita con `consumer_code_identity` en otros tests)."""
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)  # mismo commit que el contrato

    check_stage_b_admissibility(
        contract,
        producer_dir=producer_dir,
        consumer_input_mode=INPUT_MODE_SCIENTIFIC,
        consumer_code_identity=_VALID_CODE_IDENTITY,
        consumer_environment_issues=[],
        consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
    )  # no debe lanzar


def test_consumer_commit_differing_from_producer_is_rejected_without_accredited_policy(tmp_path):
    """(b) Compatibilidad PRODUCTOR-CONSUMIDOR: comparación real contra el
    commit de la ejecución consumidora. Los commits pueden coincidir o
    diferir; si difieren y no hay política de compatibilidad documentada, se
    rechaza -- esta verificación es distinta de la consistencia interna (a),
    que aquí pasa sin problemas (ambos artefactos del productor coinciden)."""
    contract = _contract()  # commit del productor = 'a' * 40
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)  # consistente internamente

    consumer_identity = {**_VALID_CODE_IDENTITY, "commit": "c" * 40}
    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=consumer_identity,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
        )
    assert any("compatibilidad no acreditada" in reason for reason in exc.value.reasons)


def test_consumer_commit_matching_producer_is_admitted(tmp_path):
    contract = _contract()  # commit del productor = 'a' * 40
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    check_stage_b_admissibility(
        contract,
        producer_dir=producer_dir,
        consumer_input_mode=INPUT_MODE_SCIENTIFIC,
        consumer_code_identity={**_VALID_CODE_IDENTITY, "commit": "a" * 40},
        consumer_environment_issues=[],
        consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
    )  # no debe lanzar


def test_missing_consumer_code_identity_is_rejected(tmp_path):
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
        )
    assert any(
        "identidad de código de la ejecución consumidora" in reason for reason in exc.value.reasons
    )


def test_missing_consumer_environment_issues_is_rejected(tmp_path):
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
        )
    assert any(
        "validación normativa del entorno de la ejecución consumidora" in reason
        for reason in exc.value.reasons
    )


def test_nonempty_consumer_environment_issues_is_rejected(tmp_path):
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=["python version mismatch"],
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
        )
    assert any("fallas de validación de entorno" in reason for reason in exc.value.reasons)


def test_producer_environment_isolated_flag_without_substance_is_rejected(tmp_path):
    """Una bandera aislada (`validated_before_training=True`) no alcanza:
    sin `constraints_identity`/`packages` reales, se rechaza."""
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(
        producer_dir,
        environment_overrides={"constraints_identity": None, "packages": {}},
    )

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
        )
    assert any("constraints.txt" in reason for reason in exc.value.reasons)
    assert any("paquetes efectivamente capturadas" in reason for reason in exc.value.reasons)


def test_stage_b_training_fingerprint_different_from_a_is_rejected(tmp_path):
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint={**_FINGERPRINT_REF, "sha256": "d" * 64},
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
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=[],
        )
    assert any(
        "huella del conjunto de entrenamiento autorizado" in reason for reason in exc.value.reasons
    )


def test_empty_consumer_fingerprint_dict_is_rejected_not_treated_as_matching(tmp_path):
    """Hallazgo de revisión externa: `consumer_training_dataset_fingerprint={}`
    no debe compararse como si `None == None` coincidiera -- se exige forma
    y contenido válidos antes de comparar."""
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint={},
        )
    assert not any("difiere de la huella" in reason for reason in exc.value.reasons)


def test_empty_sibling_dataset_fingerprint_file_is_rejected(tmp_path):
    """Hallazgo de revisión externa: un `dataset_fingerprint.json={}` en el
    directorio del productor (aun con la referencia embebida en
    frozen_config.json bien formada) se rechaza -- nunca se compara
    `None == None` como si coincidiera."""
    contract = _contract()
    producer_dir = tmp_path / "producer"
    _write_producer_evidence(producer_dir, dataset_fingerprint_payload={})

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=_VALID_CODE_IDENTITY,
            consumer_environment_issues=[],
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
        )
    assert not any("indicio de mezcla" in reason for reason in exc.value.reasons)


def test_depth_role_sensitivity_is_always_rejected_as_hard_error(tmp_path):
    contract = _contract(depth_role=DEPTH_ROLE_SENSITIVITY_ONLY)
    producer_dir = tmp_path / "producer_never_created"

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
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
            consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
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


# --- Regresiones de la revisión externa: escritura real -> modificación del
# --- JSON en disco -> lectura real -> admisibilidad (no solo dataclasses
# --- construidas a mano).

_FAST_PARAMS = {
    "C": 1.0,
    "weighting": WEIGHTING_NONE,
    "solver": "lbfgs",
    "max_iter": 2000,
}


def _write_real_producer_dir(
    tmp_path,
    *,
    depth_column=PRIMARY_DEPTH_COLUMN,
    input_mode=INPUT_MODE_SCIENTIFIC,
    scientific_run=True,
):
    """Directorio de productor completo y real (no una dataclass hecha a
    mano): `frozen_config.json` + `code_version.json` + `environment.json` +
    `dataset_fingerprint.json`, todos mutuamente consistentes, vía
    `artifacts.write_stage_a_artifacts`."""
    import numpy as np
    import pandas as pd

    n = 120
    frame = pd.DataFrame(
        {
            "feature_timestamp": pd.date_range("2015-01-07", periods=n),
            "segment_id": sum(([f"outer_fold_{i + 1}"] * 40 for i in range(3)), []),
        }
    )
    pattern = np.array([0, 1] * (n // 2))
    oof = CandidateOOF(
        family=FAMILY_LOGISTIC_REGRESSION,
        y_true=pattern,
        y_pred=pattern,
        y_score=np.where(pattern == 1, 0.9, 0.1),
        frame_with_segment_id=frame,
        per_fold_mcc=[1.0, 1.0, 1.0],
    )

    class _Selection:
        outcome = "STABLE_WINNER"
        global_mcc_by_family: dict = {}
        pairwise_intervals: dict = {}
        bootstrap_diagnostics: dict = {}
        equivalence_set: list = []
        stable_winner = FAMILY_LOGISTIC_REGRESSION
        selected_family = FAMILY_LOGISTIC_REGRESSION
        selection_reason = "fixture_determinista"

    frozen = FrozenConfig(
        family=FAMILY_LOGISTIC_REGRESSION,
        config=ModelConfig(FAMILY_LOGISTIC_REGRESSION, dict(_FAST_PARAMS)),
        median_mcc=0.4,
        fold_mcc=[0.3, 0.4, 0.5],
        folds=[],
    )

    out_dir = tmp_path / "producer"
    write_stage_a_artifacts(
        out_dir,
        depth_column=depth_column,
        input_mode=input_mode,
        scientific_run=scientific_run,
        resolved_config={"stage": "A"},
        provenance_report=ProvenanceReport(era5_path="era5.csv", nasa_power_path="nasa.csv"),
        environment_info=dict(_VALID_ENVIRONMENT),
        input_hashes={},
        outer_fold_boundaries=[],
        per_family_outer_results={},
        oof_by_family={FAMILY_LOGISTIC_REGRESSION: oof},
        selection_result=_Selection(),
        frozen_single_family=frozen,
        frozen_soft_voting_bases=None,
        final_p20_train=0.31,
        code_version=dict(_VALID_CODE_IDENTITY),
        dataset_fingerprint=dict(_FINGERPRINT_REF),
    )
    return out_dir


def _consumer_kwargs(**overrides):
    kwargs = dict(
        consumer_input_mode=INPUT_MODE_SCIENTIFIC,
        consumer_code_identity=dict(_VALID_CODE_IDENTITY),
        consumer_environment_issues=[],
        consumer_training_dataset_fingerprint=dict(_FINGERPRINT_REF),
    )
    kwargs.update(overrides)
    return kwargs


def test_real_valid_producer_dir_is_admitted_end_to_end(tmp_path):
    """Camino feliz sobre un directorio real (no una dataclass a mano):
    escritura -> lectura estructural -> admisibilidad."""
    producer_dir = _write_real_producer_dir(tmp_path)
    contract = load_frozen_config_contract(producer_dir)

    check_stage_b_admissibility(contract, producer_dir=producer_dir, **_consumer_kwargs())


def test_regression_mode_depth_coherence_rejected_before_reaching_admissibility(tmp_path):
    """Hallazgo 1 (revisión externa): un JSON real editado a mano para
    declarar `input_mode='synthetic'` con `scientific_run=true` ya se
    rechaza en la lectura estructural -- la admisibilidad nunca llega a
    evaluarlo."""
    producer_dir = _write_real_producer_dir(
        tmp_path, input_mode=INPUT_MODE_SYNTHETIC, scientific_run=False
    )
    path = producer_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["scientific_run"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(Exception):
        contract = load_frozen_config_contract(producer_dir)
        check_stage_b_admissibility(contract, producer_dir=producer_dir, **_consumer_kwargs())


def test_regression_candidate_config_invented_family_rejected_before_admissibility(tmp_path):
    """Hallazgo 2 (revisión externa): `selected_family='invented'` editado a
    mano sobre un artefacto real ya se rechaza al leerlo estructuralmente."""
    producer_dir = _write_real_producer_dir(tmp_path)
    path = producer_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["selected_family"] = "invented"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(Exception):
        contract = load_frozen_config_contract(producer_dir)
        check_stage_b_admissibility(contract, producer_dir=producer_dir, **_consumer_kwargs())


def test_regression_empty_fingerprint_ref_rejected_before_admissibility(tmp_path):
    """Hallazgo 3 (revisión externa): `producer.dataset_fingerprint_ref={}`
    editado a mano sobre un artefacto real ya se rechaza al leerlo
    estructuralmente, antes de cualquier comparación en admisibilidad."""
    producer_dir = _write_real_producer_dir(tmp_path)
    path = producer_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["producer"]["dataset_fingerprint_ref"] = {}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(Exception):
        contract = load_frozen_config_contract(producer_dir)
        check_stage_b_admissibility(contract, producer_dir=producer_dir, **_consumer_kwargs())


def test_regression_empty_sibling_fingerprint_file_rejected_by_admissibility(tmp_path):
    """Hallazgo 3 (revisión externa), variante que SÍ llega a admisibilidad:
    la referencia embebida en frozen_config.json queda intacta y válida,
    pero el archivo hermano `dataset_fingerprint.json` se corrompe a `{}`
    por separado -- la lectura estructural no lo toca (no es su responsabilidad),
    y es `check_stage_b_admissibility` quien lo rechaza."""
    producer_dir = _write_real_producer_dir(tmp_path)
    contract = load_frozen_config_contract(producer_dir)  # pasa: no se tocó frozen_config.json
    (producer_dir / "dataset_fingerprint.json").write_text("{}", encoding="utf-8")

    with pytest.raises(StageBAdmissibilityError):
        check_stage_b_admissibility(contract, producer_dir=producer_dir, **_consumer_kwargs())


def test_regression_consumer_commit_mismatch_rejected_on_real_artifact(tmp_path):
    """Hallazgo 4 (revisión externa): sobre un artefacto real, íntegro y
    consistente, la compatibilidad productor-consumidor todavía puede
    rechazar por un commit de consumidor distinto, sin política acreditada."""
    producer_dir = _write_real_producer_dir(tmp_path)
    contract = load_frozen_config_contract(producer_dir)

    with pytest.raises(StageBAdmissibilityError) as exc:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            **_consumer_kwargs(consumer_code_identity={**_VALID_CODE_IDENTITY, "commit": "e" * 40}),
        )
    assert any("compatibilidad no acreditada" in reason for reason in exc.value.reasons)
