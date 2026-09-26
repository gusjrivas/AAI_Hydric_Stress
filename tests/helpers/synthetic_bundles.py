"""Shared synthetic fixtures for ensemble tests — never real data, never real
v4 artifacts (none exist). Reuses the real `HorizonContract`, `ArtifactIdentity`,
`capture_environment` and file-hashing pattern already used by
`operational_run_artifacts.persist_operational_run`, so a fixture built here
satisfies the real, unmodified `load_operational_bundle` without weakening it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from predictive_modeling.operational_contract import (
    ArtifactIdentity,
    HorizonContract,
    VariableMetadata,
)
from predictive_modeling.operational_preparation import DateRange, TemporalCutPlan
from predictive_modeling.operational_run_artifacts import capture_environment

DEFAULT_FEATURE_COLUMNS = ["temperature", "relative_humidity"]
DEFAULT_EVENT = {
    "variable": "soil_moisture",
    "threshold": 0.3,
    "unit": "m3/m3",
    "comparison": "lt",
}
DEFAULT_VARIABLES = [
    {"name": "soil_moisture", "unit": "m3/m3"},
    {"name": "temperature", "unit": "degC"},
    {"name": "relative_humidity", "unit": "%"},
]

# A single set of temporal cuts satisfying TemporalCutPlan/HorizonContract's
# own validation (train < calibration < evaluation <= inference_as_of,
# all within allowed_data). trained_through/calibrated_through must land
# inside train/calibration respectively.
DEFAULT_TEMPORAL_CUTS = TemporalCutPlan(
    allowed_data=DateRange("2024-01-01", "2024-06-30"),
    train=DateRange("2024-01-01", "2024-03-31"),
    calibration=DateRange("2024-04-01", "2024-04-30"),
    evaluation=DateRange("2024-05-01", "2024-05-31"),
    inference_as_of="2024-06-30",
)
DEFAULT_TRAINED_THROUGH = "2024-03-31"
DEFAULT_CALIBRATED_THROUGH = "2024-04-30"
DEFAULT_DATA_SNAPSHOT_SHA256 = "a" * 64


@dataclass
class StubEstimator:
    """A minimal fake model/calibrator: fixed positive-class probability,
    `classes_=[0,1]`, `feature_names_in_` settable — used only to fix exact
    probability test cases (Nivel 1), never to validate v4 itself."""

    positive_probability: float
    classes_: list[int] = field(default_factory=lambda: [0, 1])
    feature_names_in_: np.ndarray | None = None

    def predict_proba(self, X):
        n = len(X)
        return np.array([[1 - self.positive_probability, self.positive_probability]] * n)


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_single_bundle(
    root: Path,
    *,
    sensor_id: str,
    horizon: int,
    model: Any,
    calibrator: Any,
    feature_columns: list[str] | None = None,
    decision_threshold: float = 0.5,
    event: dict | None = None,
    variables: list[dict] | None = None,
    contract_version: str = "producer_daily_h123_v1",
    model_identity_label: str,
    calibrator_identity_label: str,
    temporal_cuts: TemporalCutPlan | None = None,
    trained_through: str = DEFAULT_TRAINED_THROUGH,
    calibrated_through: str = DEFAULT_CALIBRATED_THROUGH,
    data_snapshot_sha256: str = DEFAULT_DATA_SNAPSHOT_SHA256,
    feature_names: list[str] | None = None,
    lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
) -> Path:
    """Writes a real, loadable v2 bundle (model.joblib, calibrator.joblib,
    contract.json, bundle.json) at `root`. File hashes in `bundle.json` are
    computed from the bytes actually written to disk, after writing —
    mirroring `persist_operational_run`'s own order."""
    root.mkdir(parents=True, exist_ok=True)
    feature_columns = feature_columns or DEFAULT_FEATURE_COLUMNS
    event = event or DEFAULT_EVENT
    variables = variables or DEFAULT_VARIABLES
    temporal_cuts = temporal_cuts or DEFAULT_TEMPORAL_CUTS

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
        "feature_names": (
            list(feature_names) if feature_names is not None else list(feature_columns)
        ),
        "lags": list(lags) if lags is not None else [],
        "rolling_windows": list(rolling_windows) if rolling_windows is not None else [],
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
    root: Path, *, sensor_id: str, horizon: int, contract_version: str = "producer_daily_h123_v1"
) -> Path:
    manifest = {
        "format_version": 1,
        "mode": "ensemble",
        "policy_version": "ensemble_agreement_v1",
        "sensor_id": sensor_id,
        "horizon_days": horizon,
        "contract_version": contract_version,
        "families": [
            "logistic_regression",
            "random_forest",
            "hist_gradient_boosting_classifier",
        ],
        "weights": {
            "logistic_regression": 1 / 3,
            "random_forest": 1 / 3,
            "hist_gradient_boosting_classifier": 1 / 3,
        },
    }
    root.mkdir(parents=True, exist_ok=True)
    path = root / "ensemble_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path
