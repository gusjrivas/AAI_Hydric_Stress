import json
from copy import deepcopy
from pathlib import Path

import pytest

from predictive_modeling.calibration_manifest import (
    CalibrationManifestError,
    freeze_calibration_manifest,
    inspect_calibration_manifest,
    require_ready_for_fit,
    verify_frozen_calibration_manifest,
)


def _synthetic_ready_manifest():
    """Illustrative values only, explicitly scoped to a synthetic test fixture."""

    return {
        "schema_version": "producer_calibration_plan_v1",
        "contract_version": "producer_daily_h123_v1",
        "status": "ready_for_fit",
        "frozen_at": "2026-09-19T12:00:00Z",
        "calendar_timezone": "UTC",
        "horizons": [1, 2, 3],
        "dataset": {
            "dataset_id": "synthetic-calendar-fixture",
            "sha256": "a" * 64,
            "source_kind": "synthetic",
            "synthetic_fixture": True,
            "site": "synthetic-site",
            "sensor_id": "synthetic-sensor",
            "population": "synthetic unit-test days",
            "provenance": "generated deterministically inside the test",
            "prior_exposure": "synthetic fixture; no real assessment claim",
            "allowed_dates": {"start": "2024-01-01", "end": "2024-04-30"},
        },
        "intended_use": "exercise validators only; not a real calibration plan",
        "event": {
            "variable": "soil_moisture",
            "unit": "m3/m3",
            "comparison": "lt",
            "percentile": 20.0,
            "threshold_source": "training_observations_only",
            "threshold_reference": {"start": "2024-01-01", "end": "2024-02-29"},
        },
        "partitions": {
            "train": {"start": "2024-01-01", "end": "2024-02-29"},
            "calibration": {"start": "2024-03-01", "end": "2024-03-31"},
            "evaluation": {"start": "2024-04-01", "end": "2024-04-30"},
        },
        "model_plan": {
            "family": "synthetic-random-forest-fixture",
            "hyperparameters": {"n_estimators": 2, "max_depth": 1},
        },
        "training_seeds": [0, 1, 2, 3, 4],
        "deployment_seed": 2,
        "calibration": {"method": "sigmoid"},
        "probability_bins": {
            "strategy": "equal_width",
            "count": 10,
            "include_one_in_last": True,
        },
        "support": {
            "minimum_bin_count": 2,
            "minimum_class_count": 2,
            "minimum_temporal_blocks": 2,
            "justification": "small synthetic fixture values; never for real data",
        },
        "coverage": {"minimum": 0.5},
        "tolerances": {
            "epsilon_ece": 0.2,
            "epsilon_bin": 0.3,
            "justification": "synthetic validator boundary values only",
        },
        "stability_windows": [
            {
                "start": "2024-04-01",
                "end": "2024-04-15",
                "criteria_reference": "global",
            },
            {
                "start": "2024-04-16",
                "end": "2024-04-30",
                "criteria_reference": "global",
            },
        ],
        "uncertainty": {
            "method": "synthetic-moving-block-bootstrap-fixture",
            "block_length_days": 2,
            "gap_treatment": "preserve synthetic calendar positions",
            "replicates": 10,
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


def test_incomplete_draft_is_distinct_from_a_ready_plan_and_cannot_enable_fit():
    draft = {
        "schema_version": "producer_calibration_plan_v1",
        "contract_version": "producer_daily_h123_v1",
        "status": "draft",
    }

    report = inspect_calibration_manifest(draft)

    assert report.declared_status == "draft"
    assert not report.ready_for_fit
    assert report.issues
    with pytest.raises(CalibrationManifestError, match="status no es ready_for_fit"):
        require_ready_for_fit(draft)


def test_approved_tolerances_do_not_automatically_enable_fitting():
    path = Path(__file__).resolve().parents[1] / "config" / "producer-calibration-plan.draft.json"
    draft = json.loads(path.read_text(encoding="utf-8"))

    report = inspect_calibration_manifest(draft)

    assert report.declared_status == "draft"
    assert not report.ready_for_fit

    # Decisiones ya ratificadas (docs/design/operational-calibration-manifest-decisions.md):
    # deben estar presentes y no generar incumplimientos propios.
    assert draft["dataset"]["sensor_id"]
    assert draft["model_plan"]["hyperparameters"]
    assert draft["deployment_seed"] in draft["training_seeds"]
    for ratified_section in (
        "support",
        "coverage",
        "stability_windows",
        "uncertainty",
        "multiplicity",
        "log_loss",
    ):
        assert ratified_section in draft

    # Approved product tolerances do not automatically authorize fitting.
    assert draft["tolerances"]["epsilon_ece"] == 0.10
    assert draft["tolerances"]["epsilon_bin"] == 0.15
    assert draft["tolerances"]["justification"]
    assert draft["tolerances"]["approval"]["date"] == "2026-09-20"
    assert report.issues == ()

    with pytest.raises(CalibrationManifestError, match="status no es ready_for_fit"):
        require_ready_for_fit(draft)


def test_complete_synthetic_fixture_can_exercise_the_prefit_gate():
    manifest = _synthetic_ready_manifest()

    report = inspect_calibration_manifest(manifest)

    assert report.ready_for_fit
    require_ready_for_fit(manifest)


@pytest.mark.parametrize(
    ("path", "invalid_value"),
    [
        (("support", "minimum_bin_count"), None),
        (("support", "minimum_class_count"), 0),
        (("support", "minimum_temporal_blocks"), -1),
        (("coverage", "minimum"), 1.1),
        (("tolerances", "epsilon_ece"), 0),
        (("tolerances", "epsilon_bin"), 1),
        (("stability_windows",), []),
        (("uncertainty", "block_length_days"), 0),
        (("uncertainty", "replicates"), None),
        (("uncertainty", "resampling_seed"), None),
        (("multiplicity", "family_dimensions"), ["horizon"]),
        (("deployment_seed",), None),
    ],
)
def test_missing_or_out_of_range_methodological_decisions_block_fit(path, invalid_value):
    manifest = deepcopy(_synthetic_ready_manifest())
    target = manifest
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = invalid_value

    with pytest.raises(CalibrationManifestError):
        require_ready_for_fit(manifest)


def test_overlapping_or_out_of_evaluation_stability_windows_block_fit():
    manifest = deepcopy(_synthetic_ready_manifest())
    manifest["stability_windows"][1]["start"] = "2024-04-15"

    with pytest.raises(CalibrationManifestError, match="no debe solaparse"):
        require_ready_for_fit(manifest)


def test_real_data_cannot_be_disguised_as_an_unmarked_synthetic_fixture():
    manifest = deepcopy(_synthetic_ready_manifest())
    manifest["dataset"]["synthetic_fixture"] = False

    with pytest.raises(CalibrationManifestError, match="synthetic_fixture=true"):
        require_ready_for_fit(manifest)


def test_freeze_records_exact_content_identity_and_detects_later_changes(tmp_path):
    manifest = _synthetic_ready_manifest()
    path = tmp_path / "synthetic-calibration-plan.json"

    identity = freeze_calibration_manifest(manifest, path)

    assert (
        identity.sha256
        == json.loads(identity.identity_path.read_text(encoding="utf-8"))["content_sha256"]
    )
    assert verify_frozen_calibration_manifest(path) == manifest

    changed = json.loads(path.read_text(encoding="utf-8"))
    changed["deployment_seed"] = 3
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(CalibrationManifestError, match="ya no coincide"):
        verify_frozen_calibration_manifest(path)


def test_freeze_never_overwrites_an_existing_manifest(tmp_path):
    path = tmp_path / "synthetic-calibration-plan.json"
    freeze_calibration_manifest(_synthetic_ready_manifest(), path)

    with pytest.raises(FileExistsError):
        freeze_calibration_manifest(_synthetic_ready_manifest(), path)
