import hashlib
import json
from pathlib import Path

import pytest

from historical_replay.admission_policy import ADMITTED_CANDIDATES, AdmissionPolicyError
from historical_replay.package_loader import (
    IntegrityError,
    InventoryError,
    ParentChildInconsistencyError,
    PredictionBeforeCutoffError,
    ProvenanceError,
    TemporalConcordanceError,
    TrainingDatesError,
    TrainingMaturityError,
    UnsupportedManifestVersionError,
    load_package,
)

REAL_ADMITTED = ADMITTED_CANDIDATES[0]
# Copia del dataset real (git-tracked, ~21KB, dato agronómico ya autorizado,
# no un artefacto de test sintético) — la política de admisión exige el hash
# exacto de este contenido; un dataset sintético no podría pasarla nunca.
REAL_DATASET_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "melchor_romero_2024_consolidado.parquet"
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


DEFAULT_CANDIDATE = {
    "experiment_id": REAL_ADMITTED.experiment_id,
    "run_id_child": REAL_ADMITTED.run_id_child,
    "run_id_parent": REAL_ADMITTED.run_id_parent,
    "config_name": REAL_ADMITTED.config_name,
    "seed": REAL_ADMITTED.seed,
}


def _write_fixture_package(
    tmp_path,
    *,
    tamper_predictions=False,
    break_dataset_hash=False,
    training_dates=None,
    split_date="2024-10-19",
    predictions_rows=None,
    schema_version="historical_replay_package_v2",
    candidate_overrides=None,
    run_metadata_overrides=None,
    manifest_overrides=None,
    omit_file_from_inventory=None,
    missing_historical_hash=False,
    mismatched_dataset_file=False,
):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "dataset").mkdir()

    candidate = dict(DEFAULT_CANDIDATE)
    if candidate_overrides:
        candidate.update(candidate_overrides)

    if predictions_rows is None:
        predictions_rows = [
            {
                "timestamp": "2024-10-19T00:00:00.000",
                "target_timestamp": "2024-10-22T00:00:00.000",
                "target_observed": True,
                "y_true": 1.0,
                "y_proba": 0.44,
                "y_pred": 0,
                "persistence": 1,
                "majority_class": 0,
                "always_stress": 1,
            }
        ]
    predictions_path = package_dir / "predictions.json"
    predictions_path.write_text(json.dumps({"rows": predictions_rows}), encoding="utf-8")

    effective_config = {
        "seed": candidate["seed"],
        "training_dates": (
            training_dates if training_dates is not None else ["2024-10-15T00:00:00.000"]
        ),
        "contract": {"horizon_days": 3, "alert_threshold": 0.5, "percentile": 20.0},
    }
    effective_config_path = package_dir / "effective_configuration.json"
    effective_config_path.write_text(json.dumps(effective_config), encoding="utf-8")

    dataset_path = package_dir / "dataset" / "melchor_romero_2024_consolidado.parquet"
    dataset_bytes = REAL_DATASET_PATH.read_bytes()
    if mismatched_dataset_file:
        # Copia con un byte de más: propia y autoconsistente (su propio
        # hash de custodia coincidirá con el "historical_sha256" que este
        # manifiesto declare para ella), pero deliberadamente distinta del
        # dataset real — para aislar la comprobación contra
        # run_metadata.json (que sigue declarando el hash real) de la
        # comprobación de custodia (que aquí sí coincide consigo misma).
        dataset_bytes = dataset_bytes + b"\x00"
    dataset_path.write_bytes(dataset_bytes)
    dataset_custody = _sha256(dataset_path)
    if not mismatched_dataset_file:
        assert dataset_custody == REAL_ADMITTED.dataset_sha256  # guarda contra desincronización

    run_metadata = {
        "child": {
            "run_id": candidate["run_id_child"],
            "experiment_id": candidate["experiment_id"],
            "status": "FINISHED",
            "run_name": "base-seed4",
            "tags": {"mlflow.parentRunId": candidate["run_id_parent"]},
            "params": {"config_name": candidate["config_name"], "seed": str(candidate["seed"])},
        },
        "parent": {
            "run_id": candidate["run_id_parent"],
            "experiment_id": candidate["experiment_id"],
            "status": "FINISHED",
            "run_name": "base",
            "params": {
                "commit_sha": REAL_ADMITTED.commit_sha,
                "dataset_sha256": REAL_ADMITTED.dataset_sha256,
                "split_date": split_date,
                "horizon_days": "3",
            },
        },
    }
    if run_metadata_overrides:
        for section, overrides in run_metadata_overrides.items():
            for key, value in overrides.items():
                existing = run_metadata[section].get(key)
                if isinstance(existing, dict) and isinstance(value, dict):
                    existing.update(value)
                else:
                    run_metadata[section][key] = value
    run_metadata_path = package_dir / "run_metadata.json"
    run_metadata_path.write_text(json.dumps(run_metadata), encoding="utf-8")

    # Hashes de custodia se calculan sobre el contenido "bueno" antes de
    # cualquier alteración deliberada, para que la alteración sea detectable
    # por mismatch de hash (y no, por accidente, por otro motivo).
    files = {
        "predictions.json": _sha256(predictions_path),
        "effective_configuration.json": _sha256(effective_config_path),
        "run_metadata.json": _sha256(run_metadata_path),
        "dataset/melchor_romero_2024_consolidado.parquet": dataset_custody,
    }
    if omit_file_from_inventory:
        files.pop(omit_file_from_inventory, None)

    if tamper_predictions:
        predictions_path.write_text(
            json.dumps({"rows": predictions_rows + [{"tampered": True}]}), encoding="utf-8"
        )

    dataset_historical_sha256 = (
        None if missing_historical_hash else ("0" * 64 if break_dataset_hash else dataset_custody)
    )

    manifest = {
        "schema_version": schema_version,
        "package_id": "base-seed4-test",
        # `admission_contract` es puramente descriptivo: el lector ya no lo
        # lee para decidir admisión (ver historical_replay.admission_policy).
        "admission_contract": {
            "scope": "single_manually_verified_candidate",
            "verified_candidates": [
                {
                    "experiment_id": candidate["experiment_id"],
                    "run_id_child": candidate["run_id_child"],
                    "model_identity_verified_by": REAL_ADMITTED.model_identity_verified_by,
                }
            ],
        },
        "candidate": candidate,
        "execution_identity": {"commit_sha": REAL_ADMITTED.commit_sha},
        "dataset": {
            "name": "melchor_romero_2024_consolidado",
            "historical_sha256": dataset_historical_sha256,
            "package_relative_path": "dataset/melchor_romero_2024_consolidado.parquet",
        },
        "temporal_semantics": {"horizon_days": 3, "split_date": split_date},
        "files": {path: {"custody_sha256": digest} for path, digest in files.items()},
    }
    if manifest_overrides:
        for section, overrides in manifest_overrides.items():
            existing = manifest.get(section)
            if isinstance(existing, dict) and isinstance(overrides, dict):
                existing.update(overrides)
            else:
                manifest[section] = overrides
    (package_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return package_dir


def test_load_valid_package_succeeds(tmp_path):
    package_dir = _write_fixture_package(tmp_path)

    package = load_package(package_dir)

    assert len(package.records) == 1
    assert package.records[0].identity.run_id == "1157696b7bb941e394c5af530c762b07"
    assert len(package.dataset) == 366  # dataset real completo, no un recorte sintético
    assert package.run_metadata["parent"]["run_id"] == "6d516bb9f778450f8fbe2e5492818e57"
    # Paso 4.1 §3: la API debe poder distinguir el corte de partición
    # (split_date) de la fecha máxima de entrenamiento realmente usada —
    # expuesta aquí para que el router la derive sin volver a leer disco.
    assert package.effective_configuration["training_dates"] == ["2024-10-15T00:00:00.000"]


def test_altered_file_is_rejected_by_hash_mismatch(tmp_path):
    package_dir = _write_fixture_package(tmp_path, tamper_predictions=True)

    with pytest.raises(IntegrityError):
        load_package(package_dir)


def test_dataset_historical_hash_inconsistent_with_custody_is_rejected(tmp_path):
    package_dir = _write_fixture_package(tmp_path, break_dataset_hash=True)

    with pytest.raises(ProvenanceError):
        load_package(package_dir)


def test_missing_historical_hash_is_rejected_never_substituted(tmp_path):
    package_dir = _write_fixture_package(tmp_path, missing_historical_hash=True)

    with pytest.raises(ProvenanceError):
        load_package(package_dir)


def test_historical_hash_inconsistent_with_run_metadata_is_rejected(tmp_path):
    # El manifiesto es autoconsistente con su propia copia del dataset
    # (custodia == historical_sha256 declarado), pero ese dataset no es el
    # real: run_metadata.json (que sigue declarando el hash real, sin
    # tocar) lo detecta.
    package_dir = _write_fixture_package(tmp_path, mismatched_dataset_file=True)

    with pytest.raises(ProvenanceError):
        load_package(package_dir)


def test_unsupported_manifest_schema_version_is_rejected(tmp_path):
    package_dir = _write_fixture_package(tmp_path, schema_version="unknown_v99")

    with pytest.raises(UnsupportedManifestVersionError):
        load_package(package_dir)


def test_training_date_not_matured_before_cutoff_is_rejected(tmp_path):
    package_dir = _write_fixture_package(
        tmp_path, training_dates=["2024-10-17T00:00:00.000"], split_date="2024-10-19"
    )

    with pytest.raises(TrainingMaturityError):
        load_package(package_dir)


def test_missing_training_dates_is_rejected(tmp_path):
    package_dir = _write_fixture_package(tmp_path, training_dates=[])

    with pytest.raises(TrainingDatesError):
        load_package(package_dir)


def test_malformed_training_date_is_rejected(tmp_path):
    package_dir = _write_fixture_package(tmp_path, training_dates=["not-a-date"])

    with pytest.raises(TrainingDatesError):
        load_package(package_dir)


def test_prediction_before_cutoff_is_rejected(tmp_path):
    row = {
        "timestamp": "2024-10-18T00:00:00.000",  # antes del corte 2024-10-19
        "target_timestamp": "2024-10-21T00:00:00.000",
        "target_observed": True,
        "y_true": 1.0,
        "y_proba": 0.44,
        "y_pred": 0,
    }
    package_dir = _write_fixture_package(tmp_path, predictions_rows=[row], split_date="2024-10-19")

    with pytest.raises(PredictionBeforeCutoffError):
        load_package(package_dir)


def test_parent_child_tag_inconsistency_is_rejected(tmp_path):
    package_dir = _write_fixture_package(
        tmp_path, run_metadata_overrides={"child": {"tags": {"mlflow.parentRunId": "otro-run"}}}
    )

    with pytest.raises(ParentChildInconsistencyError):
        load_package(package_dir)


def test_parent_child_commit_inconsistency_is_rejected(tmp_path):
    # run_metadata sigue declarando el commit real (pasa la política de
    # admisión); es el resumen del propio manifiesto el que no coincide con
    # esos metadatos capturados.
    package_dir = _write_fixture_package(
        tmp_path, manifest_overrides={"execution_identity": {"commit_sha": "otro-commit"}}
    )

    with pytest.raises(ParentChildInconsistencyError):
        load_package(package_dir)


def test_non_finished_run_status_is_rejected(tmp_path):
    package_dir = _write_fixture_package(
        tmp_path, run_metadata_overrides={"parent": {"status": "RUNNING"}}
    )

    with pytest.raises(ParentChildInconsistencyError):
        load_package(package_dir)


def test_horizon_concordance_mismatch_across_documents_is_rejected(tmp_path):
    package_dir = _write_fixture_package(
        tmp_path, run_metadata_overrides={"parent": {"params": {"horizon_days": "5"}}}
    )

    with pytest.raises(TemporalConcordanceError):
        load_package(package_dir)


def test_file_consumed_but_absent_from_inventory_is_rejected(tmp_path):
    package_dir = _write_fixture_package(tmp_path, omit_file_from_inventory="run_metadata.json")

    with pytest.raises(InventoryError):
        load_package(package_dir)


def test_unknown_candidate_is_rejected_even_if_everything_agrees_internally(tmp_path):
    # El manifiesto, su propio admission_contract.verified_candidates y
    # run_metadata.json concuerdan perfectamente entre sí — pero describen
    # un run que no es el admitido por la política externa
    # (historical_replay.admission_policy). La autodeclaración interna nunca
    # basta: la admisión se decide contra esa política, no contra el
    # manifiesto que se está validando.
    package_dir = _write_fixture_package(
        tmp_path,
        candidate_overrides={"run_id_child": "otro-run-nunca-revisado"},
        run_metadata_overrides={"child": {"run_id": "otro-run-nunca-revisado"}},
    )

    with pytest.raises(AdmissionPolicyError):
        load_package(package_dir)


def test_duplicate_identity_in_predictions_is_rejected(tmp_path):
    row = {
        "timestamp": "2024-10-19T00:00:00.000",
        "target_timestamp": "2024-10-22T00:00:00.000",
        "target_observed": True,
        "y_true": 1.0,
        "y_proba": 0.44,
        "y_pred": 0,
    }
    package_dir = _write_fixture_package(tmp_path, predictions_rows=[row, dict(row)])

    from historical_replay.records import DuplicateIdentityError

    with pytest.raises(DuplicateIdentityError):
        load_package(package_dir)


def test_load_works_without_network(tmp_path, monkeypatch):
    import socket

    def _blocked(*args, **kwargs):
        raise AssertionError("load_package no debe intentar ninguna conexión de red.")

    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    package_dir = _write_fixture_package(tmp_path)
    package = load_package(package_dir)

    assert len(package.records) == 1
