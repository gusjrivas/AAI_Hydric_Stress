"""Prerecorded acceptance examples; fixtures only, no external datasets."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.metrics import metrics_payload, onset_metrics
from experiment_runner.controlled_daily_v4.stage_b_custody import (
    finalize,
    recover,
    reserve,
    validate_paths,
)
from experiment_runner.controlled_daily_v4.tuning import InsufficientFoldSupport, select_best_config


def test_onsets_distinguish_early_same_day_late_and_missed():
    y = [0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0]
    alerts = [0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1]
    result = onset_metrics(y, alerts, pd.date_range("2020-01-01", periods=len(y)))
    assert result["episodes"] == dict(
        total=4, evaluable=4, censored=0, anticipated=1, same_day=1, late=1, missed=1
    )
    assert [r["lead_days"] for r in result["records"]] == [3, 0, -1, None]
    assert result["false_notice_days"] == 1
    assert result["false_notice_runs"] == 1
    assert result["anticipation_rate"]["value"] == 0.25


def test_onset_no_episodes_and_segment_boundaries_are_not_zero_evidence():
    dates = pd.date_range("2020-01-01", periods=4)
    r = onset_metrics([0] * 4, [0] * 4, dates)
    assert r["anticipation_rate"]["status"] == "undefined"
    r = onset_metrics([0, 1, 1, 0], [0, 0, 1, 0], dates, [0, 0, 1, 1])
    assert r["episodes"]["total"] == 2
    assert r["episodes"]["censored"] == 1
    assert r["episodes"]["missed"] == 1


def test_onset_gaps_and_invalid_dates():
    r = onset_metrics([0, 1], [0, 1], pd.to_datetime(["2020-01-01", "2020-01-03"]))
    assert r["episodes"]["censored"] == 1
    with pytest.raises(ValueError):
        onset_metrics([0, 1], [0, 1], ["2020-01-01", "2020-01-01"])


@pytest.mark.parametrize("label", [0, 1])
def test_monoclass_defined_metrics_keep_support(label):
    result = metrics_payload([label] * 4, [0, 1, 0, 1], [0.1, 0.8, 0.3, 0.9])
    assert result["n_observations"] == 4
    assert result["mcc"]["status"] == "undefined"
    assert result["balanced_accuracy"]["status"] == "undefined"
    assert result["brier_score"]["status"] == "defined"
    assert result["log_loss"]["status"] == "defined"
    assert sum(map(sum, result["confusion_matrix"])) == 4
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("scores", [[np.nan] * 3, [1, np.nan, np.nan]])
def test_no_selection_without_two_folds(monkeypatch, scores):
    monkeypatch.setattr(
        "experiment_runner.controlled_daily_v4.tuning.evaluate_config_on_folds",
        lambda *args: scores,
    )
    with pytest.raises(InsufficientFoldSupport):
        select_best_config([SimpleNamespace(family="fixture", params={})], [])


def test_two_valid_folds_selects_by_score_not_order(monkeypatch):
    monkeypatch.setattr(
        "experiment_runner.controlled_daily_v4.tuning.evaluate_config_on_folds",
        lambda config, folds: config.scores,
    )
    low = SimpleNamespace(family="fixture", params={}, scores=[0, 0, np.nan])
    high = SimpleNamespace(family="fixture", params={}, scores=[0.5, 0.7, np.nan])
    selected, median, _ = select_best_config([low, high], [])
    assert selected is high
    assert median == 0.6


def test_bootstrap_support_rejects_79_percent_and_accepts_80(monkeypatch):
    from experiment_runner.controlled_daily_v4 import bootstrap as b

    monkeypatch.setattr(b, "build_segment_plans", lambda *a, **k: [])
    monkeypatch.setattr(
        b, "moving_block_bootstrap_indices", lambda *a, **k: [np.array([i]) for i in range(100)]
    )
    for valid in [79, 80]:

        def metric(y, p):
            return float(y[0]) if y[0] < valid else np.nan

        def call():
            return b.paired_bootstrap_delta(
                np.arange(100), np.zeros(100), np.ones(100), pd.DataFrame(), metric, 100
            )

        if valid == 79:
            with pytest.raises(b.NoValidBootstrapReplicasError) as exc:
                call()
            assert exc.value.diagnostics.replicas_valid == 79
            assert exc.value.diagnostics.discarded_fraction == 0.21
        else:
            assert call().diagnostics.support_sufficient


def test_stage_a_insufficient_folds_returns_no_candidate(monkeypatch):
    from experiment_runner.controlled_daily_v4 import stage_a_runner as a

    monkeypatch.setattr(
        a, "_run_stage_a", lambda *args: (_ for _ in ()).throw(InsufficientFoldSupport("no folds"))
    )
    monkeypatch.setattr(a, "build_eligible_frame", lambda *args: pd.DataFrame())
    monkeypatch.setattr(a, "compute_dataset_fingerprint", lambda *args: {})
    result = a.run_stage_a(None, "unused")
    assert result.selection.outcome == "NO_VALID_SELECTION"
    assert result.selection.selected_family is None
    assert result.final_estimator is None


def test_b_custody_blocks_second_candidate_and_incomplete_recovery(tmp_path):
    registry = tmp_path / "registry.sqlite"
    reserve(registry, {"candidate": "A"})
    with pytest.raises(ValueError, match="already attempted"):
        reserve(registry, {"candidate": "B"})
    with pytest.raises(ValueError, match="Incomplete"):
        recover(registry, "process interrupted")


def test_b_recovery_verifies_hashes_and_records_event(tmp_path):
    import sqlite3

    registry = tmp_path / "registry.sqlite"
    attempt = reserve(registry, {"candidate": "A"})
    out = tmp_path / "output"
    out.mkdir()
    for name in (
        "decision.json",
        "predictions_2023.csv",
        "metrics.json",
        "stage_b_custody.json",
        "code_version.json",
        "resolved_config.json",
    ):
        (out / name).write_text("{}")
    finalize(registry, attempt, out)
    assert recover(registry, "recover after terminal disconnect")["directory"] == str(out)
    with sqlite3.connect(registry) as conn:
        assert (
            conn.execute("SELECT count(*) FROM events WHERE kind='RECOVERED_READ_ONLY'").fetchone()[
                0
            ]
            == 1
        )
    (out / "metrics.json").write_text("altered")
    with pytest.raises(ValueError, match="integrity"):
        recover(registry, "check altered artifact")


def test_scientific_paths_reject_checkout_and_overlap(tmp_path):
    repo = tmp_path / "checkout"
    repo.mkdir()
    with pytest.raises(ValueError, match="outside checkout"):
        validate_paths(repo / "out", tmp_path / "registry", tmp_path / "A", repo)
    with pytest.raises(ValueError, match="outside all"):
        validate_paths(tmp_path / "out", tmp_path / "out" / "ledger", tmp_path / "A", repo)


def test_preflight_disjoint_paths(tmp_path):
    from experiment_runner.controlled_daily_v4.preflight import validate_layout

    paths = [tmp_path / name for name in ("repo", "raw", "evidence", "ledger", "backup")]
    for path in paths:
        path.mkdir()
    assert validate_layout(*paths) == paths
    with pytest.raises(ValueError, match="disjoint"):
        validate_layout(paths[0], paths[1], paths[2], paths[2], paths[4])


def test_mcc_constant_prediction_is_undefined():
    result = metrics_payload([0, 1, 0, 1], [0, 0, 0, 0], [0.1] * 4)
    assert result["mcc"]["value"] is None
    assert result["mcc"]["undefined_reason"] == "constant_prediction"


def test_b_guard_reserves_before_value_validation(tmp_path, monkeypatch):
    from experiment_runner.controlled_daily_v4 import stage_b_custody as b

    producer = tmp_path / "A"
    producer.mkdir()
    (producer / "frozen_config.json").write_text("{}")
    (producer / "resolved_config.json").write_text(json.dumps({"image_id": "sha256:" + "a" * 64}))
    from experiment_runner.controlled_daily_v4.features import feature_contract

    raw1, raw2 = tmp_path / "era5", tmp_path / "nasa"
    raw1.write_text("fixture")
    raw2.write_text("fixture")
    registry = tmp_path / "b.sqlite"
    args = SimpleNamespace(
        input_mode="scientific",
        stage_b_registry_path=registry,
        output_dir=tmp_path / "B",
        producer_dir=producer,
        recover_stage_b=False,
        overwrite=False,
        image_id="sha256:" + "a" * 64,
        seed=20250109,
        bootstrap_replicas=5000,
        era5_csv=raw1,
        nasa_power_csv=raw2,
    )
    contract = SimpleNamespace(
        scientific_run=True,
        candidate_produced=True,
        depth_role="primary_selection",
        producer_code_identity={"commit": "a" * 40},
        raw={"feature_contract": feature_contract()},
    )
    monkeypatch.setattr(
        "experiment_runner.controlled_daily_v4.transfer_contract.load_frozen_config_contract",
        lambda *a: contract,
    )

    def validation(*a, **kw):
        assert registry.exists()
        with pytest.raises(ValueError, match="already attempted"):
            b.reserve(registry, {})
        return SimpleNamespace(ok=False)

    monkeypatch.setattr(
        "experiment_runner.controlled_daily_v4.provenance.validate_pergamino_provenance", validation
    )
    with pytest.raises(ValueError, match="Provenance failed"):
        b.guarded_stage_b(
            args,
            lambda *a, **kw: pytest.fail("fit must not run"),
            code_identity=SimpleNamespace(available=True, dirty=False, commit="a" * 40),
            environment_info={},
        )


def test_global_selection_needs_two_valid_outer_folds():
    from experiment_runner.controlled_daily_v4.selection import CandidateOOF, select_family

    truth = np.array([0, 0, 1, 1, 0, 1])
    candidate = CandidateOOF(
        "logistic_regression",
        truth,
        truth,
        truth.astype(float),
        pd.DataFrame({"segment_id": [0, 0, 1, 1, 2, 2]}),
    )
    result = select_family({"logistic_regression": candidate})
    assert result.selected_family is None
    assert result.selection_reason.startswith("insufficient_outer_fold_support")


def test_preflight_does_not_read_input_contents(tmp_path, monkeypatch):
    from experiment_runner.controlled_daily_v4 import preflight as p

    paths = [tmp_path / name for name in ("repo", "raw", "evidence", "ledger", "backups")]
    for path in paths:
        path.mkdir()
    for name in (
        "pergamino_era5land_soil_hourly_2015_2025.csv",
        "pergamino_nasa_power_daily_2015_2025.csv",
    ):
        (paths[1] / name).write_text("fixture")
    reference = SimpleNamespace(size_bytes=7, sha256="a" * 64)
    monkeypatch.setattr(
        p,
        "load_manifest_identity_reference",
        lambda: SimpleNamespace(era5=reference, nasa_power=reference),
    )
    monkeypatch.setattr(
        p,
        "capture_code_identity",
        lambda: SimpleNamespace(available=True, dirty=False, commit="b" * 40),
    )
    monkeypatch.setattr(p, "capture_environment", lambda: {})
    monkeypatch.setattr(p, "validate_environment", lambda env: SimpleNamespace(ok=True))
    hashed = []
    monkeypatch.setattr(p, "sha", lambda path: hashed.append(path) or "c" * 64)
    payload = p.prepare_manifest(*paths, image_id="sha256:" + "d" * 64)
    assert payload["values_read"] is False
    assert set(hashed) == {p.DEFAULT_CONSTRAINTS_PATH, p.DEFAULT_MANIFEST_PATH}
    assert list(paths[3].iterdir()) == []
    assert payload["scientific_stages_executed"] == []


def test_b_parallel_attempts_share_one_reservation(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    registry = tmp_path / "concurrent.sqlite"

    def attempt(number):
        try:
            return reserve(registry, {"candidate": number})
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        attempts = list(executor.map(attempt, [1, 2]))
    assert sum(value is not None for value in attempts) == 1
