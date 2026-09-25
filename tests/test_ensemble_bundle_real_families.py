"""Nivel 2: the three real v4 families, genuinely fit and calibrated on
synthetic data -- never a `StubEstimator` double (those are reserved for
exact-probability cases in `tests/test_ensemble_bundle.py`).

Reuses, unmodified: `experiment_runner.controlled_daily_v4.models.fit_estimator`
(frozen protocol; fits on `ndarray`, never a DataFrame) and the same
`CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")` pattern
already used by `predictive_modeling.operational_run.fit_seed`, on a
calibration partition disjoint from training. `attach_feature_names` is the
only packaging-time addition, applied after fitting, and this test asserts
it does not change predicted probabilities.

Never reads real data; never opens a holdout; never touches
`controlled_daily_v3`/`historical_replay`/`replay_packages/`.
"""

from __future__ import annotations

import hashlib
from datetime import date

import numpy as np
import pandas as pd
import pytest
from sklearn.calibration import CalibratedClassifierCV, FrozenEstimator

from experiment_runner.controlled_daily_v4.models import fit_estimator
from predictive_modeling.bundle_packaging import attach_feature_names
from predictive_modeling.ensemble_bundle import load_ensemble_bundle, predict_ensemble_bundle
from predictive_modeling.operational_preparation import (
    TARGET_LABEL_COLUMN,
    add_multihorizon_targets,
    partition_labeled_horizon,
)
from predictive_modeling.operational_run import (
    DEFAULT_LAGS,
    DEFAULT_ROLLING_WINDOWS,
    build_feature_frame,
    resolve_cut_plan,
    resolve_feature_columns,
    resolve_frozen_threshold,
)
from tests.helpers.synthetic_bundles import write_ensemble_manifest, write_single_bundle

N_DAYS = 240
TRAIN_END = date(2024, 5, 19)
CALIBRATION_START = date(2024, 5, 20)
CALIBRATION_END = date(2024, 6, 28)
EVALUATION_START = date(2024, 6, 29)
EVALUATION_END = date(2024, 8, 27)
HORIZON = 1

FAMILY_PARAMS = {
    "logistic_regression": {"C": 1.0},
    "random_forest": {"n_estimators": 10, "max_depth": 4, "min_samples_leaf": 5},
    "hist_gradient_boosting_classifier": {
        "learning_rate": 0.1,
        "max_iter": 10,
        "max_leaf_nodes": 15,
        "l2_regularization": 0.0,
    },
}


def _synthetic_frame() -> pd.DataFrame:
    rng = np.random.default_rng(20260925)
    dates = pd.date_range("2024-01-01", periods=N_DAYS, freq="D")
    day = np.arange(N_DAYS)
    soil_moisture = 0.5 + 0.25 * np.sin(2 * np.pi * day / 45) + rng.normal(0, 0.03, N_DAYS)
    temperature = 20 + 8 * np.sin(2 * np.pi * day / 90 + 1.0) + rng.normal(0, 1.0, N_DAYS)
    relative_humidity = 60 + 15 * np.cos(2 * np.pi * day / 30) + rng.normal(0, 2.0, N_DAYS)
    return pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": np.clip(soil_moisture, 0.05, 0.95),
            "temperature": temperature,
            "relative_humidity": relative_humidity,
        }
    )


def _manifest(dataset_sha256: str) -> dict:
    return {
        "dataset": {
            "sha256": dataset_sha256,
            "allowed_dates": {"start": "2024-01-01", "end": EVALUATION_END.isoformat()},
            "variables": [
                {"name": "soil_moisture", "role": "event_variable"},
                {"name": "temperature", "role": "feature"},
                {"name": "relative_humidity", "role": "feature"},
            ],
        },
        "event": {
            "variable": "soil_moisture",
            "percentile": 20.0,
            "threshold_reference": {"start": "2024-01-01", "end": TRAIN_END.isoformat()},
        },
        "partitions": {
            "train": {"start": "2024-01-01", "end": TRAIN_END.isoformat()},
            "calibration": {
                "start": CALIBRATION_START.isoformat(),
                "end": CALIBRATION_END.isoformat(),
            },
            "evaluation": {
                "start": EVALUATION_START.isoformat(),
                "end": EVALUATION_END.isoformat(),
            },
        },
    }


@pytest.fixture(scope="module")
def fitted_partitions():
    """Fit+calibrate the three real v4 families once for the whole module:
    shared across the "serialization round trip" and "packaging does not
    change probabilities" tests, since they only read this fixture."""
    df = _synthetic_frame()
    dataset_sha256 = hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()
    manifest = _manifest(dataset_sha256)

    feature_columns = resolve_feature_columns(manifest)
    cuts = resolve_cut_plan(manifest)
    threshold = resolve_frozen_threshold(df, manifest, event_variable="soil_moisture")
    feature_frame, feature_names = build_feature_frame(
        df, feature_columns, lags=DEFAULT_LAGS, windows=DEFAULT_ROLLING_WINDOWS
    )
    labeled_by_horizon = add_multihorizon_targets(
        feature_frame, column="soil_moisture", thresholds={1: threshold, 2: threshold, 3: threshold}
    )
    prepared = partition_labeled_horizon(
        labeled_by_horizon[HORIZON], cuts=cuts, required_inference_columns=feature_names
    )

    # `partition_labeled_horizon`'s supervised partitions only guarantee an
    # observed target, not fully-populated lag/rolling features: the first
    # max(lag, window) days of `allowed_data` still carry NaN features. Drop
    # those rows here (test-only hygiene, not a change to production code).
    train_rows = prepared.train.dropna(subset=list(feature_names))
    calibration_rows = prepared.calibration.dropna(subset=list(feature_names))

    X_train = train_rows[list(feature_names)].to_numpy()
    y_train = train_rows[TARGET_LABEL_COLUMN].astype(int).to_numpy()
    X_calib = calibration_rows[list(feature_names)].to_numpy()
    y_calib = calibration_rows[TARGET_LABEL_COLUMN].astype(int).to_numpy()

    fitted = {}
    for family, params in FAMILY_PARAMS.items():
        # `fit_estimator` is `controlled_daily_v4`'s own frozen fitting
        # protocol, called unmodified with a plain ndarray -- never a
        # DataFrame -- so the fitted estimator has no `feature_names_in_`.
        model = fit_estimator(family, params, X_train, y_train)
        assert not hasattr(model, "feature_names_in_")

        calibrator = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
        calibrator.fit(X_calib, y_calib)
        assert not hasattr(calibrator, "feature_names_in_")

        fitted[family] = {"model": model, "calibrator": calibrator}

    return {
        "df": df,
        "dataset_sha256": dataset_sha256,
        "feature_columns": feature_columns,
        "feature_names": feature_names,
        "fitted": fitted,
        "X_train": X_train,
    }


def test_attach_feature_names_does_not_change_probabilities_for_the_real_families(fitted_partitions):
    feature_names = fitted_partitions["feature_names"]
    X_train = fitted_partitions["X_train"]
    sample = X_train[:5]
    sample_frame = pd.DataFrame(sample, columns=list(feature_names))

    for family, components in fitted_partitions["fitted"].items():
        for role in ("model", "calibrator"):
            estimator = components[role]
            before = estimator.predict_proba(sample)
            attach_feature_names(estimator, list(feature_names))
            after = estimator.predict_proba(sample_frame)
            assert np.array_equal(before, after), f"{family}.{role} probabilities changed after packaging"
            assert list(estimator.feature_names_in_) == list(feature_names)


def test_three_real_families_serialize_load_and_infer_through_the_real_bundle(tmp_path, fitted_partitions):
    root = tmp_path / "bundles"
    sensor_id = "synthetic-sensor"
    feature_columns = fitted_partitions["feature_columns"]
    feature_names = fitted_partitions["feature_names"]

    for family, components in fitted_partitions["fitted"].items():
        write_single_bundle(
            root / sensor_id / f"horizon_{HORIZON}" / "ensemble" / family,
            sensor_id=sensor_id,
            horizon=HORIZON,
            model=components["model"],
            calibrator=components["calibrator"],
            model_identity_label=f"{family}_model_v4",
            calibrator_identity_label=f"{family}_calibrator_v4",
            feature_columns=list(feature_columns),
            feature_names=list(feature_names),
            lags=list(DEFAULT_LAGS),
            rolling_windows=list(DEFAULT_ROLLING_WINDOWS),
            event={"variable": "soil_moisture", "threshold": 0.3, "unit": "m3/m3", "comparison": "lt"},
            variables=[
                {"name": "soil_moisture", "unit": "m3/m3"},
                {"name": "temperature", "unit": "degC"},
                {"name": "relative_humidity", "unit": "%"},
            ],
            temporal_cuts=resolve_cut_plan(_manifest(fitted_partitions["dataset_sha256"])),
            trained_through=TRAIN_END.isoformat(),
            calibrated_through=CALIBRATION_END.isoformat(),
            data_snapshot_sha256=fitted_partitions["dataset_sha256"],
        )
    write_ensemble_manifest(root / sensor_id / f"horizon_{HORIZON}", sensor_id=sensor_id, horizon=HORIZON)

    ensemble = load_ensemble_bundle(root, sensor_id=sensor_id, horizon=HORIZON)
    assert set(ensemble.components) == set(FAMILY_PARAMS)

    as_of_date = date(2024, 7, 15)  # inside evaluation, after calibrated_through
    result = predict_ensemble_bundle(
        ensemble,
        fitted_partitions["df"],
        sensor_id=sensor_id,
        units={"soil_moisture": "m3/m3", "temperature": "degC", "relative_humidity": "%"},
        as_of_date=as_of_date,
    )

    assert result["policy_version"] == "ensemble_agreement_v1"
    assert 0.0 <= result["combined_probability"] <= 1.0
    assert result["combined_alert"] == (result["combined_probability"] >= result["decision_threshold"])
    assert result["positive_votes"] in (0, 1, 2, 3)
    for component in result["components"]:
        # A genuine inference per real, distinct family, not three copies of
        # the same fit renamed.
        assert 0.0 <= component["score"] <= 1.0
    scores = {c["family"]: c["score"] for c in result["components"]}
    assert len(set(scores.values())) > 1, "the three real families produced identical scores"
