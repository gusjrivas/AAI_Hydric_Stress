"""Integrated synthetic-fixture test for the operational +1/+2/+3
orchestrator (`predictive_modeling.operational_run`).

Never reads `data/melchor_romero_2024_consolidado.parquet`, never opens a
holdout, and never touches `controlled_daily_v3`/`v4`: the manifest below
is explicitly marked `dataset.source_kind="synthetic"` and
`dataset.synthetic_fixture=True`, with intentionally reduced support and
bootstrap parameters (fewer replicates, smaller minimums) so the test runs
in seconds -- these values would never be usable to accredit a real
calibration claim.
"""

from __future__ import annotations

import hashlib
from datetime import date

import numpy as np
import pandas as pd
import pytest

from predictive_modeling.calibration_assessment import ASSESSMENT_INSUFFICIENT_EVIDENCE
from predictive_modeling.calibration_manifest import verify_frozen_calibration_manifest
from predictive_modeling.operational_run import (
    OperationalRunError,
    run_operational_manifest,
)

N_DAYS = 240
TRAIN_END = date(2024, 5, 19)
CALIBRATION_START = date(2024, 5, 20)
CALIBRATION_END = date(2024, 6, 28)
EVALUATION_START = date(2024, 6, 29)
EVALUATION_END = date(2024, 8, 27)
WINDOW_1_START = date(2024, 7, 29)
WINDOW_1_END = date(2024, 8, 27)


def _synthetic_frame() -> pd.DataFrame:
    rng = np.random.default_rng(20260920)
    dates = pd.date_range("2024-01-01", periods=N_DAYS, freq="D")
    day = np.arange(N_DAYS)
    soil_moisture = 0.5 + 0.25 * np.sin(2 * np.pi * day / 45) + rng.normal(0, 0.03, N_DAYS)
    temperature = 20 + 8 * np.sin(2 * np.pi * day / 90 + 1.0) + rng.normal(0, 1.0, N_DAYS)
    relative_humidity = 60 + 15 * np.cos(2 * np.pi * day / 30) + rng.normal(0, 2.0, N_DAYS)
    precipitation = np.clip(rng.gamma(1.5, 2.0, N_DAYS) - 1.5, 0, None)
    solar_radiation = 18 + 6 * np.sin(2 * np.pi * day / 120 + 0.5) + rng.normal(0, 1.0, N_DAYS)
    wind_speed = 3 + 1.5 * np.cos(2 * np.pi * day / 20) + rng.normal(0, 0.3, N_DAYS)
    return pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": np.clip(soil_moisture, 0.05, 0.95),
            "temperature": temperature,
            "relative_humidity": relative_humidity,
            "precipitation": precipitation,
            "solar_radiation": solar_radiation,
            "wind_speed": wind_speed,
        }
    )


def _dataset_sha256(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def _synthetic_ready_manifest(dataset_sha256: str) -> dict:
    return {
        "schema_version": "producer_calibration_plan_v1",
        "contract_version": "producer_daily_h123_v1",
        "status": "ready_for_fit",
        "frozen_at": "2026-09-20T00:00:00Z",
        "calendar_timezone": "UTC",
        "horizons": [1, 2, 3],
        "dataset": {
            "dataset_id": "synthetic-operational-run-fixture",
            "sha256": dataset_sha256,
            "source_kind": "synthetic",
            "synthetic_fixture": True,
            "site": "synthetic-site",
            "sensor_id": "synthetic-sensor",
            "population": "synthetic daily fixture; integration test only",
            "provenance": "generated deterministically inside the test (np.random.default_rng)",
            "prior_exposure": "synthetic fixture; no real assessment claim",
            "allowed_dates": {"start": "2024-01-01", "end": EVALUATION_END.isoformat()},
            "variables": [
                {"name": "soil_moisture", "role": "event_variable", "unit": "m3/m3"},
                {"name": "temperature", "role": "feature", "unit": "degC"},
                {"name": "relative_humidity", "role": "feature", "unit": "%"},
                {"name": "precipitation", "role": "feature", "unit": "mm/day"},
                {"name": "solar_radiation", "role": "feature", "unit": "MJ/m2/day"},
                {"name": "wind_speed", "role": "feature", "unit": "m/s"},
            ],
        },
        "intended_use": "exercise the operational orchestrator only; not a real calibration plan",
        "event": {
            "variable": "soil_moisture",
            "unit": "m3/m3",
            "comparison": "lt",
            "percentile": 20.0,
            "threshold_source": "training_observations_only",
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
        "model_plan": {
            "family": "random_forest",
            "hyperparameters": {
                "n_estimators": 20,
                "max_depth": 4,
                "min_samples_leaf": 2,
                "min_samples_split": 2,
                "max_features": "sqrt",
                "bootstrap": True,
                "criterion": "gini",
            },
        },
        "training_seeds": [0, 1, 2, 3, 4],
        "deployment_seed": 0,
        "calibration": {"method": "sigmoid"},
        "probability_bins": {
            "strategy": "equal_width",
            "count": 10,
            "include_one_in_last": True,
        },
        "support": {
            "minimum_bin_count": 2,
            "minimum_class_count": 3,
            "minimum_temporal_blocks": 2,
            "justification": "reduced synthetic-fixture floor; never used for a real assessment",
        },
        "coverage": {"minimum": 0.5},
        "tolerances": {
            "epsilon_ece": 0.4,
            "epsilon_bin": 0.4,
            "justification": "wide synthetic-fixture tolerance; exercises wiring, not a real gate",
        },
        "stability_windows": [
            {
                "start": WINDOW_1_START.isoformat(),
                "end": WINDOW_1_END.isoformat(),
                "criteria_reference": "global",
            }
        ],
        "uncertainty": {
            "method": "synthetic-fixture moving-block bootstrap",
            "block_length_days": 3,
            "gap_treatment": "preserve synthetic calendar positions",
            "replicates": 30,
            "resampling_seed": 11,
            "nominal_level": 0.95,
        },
        "multiplicity": {
            "method": "synthetic simultaneous-upper-bound fixture",
            "family_dimensions": [
                "horizon",
                "seed",
                "stability_window",
                "supported_probability_bin",
            ],
        },
        "log_loss": {"clipping_epsilon": 0.001},
    }


@pytest.fixture(scope="module")
def frozen_manifest(tmp_path_factory: pytest.TempPathFactory) -> dict:
    df = _synthetic_frame()
    manifest = _synthetic_ready_manifest(_dataset_sha256(df))
    # Not calling `freeze_calibration_manifest`/`verify_frozen_calibration_manifest`
    # would skip the exact identity check the real CLI performs; exercise it
    # here too, against a throwaway tmp_path copy, never the real config file.
    from predictive_modeling.calibration_manifest import freeze_calibration_manifest

    directory = tmp_path_factory.mktemp("operational-run-fixture")
    manifest_path = directory / "manifest.json"
    freeze_calibration_manifest(manifest, manifest_path)
    return verify_frozen_calibration_manifest(manifest_path)


def test_operational_run_evaluates_all_three_horizons_end_to_end(frozen_manifest):
    df = _synthetic_frame()
    dataset_sha256 = _dataset_sha256(df)

    result = run_operational_manifest(frozen_manifest, df, dataset_sha256=dataset_sha256)

    assert result.dataset_sha256 == dataset_sha256
    assert result.event_variable == "soil_moisture"
    assert result.feature_columns == (
        "temperature",
        "relative_humidity",
        "precipitation",
        "solar_radiation",
        "wind_speed",
    )
    assert set(result.periods) == {"full", "window_1"}
    assert result.bootstrap_result is not None
    assert result.contract_family_valid is True
    assert len(result.horizons) == 3

    for horizon_result in result.horizons:
        assert horizon_result.status == "evaluated"
        assert horizon_result.reason is None
        assert len(horizon_result.seed_fits) == 5
        for seed_fit in horizon_result.seed_fits:
            assert seed_fit.training_rows > 0
            assert seed_fit.calibration_rows > 0
            assert seed_fit.evaluation_rows > 0
            for probability in seed_fit.calibrated_by_target_date.values():
                assert 0.0 <= probability <= 1.0
            for probability in seed_fit.raw_by_target_date.values():
                assert 0.0 <= probability <= 1.0
        assert horizon_result.assessment is not None
        assert horizon_result.assessment.assessment_result in (
            "passed",
            "failed",
            ASSESSMENT_INSUFFICIENT_EVIDENCE,
        )
        assert horizon_result.final_decision is not None
        assert horizon_result.final_decision.final_result in (
            "passed",
            "failed",
            ASSESSMENT_INSUFFICIENT_EVIDENCE,
        )
        assert horizon_result.baseline_comparisons  # at least one (seed, period) evaluated
        assert horizon_result.contract is not None
        assert horizon_result.contract.artifact_state == "trained_bundle"
        assert horizon_result.contract.model_identity is not None
        assert horizon_result.contract.calibrator_identity is not None

    # Each horizon must have its own, independent model/calibrator identity
    # (operational_contract.validate_horizon_contract_family already enforces
    # this; assert it explicitly here too as a regression guard).
    model_hashes = {hr.contract.model_identity.sha256 for hr in result.horizons}
    assert len(model_hashes) == 3

    # Same frozen threshold is reused numerically for h=1, h=2 and h=3
    # (design.md: "de modo que sean numericamente iguales").
    thresholds = {hr.threshold for hr in result.horizons}
    assert thresholds == {result.threshold}


def test_operational_run_rejects_a_dataset_sha256_mismatch(frozen_manifest):
    df = _synthetic_frame()
    with pytest.raises(OperationalRunError, match="dataset_sha256"):
        run_operational_manifest(frozen_manifest, df, dataset_sha256="0" * 64)


def test_operational_run_rejects_an_unsupported_model_family(frozen_manifest):
    df = _synthetic_frame()
    dataset_sha256 = _dataset_sha256(df)
    tampered = dict(frozen_manifest)
    tampered["model_plan"] = {**frozen_manifest["model_plan"], "family": "gradient_boosting"}
    with pytest.raises(OperationalRunError, match="model_plan.family"):
        run_operational_manifest(tampered, df, dataset_sha256=dataset_sha256)


def test_operational_run_isolates_a_single_horizon_training_failure(frozen_manifest, monkeypatch):
    """design.md: 'Falla de un horizonte no inventa su valor ni invalida los
    otros.' `partitions.train`, el umbral y `partitions.evaluation` son
    compartidos por los tres horizontes (misma `threshold_reference` para
    los tres), asi que no existe una corrupcion de datos que rompa el
    ajuste de un horizonte sin romper los otros dos a la vez. Para probar
    el aislamiento de todas formas, se fuerza una excepcion de
    entrenamiento (equivalente a la que produce scikit-learn con una sola
    clase) unicamente en la primera llamada de semilla del horizonte 2
    (`manifest["horizons"] == [1, 2, 3]`, procesados en ese orden, 5
    semillas cada uno; el orquestador corta ese horizonte ante la primera
    semilla fallida, sin intentar las 4 restantes) y se verifica que h=1
    y h=3 se evaluan con normalidad mientras h=2 queda en training_failed.
    """
    from predictive_modeling import operational_run

    df = _synthetic_frame()
    dataset_sha256 = _dataset_sha256(df)
    real_fit_seed = operational_run.fit_seed
    calls = {"n": 0}

    def flaky_fit_seed(**kwargs):
        calls["n"] += 1
        if calls["n"] == 6:  # primera llamada de semilla del horizonte 2
            raise ValueError("synthetic single-class failure forced for this test")
        return real_fit_seed(**kwargs)

    monkeypatch.setattr(operational_run, "fit_seed", flaky_fit_seed)

    result = operational_run.run_operational_manifest(
        frozen_manifest, df, dataset_sha256=dataset_sha256
    )

    statuses = {hr.horizon: hr.status for hr in result.horizons}
    assert statuses[1] == "evaluated"
    assert statuses[2] == "training_failed"
    assert statuses[3] == "evaluated"

    failed = next(hr for hr in result.horizons if hr.horizon == 2)
    assert failed.reason is not None and "training_failed" in failed.reason
    assert failed.contract is None
    assert failed.seed_fits == ()

    for horizon in (1, 3):
        evaluated = next(hr for hr in result.horizons if hr.horizon == horizon)
        assert len(evaluated.seed_fits) == 5
        assert evaluated.contract is not None

    # Con solo 2 de 3 horizontes entrenados, la familia h=1/2/3 no puede
    # validarse como conjunto compatible completo.
    assert result.contract_family_valid is False
