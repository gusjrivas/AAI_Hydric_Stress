from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.artifacts import (
    OutputDirectoryNotEmptyError,
    ensure_output_directory,
    oof_to_dataframe,
    write_stage_a_artifacts,
)
from experiment_runner.controlled_daily_v4.provenance import ProvenanceReport
from experiment_runner.controlled_daily_v4.selection import CandidateOOF, select_family


def _dummy_oof(family):
    frame = pd.DataFrame({"segment_id": ["outer_fold_1"] * 10})
    return CandidateOOF(
        family=family,
        y_true=np.array([0, 1] * 5),
        y_pred=np.array([0, 1] * 5),
        y_score=np.array([0.1, 0.9] * 5),
        frame_with_segment_id=frame,
    )


def test_ensure_output_directory_rejects_non_empty_without_overwrite(tmp_path):
    (tmp_path / "existing.txt").write_text("x")
    with pytest.raises(OutputDirectoryNotEmptyError):
        ensure_output_directory(tmp_path, overwrite=False)


def test_ensure_output_directory_allows_overwrite(tmp_path):
    (tmp_path / "existing.txt").write_text("x")
    result = ensure_output_directory(tmp_path, overwrite=True)
    assert result == tmp_path


def test_oof_to_dataframe_includes_predictions():
    oof = _dummy_oof("logistic_regression")
    df = oof_to_dataframe(oof)
    assert set(["segment_id", "y_true", "y_pred", "y_score"]).issubset(df.columns)
    assert len(df) == 10


def test_write_stage_a_artifacts_produces_expected_files(tmp_path):
    dummy_oof_by_family = {
        "logistic_regression": _dummy_oof("logistic_regression"),
        "random_forest": _dummy_oof("random_forest"),
        "hist_gradient_boosting_classifier": _dummy_oof("hist_gradient_boosting_classifier"),
        "soft_voting": _dummy_oof("soft_voting"),
    }
    selection_result = select_family(dummy_oof_by_family, delta=0.05, n_replicas=10, seed=1)

    provenance_report = ProvenanceReport(era5_path="era5.csv", nasa_power_path="nasa.csv")

    written = write_stage_a_artifacts(
        tmp_path / "out",
        depth_column="soil_moisture_0_to_7cm",
        resolved_config={"stage": "A"},
        provenance_report=provenance_report,
        environment_info={"python": "3.11.16"},
        input_hashes={"era5_sha256": "abc", "nasa_power_sha256": "def"},
        outer_fold_boundaries=[{"outer_fold_index": 1}],
        per_family_outer_results={},
        oof_by_family=dummy_oof_by_family,
        selection_result=selection_result,
        frozen_single_family=None,
        frozen_soft_voting_bases=None,
        final_p20_train=0.31,
    )

    assert (tmp_path / "out" / "selection_decision.json").exists()
    assert (tmp_path / "out" / "holdout_status.json").exists()
    payload = json.loads((tmp_path / "out" / "holdout_status.json").read_text(encoding="utf-8"))
    assert payload["stage_b_executed"] is False
    assert payload["stage_c_executed"] is False
    assert payload["holdout_2024_2025_open"] is False

    selection_payload = json.loads(
        (tmp_path / "out" / "selection_decision.json").read_text(encoding="utf-8")
    )
    assert "|" not in "".join(selection_payload["global_mcc_by_family"].keys())
    for key in selection_payload["pairwise_intervals"]:
        assert "|" in key

    for path in written.values():
        assert path.exists()


def test_write_stage_a_artifacts_rejects_overwrite_by_default(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "something.json").write_text("{}")

    provenance_report = ProvenanceReport(era5_path="era5.csv", nasa_power_path="nasa.csv")
    dummy = {
        "logistic_regression": _dummy_oof("logistic_regression"),
        "random_forest": _dummy_oof("random_forest"),
        "hist_gradient_boosting_classifier": _dummy_oof("hist_gradient_boosting_classifier"),
        "soft_voting": _dummy_oof("soft_voting"),
    }
    selection_result = select_family(dummy, delta=0.05, n_replicas=5, seed=1)

    with pytest.raises(OutputDirectoryNotEmptyError):
        write_stage_a_artifacts(
            out_dir,
            depth_column="soil_moisture_0_to_7cm",
            resolved_config={},
            provenance_report=provenance_report,
            environment_info={},
            input_hashes={},
            outer_fold_boundaries=[],
            per_family_outer_results={},
            oof_by_family=dummy,
            selection_result=selection_result,
            frozen_single_family=None,
            frozen_soft_voting_bases=None,
            final_p20_train=0.3,
        )
