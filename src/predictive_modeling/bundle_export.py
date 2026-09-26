"""Production writer for a single operational v2 bundle component
(`model.joblib` + `calibrator.joblib` + `contract.json` + `bundle.json`) and
for an `ensemble_manifest.json`.

This is the production counterpart of the pattern `tests/helpers/
synthetic_bundles.py` uses for fixtures: any caller building a real bundle
(an ensemble-demo executor, a future single-model exporter) uses this
module, never a test helper. File hashes are computed from the bytes
actually written to disk, after writing — the estimators passed in must
already be fitted; this module never fits, trains, or calibrates anything.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import joblib

from predictive_modeling.operational_contract import (
    ArtifactIdentity,
    HorizonContract,
    VariableMetadata,
)
from predictive_modeling.operational_preparation import TemporalCutPlan
from predictive_modeling.operational_run_artifacts import capture_environment

SUPPORTED_ENSEMBLE_FAMILIES: tuple[str, ...] = (
    "logistic_regression",
    "random_forest",
    "hist_gradient_boosting_classifier",
)


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_component_bundle(
    root: Path,
    *,
    sensor_id: str,
    horizon: int,
    model: Any,
    calibrator: Any,
    feature_columns: list[str],
    feature_names: list[str],
    lags: list[int],
    rolling_windows: list[int],
    decision_threshold: float,
    event: dict[str, Any],
    variables: list[dict[str, str]],
    contract_version: str,
    model_identity_label: str,
    calibrator_identity_label: str,
    temporal_cuts: TemporalCutPlan,
    trained_through: str,
    calibrated_through: str,
    data_snapshot_sha256: str,
) -> Path:
    """Write one real, loadable v2 bundle component at `root`.

    `model`/`calibrator` must already be fitted (and, if array-fit, already
    carry `feature_names_in_` via `bundle_packaging.attach_feature_names`
    -- this function does not call it). Never invents a threshold, a
    dataset hash, or a temporal cut: all are required, explicit inputs.
    """
    root.mkdir(parents=True, exist_ok=True)

    model_path = root / "model.joblib"
    calibrator_path = root / "calibrator.joblib"
    joblib.dump(model, model_path)
    joblib.dump(calibrator, calibrator_path)
    model_sha256 = _sha256_of(model_path)
    calibrator_sha256 = _sha256_of(calibrator_path)

    contract = HorizonContract(
        horizon_days=horizon,
        sensor_id=sensor_id,
        data_snapshot_sha256=data_snapshot_sha256,
        imputation="none_grid_gaps_preserved",
        variables=tuple(VariableMetadata(item["name"], item["unit"]) for item in variables),
        event_variable=event["variable"],
        event_threshold=event["threshold"],
        event_unit=event["unit"],
        event_comparison=event["comparison"],
        temporal_cuts=temporal_cuts,
        artifact_state="trained_bundle",
        contract_version=contract_version,
        model_identity=ArtifactIdentity(
            version=model_identity_label,
            sha256=model_sha256,
            horizon_days=horizon,
            contract_version=contract_version,
        ),
        calibrator_identity=ArtifactIdentity(
            version=calibrator_identity_label,
            sha256=calibrator_sha256,
            horizon_days=horizon,
            contract_version=contract_version,
        ),
        trained_through=date.fromisoformat(trained_through),
        calibrated_through=date.fromisoformat(calibrated_through),
    )
    contract_dict = contract.to_dict()
    contract_path = root / "contract.json"
    contract_path.write_text(json.dumps(contract_dict), encoding="utf-8")
    contract_sha256 = _sha256_of(contract_path)

    bundle = {
        "format_version": 1,
        "contract": contract_dict,
        "feature_columns": list(feature_columns),
        "feature_names": list(feature_names),
        "lags": list(lags),
        "rolling_windows": list(rolling_windows),
        "decision_threshold": decision_threshold,
        "environment": capture_environment(),
        "files": {
            "model.joblib": model_sha256,
            "calibrator.joblib": calibrator_sha256,
            "contract.json": contract_sha256,
        },
    }
    (root / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    return root


def write_ensemble_manifest(
    root: Path,
    *,
    sensor_id: str,
    horizon: int,
    contract_version: str,
    policy_version: str = "ensemble_agreement_v1",
    families: tuple[str, ...] = SUPPORTED_ENSEMBLE_FAMILIES,
) -> Path:
    """Write `ensemble_manifest.json` for `predictive_modeling.ensemble_bundle`
    to load. Weights are always exactly uniform for `ensemble_agreement_v1` --
    never renormalized, never computed here."""
    manifest = {
        "format_version": 1,
        "mode": "ensemble",
        "policy_version": policy_version,
        "sensor_id": sensor_id,
        "horizon_days": horizon,
        "contract_version": contract_version,
        "families": list(families),
        "weights": {family: 1 / len(families) for family in families},
    }
    root.mkdir(parents=True, exist_ok=True)
    path = root / "ensemble_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path
