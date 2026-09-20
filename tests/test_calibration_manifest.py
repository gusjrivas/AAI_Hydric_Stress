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


def test_frozen_v1_manifest_is_preserved_untouched_but_superseded():
    """v1 (2026-09-20) computed ECE only over bins with support, contradicting
    design.md ("no omitir intervalos de poco soporte del cálculo para mejorar
    la cifra"). It is kept as historical evidence, byte-for-byte, and must
    never be treated as the active manifest again."""
    repo_root = Path(__file__).resolve().parents[1]
    frozen_path = repo_root / "config" / "producer-calibration-plan.frozen.json"

    frozen_v1 = verify_frozen_calibration_manifest(frozen_path)

    assert (
        json.loads(
            (
                repo_root / "config" / "producer-calibration-plan.frozen.json.identity.json"
            ).read_text(encoding="utf-8")
        )["content_sha256"]
        == "0301207e5d750002694a73b3e9313ee2ea6bff58f1081fcd4797c2ef9279cbd1"
    )
    assert "solo bins con soporte en esa replica" in frozen_v1["uncertainty"]["method"].lower()


def test_frozen_v2_manifest_matches_the_corrected_draft_and_fixes_the_ece_bug():
    repo_root = Path(__file__).resolve().parents[1]
    frozen_path = repo_root / "config" / "producer-calibration-plan.frozen.v2.json"
    draft_path = repo_root / "config" / "producer-calibration-plan.draft.json"

    frozen = verify_frozen_calibration_manifest(frozen_path)

    assert frozen["status"] == "ready_for_fit"
    assert frozen["frozen_at"]
    report = inspect_calibration_manifest(frozen)
    assert report.ready_for_fit
    require_ready_for_fit(frozen)

    # El borrador se conserva como antecedente: mismo contenido salvo
    # status/frozen_at, y sigue bloqueado para ajuste por diseño.
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    assert draft["status"] == "draft"
    assert not inspect_calibration_manifest(draft).ready_for_fit
    freeze_only_fields = {"status", "frozen_at"}
    frozen_without_freeze_fields = {
        key: value for key, value in frozen.items() if key not in freeze_only_fields
    }
    draft_without_freeze_fields = {
        key: value for key, value in draft.items() if key not in freeze_only_fields
    }
    assert frozen_without_freeze_fields == draft_without_freeze_fields

    # No tocamos tolerancias ni particiones al corregir el ECE.
    assert frozen["tolerances"]["epsilon_ece"] == 0.10
    assert frozen["tolerances"]["epsilon_bin"] == 0.15
    assert frozen["partitions"] == {
        "train": {"start": "2024-01-01", "end": "2024-08-06"},
        "calibration": {"start": "2024-08-07", "end": "2024-10-18"},
        "evaluation": {"start": "2024-10-19", "end": "2024-12-31"},
    }


def test_draft_separates_ece_inclusion_backed_bins_and_replicate_invalidity():
    """design.md: ECE sums over every non-empty bin; support.minimum_bin_count
    only gates coverage/individually publishable bins, never the ECE sum."""
    path = Path(__file__).resolve().parents[1] / "config" / "producer-calibration-plan.draft.json"
    draft = json.loads(path.read_text(encoding="utf-8"))
    uncertainty = draft["uncertainty"]

    method = uncertainty["method"].lower()
    assert "solo bins con soporte" not in method

    ece_inclusion = uncertainty["ece_bin_inclusion"].lower()
    assert "no vac" in ece_inclusion or "al menos 1 observacion" in ece_inclusion
    assert "no omitir intervalos de poco soporte" in ece_inclusion
    assert "minimum_bin_count no filtra esta suma" in ece_inclusion

    backed_bin_family = uncertainty["backed_bin_family"]
    assert "minimum_bin_count" in backed_bin_family
    assert "epsilon_bin" in backed_bin_family or "supported_probability_bin" in backed_bin_family

    invalid_rule = uncertainty["invalid_replicate_rule"].lower()
    assert "minimum_class_count" in invalid_rule
    assert "minimum_temporal_blocks" in invalid_rule
    assert "no invalida la replica" in invalid_rule or "no invalida por si solo" in invalid_rule


def test_synthetic_ece_over_all_nonempty_bins_differs_from_support_filtered_ece():
    """Illustrative, synthetic-only: demonstrates why excluding a low-support
    (but non-empty) bin from ECE understates the miscalibration, which is
    exactly the bug fixed in this revision. No real data is used."""

    def ece(bins: list[dict], *, total: int) -> float:
        return sum(b["count"] / total * abs(b["freq"] - b["mean_prob"]) for b in bins)

    bins = [
        {"count": 40, "freq": 0.30, "mean_prob": 0.30},  # respaldado, bien calibrado
        {"count": 3, "freq": 0.90, "mean_prob": 0.20},  # no vacio, sin soporte, muy mal calibrado
    ]
    total = sum(b["count"] for b in bins)
    minimum_bin_count = 10

    correct_ece_over_all_nonempty_bins = ece(bins, total=total)
    incorrect_ece_excluding_low_support_bins = ece(
        [b for b in bins if b["count"] >= minimum_bin_count], total=total
    )

    assert correct_ece_over_all_nonempty_bins > incorrect_ece_excluding_low_support_bins
    assert incorrect_ece_excluding_low_support_bins == pytest.approx(0.0)


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
