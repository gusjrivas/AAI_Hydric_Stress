"""Recuperación de solo lectura de una corrida finalizada de la Etapa C
(`artifacts.verify_stage_c_recovery`) -- revisión dirigida, hallazgo 2:
'un ledger finalizado que referencia un directorio inexistente devuelve
exit 0'.

Nunca lee datos reales de Pergamino/holdout: construye artefactos reales de
C sobre la serie sintética ya usada por `test_controlled_daily_v4_stage_c_runner.py`,
vía `write_stage_c_artifacts`, y ejercita `verify_stage_c_recovery`
directamente (sin CLI ni ledger) para aislar el mecanismo de integridad."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4 import artifacts
from experiment_runner.controlled_daily_v4.config import (
    DEPTH_ROLE_PRIMARY,
    FAMILY_LOGISTIC_REGRESSION,
    PRIMARY_DEPTH_COLUMN,
    WEIGHTING_NONE,
)
from experiment_runner.controlled_daily_v4.stage_c_runner import run_stage_c
from experiment_runner.controlled_daily_v4.transfer_contract import (
    FrozenCandidate,
    FrozenConfigContract,
)

REDUCED_BOOTSTRAP_REPLICAS = 20
_HOLDOUT_KEY = "deadbeef" * 8
_ATTEMPT_ID = "attempt-1"


def _daily_series(n_days=4018, seed=101):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-01-01", periods=n_days, freq="D")
    seasonal = np.sin(np.linspace(0, 2 * np.pi * (n_days / 365.25), n_days))
    soil_0_7 = np.clip(0.35 + 0.08 * seasonal + rng.normal(0, 0.05, n_days), 0.05, 0.65)
    rh2m = np.clip(70 + 15 * seasonal + rng.normal(0, 5, n_days), 10, 100)
    radiation = np.clip(18 + 8 * np.sin(seasonal + 1) + rng.normal(0, 3, n_days), 0, 35)
    return pd.DataFrame(
        {PRIMARY_DEPTH_COLUMN: soil_0_7, "RH2M": rh2m, "ALLSKY_SFC_SW_DWN": radiation},
        index=dates,
    )


def _contract():
    candidate = FrozenCandidate(
        family=FAMILY_LOGISTIC_REGRESSION,
        params={"C": 1.0, "weighting": WEIGHTING_NONE, "solver": "lbfgs", "max_iter": 200},
        median_mcc={"value": 0.3, "status": "defined"},
        fold_mcc=[],
    )
    return FrozenConfigContract(
        schema_version="controlled_daily_v4_transfer_contract.v1",
        input_mode="synthetic",
        scientific_run=False,
        depth_column=PRIMARY_DEPTH_COLUMN,
        depth_role=DEPTH_ROLE_PRIMARY,
        candidate_produced=True,
        selected_family=FAMILY_LOGISTIC_REGRESSION,
        single_family=candidate,
        soft_voting_bases=None,
        soft_voting_combination_weights=None,
        final_p20_train=None,
        final_estimator_details={},
        producer_code_identity={},
        producer_dataset_fingerprint_ref={},
        raw={},
    )


def _write_real_stage_c_artifacts(output_dir, *, holdout_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID):
    daily_series = _daily_series()
    contract = _contract()
    result = run_stage_c(contract, daily_series, bootstrap_replicas=REDUCED_BOOTSTRAP_REPLICAS)
    return artifacts.write_stage_c_artifacts(
        output_dir,
        input_mode="synthetic",
        scientific_run=False,
        resolved_config={"stage": "C"},
        producer_dir=output_dir.parent / "producer_a_unused",
        producer_contract_raw={},
        stage_b_dir=output_dir.parent / "stage_b_unused",
        stage_b_decision_raw={"verdict": "CANDIDATE_VALIDATED"},
        ledger_path=output_dir.parent / "ledger_unused.sqlite3",
        holdout_identity_key=holdout_key,
        attempt_id=attempt_id,
        authorized_by="tester",
        consumer_code_identity={"available": False, "source": "unavailable", "commit": None},
        consumer_environment_info={},
        consumer_environment_issues=[],
        result=result,
    )


def test_integrity_manifest_is_written_as_last_artifact(tmp_path):
    output_dir = tmp_path / "stage_c_out"
    written = _write_real_stage_c_artifacts(output_dir)
    assert "integrity_manifest" in written
    manifest = json.loads(written["integrity_manifest"].read_text(encoding="utf-8"))
    assert manifest["holdout_identity_key"] == _HOLDOUT_KEY
    assert manifest["attempt_id"] == _ATTEMPT_ID
    assert manifest["result_reference"] == str(output_dir.resolve())
    # El propio manifiesto nunca se referencia a sí mismo.
    assert "integrity_manifest.json" not in manifest["files"]
    assert "outcome.json" in manifest["files"]


def test_valid_recovery_succeeds_without_retraining(tmp_path):
    output_dir = tmp_path / "stage_c_out"
    _write_real_stage_c_artifacts(output_dir)
    artifacts.verify_stage_c_recovery(
        output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
    )  # no debe lanzar


def test_recovery_rejects_missing_directory(tmp_path):
    missing_dir = tmp_path / "never_written"
    with pytest.raises(artifacts.StageCRecoveryError):
        artifacts.verify_stage_c_recovery(
            missing_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )


def test_recovery_rejects_missing_required_artifact(tmp_path):
    output_dir = tmp_path / "stage_c_out"
    _write_real_stage_c_artifacts(output_dir)
    (output_dir / "outcome.json").unlink()
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )
    assert any("outcome.json" in reason for reason in exc.value.reasons)


def test_recovery_rejects_altered_content(tmp_path):
    output_dir = tmp_path / "stage_c_out"
    _write_real_stage_c_artifacts(output_dir)
    (output_dir / "outcome.json").write_text(
        json.dumps({"predictions_available": True, "reasons": [], "tampered": True}),
        encoding="utf-8",
    )
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )
    assert any("sha256" in reason for reason in exc.value.reasons)


def test_recovery_rejects_result_from_a_different_attempt(tmp_path):
    """Un manifiesto íntegro pero de OTRO intento (u OTRO holdout) nunca se
    presenta como recuperación válida del intento/holdout consultado."""
    output_dir = tmp_path / "stage_c_out"
    _write_real_stage_c_artifacts(output_dir, attempt_id="attempt-original")
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id="attempt-impostor"
        )
    assert any("attempt_id" in reason for reason in exc.value.reasons)


def test_recovery_rejects_unknown_schema_version(tmp_path):
    """Revisión dirigida (hallazgo 3, segunda ronda): un `schema_version`
    desconocido en `integrity_manifest.json` nunca habilita la recuperación,
    aunque el resto del manifiesto (holdout/intento/hashes) luzca coherente."""
    output_dir = tmp_path / "stage_c_out"
    written = _write_real_stage_c_artifacts(output_dir)
    manifest = json.loads(written["integrity_manifest"].read_text(encoding="utf-8"))
    manifest["schema_version"] = "UNKNOWN_SCHEMA"
    written["integrity_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )
    assert any("schema_version" in reason for reason in exc.value.reasons)


def test_recovery_rejects_manifest_with_only_a_stray_file(tmp_path):
    """Revisión dirigida (hallazgo 3, segunda ronda): un manifiesto cuyo
    `files` contiene ÚNICAMENTE un archivo ajeno ('only.txt') nunca es
    recuperable, aunque su hash sea correcto -- falta el conjunto completo
    de artefactos obligatorios del esquema."""
    output_dir = tmp_path / "stage_c_out"
    written = _write_real_stage_c_artifacts(output_dir)
    stray = output_dir / "only.txt"
    stray.write_text("stray", encoding="utf-8")
    manifest = json.loads(written["integrity_manifest"].read_text(encoding="utf-8"))
    import hashlib

    manifest["files"] = {"only.txt": hashlib.sha256(stray.read_bytes()).hexdigest()}
    written["integrity_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )
    assert any("conjunto completo" in reason for reason in exc.value.reasons)


def test_recovery_rejects_path_escape_via_parent_reference(tmp_path):
    """Revisión dirigida (hallazgo 3, segunda ronda): una ruta declarada con
    `..` que intenta escapar de `output_dir` se rechaza sin siquiera leer el
    archivo señalado."""
    output_dir = tmp_path / "stage_c_out"
    written = _write_real_stage_c_artifacts(output_dir)
    secret = tmp_path / "outside_secret.json"
    secret.write_text(json.dumps({"leak": True}), encoding="utf-8")
    manifest = json.loads(written["integrity_manifest"].read_text(encoding="utf-8"))
    import hashlib

    manifest["files"]["../outside_secret.json"] = hashlib.sha256(secret.read_bytes()).hexdigest()
    written["integrity_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )
    assert any("confinado" in reason for reason in exc.value.reasons)


def test_recovery_rejects_absolute_path_escape(tmp_path):
    """Misma protección que el caso anterior, para una ruta ABSOLUTA en vez
    de un componente `..`."""
    output_dir = tmp_path / "stage_c_out"
    written = _write_real_stage_c_artifacts(output_dir)
    secret = tmp_path / "outside_secret.json"
    secret.write_text(json.dumps({"leak": True}), encoding="utf-8")
    manifest = json.loads(written["integrity_manifest"].read_text(encoding="utf-8"))
    import hashlib

    manifest["files"][str(secret)] = hashlib.sha256(secret.read_bytes()).hexdigest()
    written["integrity_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )
    assert any("confinado" in reason for reason in exc.value.reasons)


def test_recovery_rejects_structurally_incoherent_schema_version_artifact(tmp_path):
    """Coherencia ESTRUCTURAL (hallazgo 3, segunda ronda): si
    `schema_version.json` en disco declara un esquema distinto del que
    declara el propio `integrity_manifest.json` (aunque su sha256 siga
    coincidiendo con lo persistido en el manifiesto), la recuperación se
    rechaza."""
    output_dir = tmp_path / "stage_c_out"
    written = _write_real_stage_c_artifacts(output_dir)
    tampered = {"schema_version": "controlled_daily_v4_stage_c.v_tampered"}
    (output_dir / "schema_version.json").write_text(json.dumps(tampered), encoding="utf-8")
    import hashlib

    manifest = json.loads(written["integrity_manifest"].read_text(encoding="utf-8"))
    manifest["files"]["schema_version.json"] = hashlib.sha256(
        (output_dir / "schema_version.json").read_bytes()
    ).hexdigest()
    written["integrity_manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )
    assert any("no coincide con el schema_version" in reason for reason in exc.value.reasons)


def test_recovery_rejects_missing_manifest(tmp_path):
    """Fallo entre la escritura de artefactos y la finalización del ledger:
    si el manifiesto de integridad nunca llegó a escribirse (u otro artefacto
    esperado falta), la recuperación se rechaza -- nunca se declara éxito
    sobre evidencia incompleta."""
    output_dir = tmp_path / "stage_c_out"
    _write_real_stage_c_artifacts(output_dir)
    (output_dir / "integrity_manifest.json").unlink()
    with pytest.raises(artifacts.StageCRecoveryError) as exc:
        artifacts.verify_stage_c_recovery(
            output_dir, holdout_identity_key=_HOLDOUT_KEY, attempt_id=_ATTEMPT_ID
        )
    assert any("integrity_manifest.json" in reason for reason in exc.value.reasons)
