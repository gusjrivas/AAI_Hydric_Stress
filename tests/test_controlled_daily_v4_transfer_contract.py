"""Tests de la lectura y validación ESTRUCTURAL del contrato de transferencia
A→B (`transfer_contract.py`). Exclusivamente sintéticos: nunca abren un CSV
real ni entrenan nada -- construyen `frozen_config.json` directamente vía
`artifacts.write_stage_a_artifacts` con `FrozenConfig`/`ModelConfig`
sintéticos, para que el resultado sea determinista (sin depender de qué
familia gane una selección estocástica)."""

from __future__ import annotations

import json

import pytest

from experiment_runner.controlled_daily_v4.artifacts import (
    TRANSFER_CONTRACT_SCHEMA_VERSION,
    write_stage_a_artifacts,
)
from experiment_runner.controlled_daily_v4.config import (
    DEPTH_ROLE_PRIMARY,
    DEPTH_ROLE_SENSITIVITY_ONLY,
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    FAMILY_SOFT_VOTING,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
    PRIMARY_DEPTH_COLUMN,
    SENSITIVITY_DEPTH_COLUMN,
    WEIGHTING_NONE,
)
from experiment_runner.controlled_daily_v4.freezing import FrozenConfig
from experiment_runner.controlled_daily_v4.models import ModelConfig
from experiment_runner.controlled_daily_v4.provenance import ProvenanceReport
from experiment_runner.controlled_daily_v4.selection import CandidateOOF
from experiment_runner.controlled_daily_v4.transfer_contract import (
    TransferContractSchemaError,
    TransferContractValidationError,
    load_frozen_config_contract,
)

_CODE_VERSION = {
    "available": True,
    "source": "git",
    "commit": "a" * 40,
    "dirty": False,
    "reason": None,
}
_DATASET_FINGERPRINT = {
    "schema_version": "controlled_daily_v4_dataset_fingerprint.v2",
    "sha256": "deadbeef" * 8,
    "n_rows": 123,
    "scope": "stage_a_eligible_rows_only",
}

_SEGMENT_SIZE = 40


def _dummy_oof(family: str) -> CandidateOOF:
    import numpy as np
    import pandas as pd

    n = _SEGMENT_SIZE * 3
    frame = pd.DataFrame(
        {
            "feature_timestamp": pd.date_range("2015-01-07", periods=n),
            "segment_id": sum(([f"outer_fold_{i + 1}"] * _SEGMENT_SIZE for i in range(3)), []),
        }
    )
    pattern = np.array([0, 1] * (n // 2))
    return CandidateOOF(
        family=family,
        y_true=pattern,
        y_pred=pattern,
        y_score=np.where(pattern == 1, 0.9, 0.1),
        frame_with_segment_id=frame,
        per_fold_mcc=[1.0, 1.0, 1.0],
    )


class _FakeSelectionResult:
    """Doble de prueba determinista: evita depender de qué familia gana una
    selección estocástica real (`select_family`) para que los tests de
    round-trip del contrato sean deterministas."""

    def __init__(self, selected_family: str | None):
        self.outcome = "STABLE_WINNER" if selected_family else "NO_VALID_SELECTION"
        self.global_mcc_by_family = {}
        self.pairwise_intervals: dict = {}
        self.bootstrap_diagnostics: dict = {}
        self.equivalence_set: list[str] = []
        self.stable_winner = selected_family
        self.selected_family = selected_family
        self.selection_reason = "fixture_determinista"


def _selection_result(selected_family: str | None = FAMILY_LOGISTIC_REGRESSION):
    return _FakeSelectionResult(selected_family)


def _write_contract(
    tmp_path,
    *,
    depth_column=PRIMARY_DEPTH_COLUMN,
    input_mode=INPUT_MODE_SCIENTIFIC,
    scientific_run=True,
    frozen_single_family=None,
    frozen_soft_voting_bases=None,
    soft_voting_combination_weights=None,
    final_p20_train=None,
    selection_result=None,
    code_version=_CODE_VERSION,
    dataset_fingerprint=_DATASET_FINGERPRINT,
):
    out_dir = tmp_path / "out"
    write_stage_a_artifacts(
        out_dir,
        depth_column=depth_column,
        input_mode=input_mode,
        scientific_run=scientific_run,
        resolved_config={"stage": "A"},
        provenance_report=ProvenanceReport(era5_path="era5.csv", nasa_power_path="nasa.csv"),
        environment_info={"validated_before_training": True, "validation_issues": []},
        input_hashes={},
        outer_fold_boundaries=[],
        per_family_outer_results={},
        oof_by_family={
            FAMILY_LOGISTIC_REGRESSION: _dummy_oof(FAMILY_LOGISTIC_REGRESSION),
        },
        selection_result=selection_result or _selection_result(),
        frozen_single_family=frozen_single_family,
        frozen_soft_voting_bases=frozen_soft_voting_bases,
        soft_voting_combination_weights=soft_voting_combination_weights,
        final_p20_train=final_p20_train,
        code_version=code_version,
        dataset_fingerprint=dataset_fingerprint,
    )
    return out_dir


_EQUAL_COMBINATION_WEIGHTS = {
    FAMILY_LOGISTIC_REGRESSION: 1.0 / 3.0,
    FAMILY_RANDOM_FOREST: 1.0 / 3.0,
    FAMILY_HIST_GRADIENT_BOOSTING: 1.0 / 3.0,
}


_VALID_PARAMS_BY_FAMILY = {
    FAMILY_LOGISTIC_REGRESSION: {
        "C": 1.0,
        "weighting": WEIGHTING_NONE,
        "solver": "lbfgs",
        "max_iter": 2000,
    },
    FAMILY_RANDOM_FOREST: {
        "n_estimators": 100,
        "max_depth": 4,
        "min_samples_leaf": 5,
        "weighting": WEIGHTING_NONE,
        "random_state": 42,
        "n_jobs": 1,
    },
    FAMILY_HIST_GRADIENT_BOOSTING: {
        "learning_rate": 0.1,
        "max_iter": 100,
        "max_leaf_nodes": 15,
        "l2_regularization": 0.0,
        "weighting": WEIGHTING_NONE,
        "max_depth": None,
        "early_stopping": False,
        "random_state": 42,
    },
}


def _single_frozen_config(family=FAMILY_LOGISTIC_REGRESSION) -> FrozenConfig:
    return FrozenConfig(
        family=family,
        config=ModelConfig(family, dict(_VALID_PARAMS_BY_FAMILY[family])),
        median_mcc=0.42,
        fold_mcc=[0.3, 0.4, 0.5],
        folds=[],
    )


def test_round_trip_single_family_candidate(tmp_path):
    out_dir = _write_contract(
        tmp_path,
        frozen_single_family=_single_frozen_config(),
        final_p20_train=0.31,
    )
    contract = load_frozen_config_contract(out_dir)

    assert contract.schema_version == TRANSFER_CONTRACT_SCHEMA_VERSION
    assert contract.candidate_produced is True
    assert contract.single_family is not None
    assert contract.single_family.family == FAMILY_LOGISTIC_REGRESSION
    assert contract.single_family.params == _VALID_PARAMS_BY_FAMILY[FAMILY_LOGISTIC_REGRESSION]
    assert contract.single_family.median_mcc["value"] == pytest.approx(0.42)
    assert contract.final_p20_train == pytest.approx(0.31)
    assert contract.soft_voting_bases is None
    assert contract.producer_code_identity == _CODE_VERSION
    assert contract.producer_dataset_fingerprint_ref["sha256"] == _DATASET_FINGERPRINT["sha256"]


def test_round_trip_soft_voting_candidate(tmp_path):
    bases = {
        FAMILY_LOGISTIC_REGRESSION: _single_frozen_config(FAMILY_LOGISTIC_REGRESSION),
        FAMILY_RANDOM_FOREST: _single_frozen_config(FAMILY_RANDOM_FOREST),
        FAMILY_HIST_GRADIENT_BOOSTING: _single_frozen_config(FAMILY_HIST_GRADIENT_BOOSTING),
    }
    out_dir = _write_contract(
        tmp_path,
        frozen_soft_voting_bases=bases,
        soft_voting_combination_weights=dict(_EQUAL_COMBINATION_WEIGHTS),
        final_p20_train=0.28,
        selection_result=_selection_result("soft_voting"),
    )
    contract = load_frozen_config_contract(out_dir)

    assert contract.single_family is None
    assert contract.soft_voting_bases is not None
    assert set(contract.soft_voting_bases) == {
        FAMILY_LOGISTIC_REGRESSION,
        FAMILY_RANDOM_FOREST,
        FAMILY_HIST_GRADIENT_BOOSTING,
    }
    assert contract.soft_voting_combination_weights == pytest.approx(_EQUAL_COMBINATION_WEIGHTS)
    for family, candidate in contract.soft_voting_bases.items():
        assert candidate.family == family
        assert candidate.params == _VALID_PARAMS_BY_FAMILY[family]


def test_declares_input_mode_and_depth_role(tmp_path):
    out_dir = _write_contract(
        tmp_path,
        depth_column=SENSITIVITY_DEPTH_COLUMN,
        input_mode=INPUT_MODE_SYNTHETIC,
        scientific_run=False,
        frozen_single_family=_single_frozen_config(),
        final_p20_train=0.4,
    )
    contract = load_frozen_config_contract(out_dir)

    assert contract.input_mode == INPUT_MODE_SYNTHETIC
    assert contract.scientific_run is False
    assert contract.depth_role == DEPTH_ROLE_SENSITIVITY_ONLY


def test_primary_depth_gets_primary_selection_role(tmp_path):
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    contract = load_frozen_config_contract(out_dir)
    assert contract.depth_role == DEPTH_ROLE_PRIMARY


def test_absence_of_candidate_is_preserved_explicitly(tmp_path):
    """Si A no produjo candidato, `frozen_config.json` debe reflejar esa
    ausencia explícita -- nunca fabricar una configuración congelada."""
    out_dir = _write_contract(
        tmp_path,
        frozen_single_family=None,
        frozen_soft_voting_bases=None,
        selection_result=_selection_result(None),
    )
    contract = load_frozen_config_contract(out_dir)

    assert contract.candidate_produced is False
    assert contract.single_family is None
    assert contract.soft_voting_bases is None
    assert contract.selected_family is None
    assert contract.final_p20_train is None


def test_rejects_unrecognized_schema_version(tmp_path):
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = "controlled_daily_v4_transfer_contract.v999"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractSchemaError):
        load_frozen_config_contract(out_dir)


def test_rejects_invalid_json(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "frozen_config.json").write_text("{not valid json", encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_missing_required_field(tmp_path):
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["depth_role"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_contradictory_depth_role(tmp_path):
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["depth_role"] = "not_a_real_role"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_candidate_produced_true_without_serialized_candidate(tmp_path):
    out_dir = _write_contract(tmp_path, selection_result=_selection_result(None))
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidate_produced"] = True
    payload["selected_family"] = FAMILY_LOGISTIC_REGRESSION
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_non_finite_median_mcc(tmp_path):
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["single_family"]["median_mcc"] = {"value": "not-a-number", "status": "defined"}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_synthetic_input_mode_with_scientific_run_true(tmp_path):
    """Hallazgo de revisión externa: un artefacto sintético nunca puede
    declararse `scientific_run=true` -- incoherencia de modo."""
    out_dir = _write_contract(
        tmp_path,
        input_mode=INPUT_MODE_SYNTHETIC,
        scientific_run=False,
        frozen_single_family=_single_frozen_config(),
        final_p20_train=0.4,
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["scientific_run"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_depth_role_not_matching_depth_column(tmp_path):
    """Hallazgo de revisión externa: `depth_column` de sensibilidad con
    `depth_role='primary_selection'` es una incoherencia de profundidad que
    la lectura estructural debe rechazar, usando el mecanismo existente
    (`config.depth_role_for_column`)."""
    out_dir = _write_contract(
        tmp_path,
        depth_column=SENSITIVITY_DEPTH_COLUMN,
        input_mode=INPUT_MODE_SYNTHETIC,
        scientific_run=False,
        frozen_single_family=_single_frozen_config(),
        final_p20_train=0.4,
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["depth_role"] == DEPTH_ROLE_SENSITIVITY_ONLY
    payload["depth_role"] = DEPTH_ROLE_PRIMARY
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_selected_family_not_recognized(tmp_path):
    """Hallazgo de revisión externa: `selected_family="invented"` no debe
    aceptarse."""
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["selected_family"] = "invented"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_selected_family_not_matching_single_family(tmp_path):
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["selected_family"] = FAMILY_RANDOM_FOREST
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_empty_params(tmp_path):
    """Hallazgo de revisión externa: `single_family.config.params={}` no
    debe aceptarse -- se exigen los hiperparámetros requeridos de la familia."""
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["single_family"]["config"]["params"] = {}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_family_not_matching_config_family(tmp_path):
    """Hallazgo de revisión externa: `single_family.family != config.family`
    no debe aceptarse."""
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["single_family"]["config"]["family"] = FAMILY_RANDOM_FOREST
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_soft_voting_base_key_not_matching_its_family(tmp_path):
    bases = {
        FAMILY_LOGISTIC_REGRESSION: _single_frozen_config(FAMILY_LOGISTIC_REGRESSION),
        FAMILY_RANDOM_FOREST: _single_frozen_config(FAMILY_RANDOM_FOREST),
        FAMILY_HIST_GRADIENT_BOOSTING: _single_frozen_config(FAMILY_HIST_GRADIENT_BOOSTING),
    }
    out_dir = _write_contract(
        tmp_path,
        frozen_soft_voting_bases=bases,
        final_p20_train=0.28,
        selection_result=_selection_result(FAMILY_SOFT_VOTING),
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    # La base declarada bajo la clave "random_forest" pasa a autodeclararse
    # "hist_gradient_boosting_classifier" -- incoherencia clave/familia.
    payload["soft_voting_bases"][FAMILY_RANDOM_FOREST]["family"] = FAMILY_HIST_GRADIENT_BOOSTING
    payload["soft_voting_bases"][FAMILY_RANDOM_FOREST]["config"][
        "family"
    ] = FAMILY_HIST_GRADIENT_BOOSTING
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_missing_weighting_in_params(tmp_path):
    """Los pesos normativos (`weighting`) deben reconstruirse explícitamente
    desde la configuración efectiva -- un artefacto que los omita se
    rechaza, en vez de recibir un default inventado en la lectura."""
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["single_family"]["config"]["params"]["weighting"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_empty_producer_fingerprint_reference(tmp_path):
    """Hallazgo de revisión externa: `producer.dataset_fingerprint_ref={}`
    no debe aceptarse -- se exige SHA-256 válido, versión de esquema
    soportada y metadatos requeridos."""
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["producer"]["dataset_fingerprint_ref"] = {}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_fingerprint_reference_with_unauthorized_scope(tmp_path):
    """Hallazgo de revisión externa: el `scope` de la huella debe ser
    exactamente el autorizado -- no basta con que las huellas coincidan
    entre sí sobre un `scope` arbitrario."""
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["producer"]["dataset_fingerprint_ref"]["scope"] = "stage_c_holdout_only"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def _soft_voting_bases():
    return {
        FAMILY_LOGISTIC_REGRESSION: _single_frozen_config(FAMILY_LOGISTIC_REGRESSION),
        FAMILY_RANDOM_FOREST: _single_frozen_config(FAMILY_RANDOM_FOREST),
        FAMILY_HIST_GRADIENT_BOOSTING: _single_frozen_config(FAMILY_HIST_GRADIENT_BOOSTING),
    }


def test_rejects_missing_soft_voting_combination_weights(tmp_path):
    """Hallazgo de revisión externa: los pesos de COMBINACIÓN del ensamble
    (distintos de `weighting`, balanceo de clases) son obligatorios cuando
    hay Soft Voting -- no se infiere un default al leer un artefacto
    incompleto."""
    out_dir = _write_contract(
        tmp_path,
        frozen_soft_voting_bases=_soft_voting_bases(),
        soft_voting_combination_weights=None,
        final_p20_train=0.28,
        selection_result=_selection_result("soft_voting"),
    )

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_invented_soft_voting_combination_weights(tmp_path):
    """Hallazgo de revisión externa: un peso de combinación que no coincide
    con el valor normativo (1/3 por base) se rechaza -- no cualquier
    distribución positiva es admisible."""
    out_dir = _write_contract(
        tmp_path,
        frozen_soft_voting_bases=_soft_voting_bases(),
        soft_voting_combination_weights={
            FAMILY_LOGISTIC_REGRESSION: 0.5,
            FAMILY_RANDOM_FOREST: 0.25,
            FAMILY_HIST_GRADIENT_BOOSTING: 0.25,
        },
        final_p20_train=0.28,
        selection_result=_selection_result("soft_voting"),
    )

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_rejects_soft_voting_combination_weights_without_soft_voting(tmp_path):
    """Coherencia inversa: `soft_voting_combination_weights` presente sin
    `soft_voting_bases` es una incoherencia estructural."""
    out_dir = _write_contract(
        tmp_path, frozen_single_family=_single_frozen_config(), final_p20_train=0.4
    )
    path = out_dir / "frozen_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["soft_voting_combination_weights"] = dict(_EQUAL_COMBINATION_WEIGHTS)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TransferContractValidationError):
        load_frozen_config_contract(out_dir)


def test_load_never_trains_or_selects(tmp_path):
    """Centinela textual: el lector estructural no debe importar ni invocar
    el runner de entrenamiento/selección ni la ingesta de CSV crudos."""
    import inspect

    from experiment_runner.controlled_daily_v4 import transfer_contract

    source = inspect.getsource(transfer_contract)
    for forbidden in (
        "stage_a_runner",
        "ingestion",
        "run_stage_a",
        "fit_estimator",
        "fit_candidate",
    ):
        assert forbidden not in source, forbidden
