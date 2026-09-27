from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts import export_ensemble_retrospective_tables as exporter


def _metric(method: str, horizon: int) -> dict:
    probabilistic = method in exporter.PROBABILISTIC_METHODS
    item = {
        "n": 100 - horizon,
        "positives": 20,
        "negatives": 80 - horizon,
        "prevalence": 0.12345678901234567,
        "confusion_matrix": {"tn": 70, "fp": 10 - horizon, "fn": horizon, "tp": 20 - horizon},
        "precision": {"status": "defined", "value": 0.8123456789012345, "reason": None},
        "recall": {"status": "defined", "value": 0.9, "reason": None},
        "f1": {"status": "defined", "value": 0.85, "reason": None},
        "mcc": {"status": "defined", "value": 0.5 + horizon / 100, "reason": None},
    }
    if method != "persistence":
        item["delta_mcc_vs_persistence"] = {
            "status": "defined",
            "value": 0.01 * horizon,
            "reason": None,
        }
    if probabilistic:
        item["average_precision"] = {
            "status": "defined",
            "value": 0.7012345678901234,
            "reason": None,
        }
        item["brier"] = {"status": "defined", "value": 0.1012345678901234, "reason": None}
        item["reliability_bins"] = [
            {
                "lower": index / 10,
                "upper": (index + 1) / 10,
                "right_inclusive": index == 9,
                "n": 0 if index == 5 else 10,
                "positives": 0 if index == 5 else index,
                "mean_score": None if index == 5 else index / 10 + 0.01,
                "observed_fraction": None if index == 5 else index / 10,
            }
            for index in range(10)
        ]
    return item


def _fixture_metrics() -> dict:
    horizons = {}
    comparisons = (
        "average_minus_majority",
        "average_minus_persistence",
        "hist_gradient_boosting_classifier_minus_persistence",
        "logistic_regression_minus_persistence",
        "majority_minus_persistence",
        "random_forest_minus_persistence",
    )
    for horizon in (1, 2, 3):
        methods = {method: _metric(method, horizon) for method in exporter.METHOD_ORDER}
        episodes = {
            method: {
                "evaluable_episodes": 4,
                "detected_episodes": horizon,
                "missed_episodes": 4 - horizon,
                "recall": {"status": "defined", "value": horizon / 4, "reason": None},
            }
            for method in exporter.METHOD_ORDER
        }
        horizons[str(horizon)] = {
            "candidate_emissions": 100 - horizon,
            "common_cases": 100 - horizon,
            "coverage_fraction": 1.0,
            "physical_threshold_p20": 0.3130583333333333,
            "decision_threshold": 0.5,
            "exclusions": {},
            "individual_availability": {
                "hist_gradient_boosting_classifier": {"available": 100 - horizon},
                "logistic_regression": {"available": 100 - horizon},
                "random_forest": {"available": 100 - horizon},
            },
            "metrics": methods,
            "case_b_nondry_at_t_dry_at_target": {
                "n": 7,
                "detected": {method: horizon for method in exporter.METHOD_ORDER},
            },
            "episodes": {
                "episodes_total": 5,
                "starts_determinable": 4,
                "left_censored": 1,
                "right_censored": 1,
                "evaluable_for_horizon": 4,
                "methods": episodes,
            },
            "uncertainty": {
                "block_length_days": 30,
                "seed": 20250109,
                "replicates_requested": 5000,
                "comparisons": {
                    name: {
                        "status": "defined",
                        "reason": None,
                        "delta_mcc_ci95": [-0.0123456789012345, 0.0345678901234567],
                        "replicates_defined": 5000,
                        "replicates_discarded_undefined": 0,
                    }
                    for name in comparisons
                },
            },
        }
    return {"horizons": horizons}


def _write_sources(root: Path) -> tuple[str, str, dict]:
    metrics = _fixture_metrics()
    manifest = {
        "status": "completado",
        "code_identity": {"commit": "a" * 40},
        "protocol_sha256": "b" * 64,
        "started_at_utc": "2026-09-27T00:00:00+00:00",
        "completed_at_utc": "2026-09-27T00:01:00+00:00",
    }
    metrics_path = root / "metrics.json"
    manifest_path = root / "execution_manifest.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return exporter.sha256_file(metrics_path), exporter.sha256_file(manifest_path), metrics


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_exported_csvs_match_every_aggregate_fixture_and_preserve_nulls(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    metrics_hash, manifest_hash, metrics = _write_sources(source)
    exporter.export_tables(
        source,
        output,
        expected_metrics_sha256=metrics_hash,
        expected_manifest_sha256=manifest_hash,
    )

    support = _rows(output / "evaluation_support.csv")
    classifications = _rows(output / "classification_metrics.csv")
    comparisons = _rows(output / "paired_mcc_comparisons.csv")
    episodes = _rows(output / "episode_onset.csv")
    reliability = _rows(output / "reliability_bins.csv")
    assert len(support) == 3
    assert len(classifications) == 18
    assert len(comparisons) == 18
    assert len(episodes) == 18
    assert len(reliability) == 120

    for row in support:
        source_h = metrics["horizons"][row["horizon_days"]]
        assert row["candidate_emissions"] == str(source_h["candidate_emissions"])
        assert row["physical_threshold_p20"] == str(source_h["physical_threshold_p20"])

    for row in classifications:
        source_item = metrics["horizons"][row["horizon_days"]]["metrics"][row["method"]]
        assert row["mcc_value"] == str(source_item["mcc"]["value"])
        assert row["tp"] == str(source_item["confusion_matrix"]["tp"])
        if row["method"] in {"persistence", "majority"}:
            assert row["average_precision_value"] == ""
            assert row["average_precision_status"] == "not_applicable"
            assert row["average_precision_value"] != "0"

    assert {row["comparison"] for row in comparisons} == set(
        metrics["horizons"]["1"]["uncertainty"]["comparisons"]
    )
    for row in comparisons:
        source_item = metrics["horizons"][row["horizon_days"]]["uncertainty"]["comparisons"][
            row["comparison"]
        ]
        assert row["ci95_lower"] == str(source_item["delta_mcc_ci95"][0])

    for row in episodes:
        source_item = metrics["horizons"][row["horizon_days"]]["episodes"]["methods"][row["method"]]
        assert row["detected_episodes"] == str(source_item["detected_episodes"])

    empty_bin = next(
        row
        for row in reliability
        if row["horizon_days"] == "1" and row["method"] == "average" and row["bin_index"] == "5"
    )
    assert empty_bin["mean_score_value"] == ""
    assert empty_bin["mean_score_status"] == "undefined"
    assert empty_bin["mean_score_reason"] == "empty_bin"
    assert empty_bin["mean_score_value"] != "0"

    readme = (output / "README.md").read_text(encoding="utf-8")
    assert metrics_hash in readme
    assert manifest_hash in readme
    assert "a" * 40 in readme
    assert "b" * 64 in readme
    assert "export_ensemble_retrospective_tables.py" in readme


def test_export_fails_closed_on_source_hash_substitution(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    metrics_hash, manifest_hash, _ = _write_sources(source)
    (source / "metrics.json").write_text("{}", encoding="utf-8")
    with pytest.raises(exporter.ExportError, match="SHA-256 inesperado"):
        exporter.export_tables(
            source,
            output,
            expected_metrics_sha256=metrics_hash,
            expected_manifest_sha256=manifest_hash,
        )


def test_canonical_hash_constants_are_exact():
    assert exporter.EXPECTED_METRICS_SHA256 == (
        "6a6a31d35196313061aa4363c98d422f4d1446a9f996d7af51cd93f762e67732"
    )
    assert exporter.EXPECTED_MANIFEST_SHA256 == (
        "780386ff58b490a452d77f968e61efcd15b998a97d28de2f908ab1a346d9d33b"
    )


@pytest.mark.skipif(
    not (exporter.CANONICAL_SOURCE_DIR / "metrics.json").exists(),
    reason="runtime canonico externo no disponible",
)
def test_versioned_tables_are_exact_export_of_canonical_aggregates(tmp_path):
    regenerated = tmp_path / "regenerated"
    exporter.export_tables(exporter.CANONICAL_SOURCE_DIR, regenerated)
    versioned = exporter.DEFAULT_OUTPUT_DIR
    for name in exporter.OUTPUT_FILES:
        assert (regenerated / name).read_bytes() == (versioned / name).read_bytes()
