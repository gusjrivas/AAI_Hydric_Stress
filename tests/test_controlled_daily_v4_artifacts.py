from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.artifacts import (
    OutputDirectoryNotEmptyError,
    StageBOutputDirectoryConflictsWithProducerError,
    ensure_output_directory,
    oof_to_dataframe,
    validate_stage_b_output_directory,
    write_stage_a_artifacts,
)
from experiment_runner.controlled_daily_v4.provenance import ProvenanceReport
from experiment_runner.controlled_daily_v4.selection import CandidateOOF, select_family

DUMMY_SEGMENT_SIZE = 40
DUMMY_N_SEGMENTS = 3
DUMMY_N = DUMMY_SEGMENT_SIZE * DUMMY_N_SEGMENTS


def _dummy_oof(family):
    """OOF sintético con tres segmentos outer de tamaño realista.

    El moving block bootstrap normativo exige bloques de 30 días, de modo que
    cada segmento debe tener al menos 30 observaciones: un segmento más corto
    se rechaza explícitamente y no serviría como fixture."""
    frame = pd.DataFrame(
        {
            "feature_timestamp": pd.date_range("2015-01-07", periods=DUMMY_N),
            "segment_id": sum(
                ([f"outer_fold_{i + 1}"] * DUMMY_SEGMENT_SIZE for i in range(DUMMY_N_SEGMENTS)),
                [],
            ),
        }
    )
    pattern = np.array([0, 1] * (DUMMY_N // 2))
    return CandidateOOF(
        family=family,
        y_true=pattern,
        y_pred=pattern,
        y_score=np.where(pattern == 1, 0.9, 0.1),
        frame_with_segment_id=frame,
        per_fold_mcc=[1.0] * DUMMY_N_SEGMENTS,
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
    assert len(df) == DUMMY_N


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
        input_mode="synthetic",
        scientific_run=False,
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
            input_mode="synthetic",
            scientific_run=False,
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


# --------------------------------------------------------------------------
# Hallazgo 1 (revisión externa 2026-09-14): protección de los artefactos de A
# ante --output-dir/--producer-dir efectivamente coincidentes (unit-level;
# ver test_controlled_daily_v4_stage_b_integration.py para el equivalente por
# CLI, con espía y verificación byte a byte).
# --------------------------------------------------------------------------


def test_validate_stage_b_output_directory_rejects_identical_paths(tmp_path):
    producer_dir = tmp_path / "producer"
    producer_dir.mkdir()
    with pytest.raises(StageBOutputDirectoryConflictsWithProducerError):
        validate_stage_b_output_directory(producer_dir, producer_dir)


def test_validate_stage_b_output_directory_rejects_relative_paths_resolving_to_same_target(
    tmp_path,
):
    producer_dir = tmp_path / "producer"
    producer_dir.mkdir()
    equivalent = tmp_path / "producer" / ".." / "producer"
    with pytest.raises(StageBOutputDirectoryConflictsWithProducerError):
        validate_stage_b_output_directory(equivalent, producer_dir)


def test_validate_stage_b_output_directory_rejects_output_nested_inside_producer(tmp_path):
    producer_dir = tmp_path / "producer"
    producer_dir.mkdir()
    nested_output = producer_dir / "nested_out"
    with pytest.raises(StageBOutputDirectoryConflictsWithProducerError):
        validate_stage_b_output_directory(nested_output, producer_dir)


def test_validate_stage_b_output_directory_rejects_producer_nested_inside_output(tmp_path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    nested_producer = output_dir / "nested_producer"
    with pytest.raises(StageBOutputDirectoryConflictsWithProducerError):
        validate_stage_b_output_directory(output_dir, nested_producer)


def test_validate_stage_b_output_directory_allows_separate_sibling_directories(tmp_path):
    producer_dir = tmp_path / "producer"
    output_dir = tmp_path / "stage_b_out"
    producer_dir.mkdir()
    validate_stage_b_output_directory(output_dir, producer_dir)  # no debe lanzar


def test_write_stage_b_artifacts_rejects_output_dir_equal_to_producer_dir_before_writing(
    tmp_path,
):
    """Ante el rechazo, ningún archivo del `producer_dir` cambia: se
    verifica byte a byte antes/después del intento fallido."""
    import dataclasses

    from experiment_runner.controlled_daily_v4 import artifacts
    from experiment_runner.controlled_daily_v4.bootstrap import BootstrapDiagnostics

    producer_dir = tmp_path / "producer"
    producer_dir.mkdir()
    schema_path = producer_dir / "schema_version.json"
    schema_path.write_text('{"schema_version": "controlled_daily_v4_stage_a.v4"}\n')
    before = schema_path.read_bytes()

    @dataclasses.dataclass
    class _FakeResult:
        training_frame_n_rows: int = 0
        training_dataset_fingerprint: dict = dataclasses.field(default_factory=dict)
        p20_train: float = float("nan")
        evaluation_frame_n_rows: int = 0
        evaluation_target_timestamp_min: str | None = None
        evaluation_target_timestamp_max: str | None = None
        feature_timestamps: object = None
        y_true: object = None
        y_pred_candidate: object = None
        y_score_candidate: object = None
        y_pred_persistence: object = None
        y_pred_majority_class: object = None
        y_pred_constant_stress: object = None
        metrics_candidate: dict = dataclasses.field(default_factory=dict)
        metrics_persistence: dict = dataclasses.field(default_factory=dict)
        metrics_majority_class: dict = dataclasses.field(default_factory=dict)
        metrics_constant_stress: dict = dataclasses.field(default_factory=dict)
        mcc_candidate: float = float("nan")
        mcc_persistence: float = float("nan")
        delta_mcc_point_estimate: float = float("nan")
        bootstrap_result: object = None
        bootstrap_diagnostics: BootstrapDiagnostics | None = None
        verdict: str = "CANDIDATE_NOT_VALIDATED"
        verdict_reasons: list = dataclasses.field(default_factory=list)
        predictions_available: bool = False
        bootstrap_executed: bool = False
        warnings_log: list = dataclasses.field(default_factory=list)

    with pytest.raises(StageBOutputDirectoryConflictsWithProducerError):
        artifacts.write_stage_b_artifacts(
            producer_dir,
            input_mode="synthetic",
            scientific_run=False,
            resolved_config={"stage": "B"},
            producer_dir=producer_dir,
            producer_contract_raw={},
            consumer_code_identity={},
            consumer_environment_info={},
            consumer_environment_issues=[],
            result=_FakeResult(feature_timestamps=[], y_true=[], y_pred_candidate=[]),
            overwrite=True,
        )

    assert schema_path.read_bytes() == before
