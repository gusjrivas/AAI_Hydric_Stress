"""Integración sintética de punta a punta: artefactos de A -> contrato ->
Etapa B (CLI y programática) -> artefactos y decisión, y C todavía bloqueada.

Nunca lee datos reales de Pergamino/Balcarce/holdout. Usa exclusivamente
fixtures sintéticas (`tests/controlled_daily_v4_fixtures.py`). El productor A
de estos tests se construye con `--input-mode synthetic` (`scientific_run
=False`), consumido por una Etapa B también sintética: ninguna ejecución de
este archivo se presenta ni puede presentarse como habilitación científica
de la Etapa C.
"""

from __future__ import annotations

import json

from experiment_runner.controlled_daily_v4 import artifacts
from experiment_runner.controlled_daily_v4.cli import main
from experiment_runner.controlled_daily_v4.config import (
    INPUT_MODE_SYNTHETIC,
    PRIMARY_DEPTH_COLUMN,
    HistGradientBoostingGridSpec,
    LogisticRegressionGridSpec,
    ProtocolConfig,
    RandomForestGridSpec,
)
from experiment_runner.controlled_daily_v4.ingestion import (
    aggregate_era5_daily,
    build_daily_joined_series,
    load_era5_hourly_raw,
    load_nasa_power_daily_raw,
    replace_missing_sentinel,
)
from experiment_runner.controlled_daily_v4.provenance import ProvenanceReport
from experiment_runner.controlled_daily_v4.stage_a_runner import run_stage_a
from tests.controlled_daily_v4_fixtures import write_synthetic_pergamino_csv_pair

# 2015-01-01 .. 2023-12-31 (3287 días): el mínimo necesario para que la
# ventana autorizada de A (2015-2022) y la de B (evaluación única de 2023)
# queden ambas cubiertas -- ni un día más, para mantener el test razonable.
_N_DAYS_THROUGH_2023 = 3287

FAST_CONFIG = ProtocolConfig(
    bootstrap_replicas=20,
    logistic_regression_grid=LogisticRegressionGridSpec(C=(0.1, 1.0)),
    random_forest_grid=RandomForestGridSpec(
        n_estimators=(50,), max_depth=(4,), min_samples_leaf=(5,)
    ),
    hist_gradient_boosting_grid=HistGradientBoostingGridSpec(
        learning_rate=(0.1,), max_iter=(50,), max_leaf_nodes=(15,), l2_regularization=(0.0,)
    ),
)


def _daily_series_from_csv(era5_path, nasa_path):
    _era5_meta, era5_df = load_era5_hourly_raw(era5_path)
    era5_daily = aggregate_era5_daily(era5_df)
    _nasa_meta, nasa_df = load_nasa_power_daily_raw(nasa_path)
    nasa_df = replace_missing_sentinel(nasa_df)
    return build_daily_joined_series(era5_daily, nasa_df)


def _write_synthetic_producer_dir(tmp_path, era5_path, nasa_path, producer_dir_name="producer_a"):
    """Corrida programática (no CLI) de la Etapa A con grillas reducidas
    (`FAST_CONFIG`), escrita explícitamente como sintética
    (`input_mode='synthetic'`, `scientific_run=False`) -- exactamente lo que
    produciría `--input-mode synthetic` en la CLI, sin pagar el costo de la
    grilla normativa completa para este test de integración."""
    daily_series = _daily_series_from_csv(era5_path, nasa_path)
    results = run_stage_a(daily_series, PRIMARY_DEPTH_COLUMN, FAST_CONFIG)
    assert results.selection.selected_family is not None, (
        "fixture determinista esperaba un candidato congelado; si esto falla, "
        "ajustar la semilla/tamaño de la serie sintética"
    )

    outer_fold_boundaries = [
        {
            "outer_fold_index": fold.index,
            "segment_id": fold.segment_id,
            "n_train": len(fold.train),
            "n_validation": len(fold.validation),
            "train_feature_start": str(fold.train["feature_timestamp"].min()),
            "train_feature_end": str(fold.train["feature_timestamp"].max()),
            "validation_feature_start": str(fold.validation["feature_timestamp"].min()),
            "validation_feature_end": str(fold.validation["feature_timestamp"].max()),
        }
        for fold in results.outer_folds
    ]

    producer_dir = tmp_path / producer_dir_name
    artifacts.write_stage_a_artifacts(
        producer_dir,
        depth_column=PRIMARY_DEPTH_COLUMN,
        input_mode=INPUT_MODE_SYNTHETIC,
        scientific_run=False,
        resolved_config={"stage": "A", "note": "fixture de integración B, sintético"},
        provenance_report=ProvenanceReport(
            era5_path=str(era5_path), nasa_power_path=str(nasa_path), mode=INPUT_MODE_SYNTHETIC
        ),
        environment_info={},
        input_hashes={},
        outer_fold_boundaries=outer_fold_boundaries,
        inner_fold_boundaries_by_outer=results.inner_folds_by_outer,
        per_family_outer_results=results.per_family_outer_results,
        oof_by_family=results.oof_by_family,
        selection_result=results.selection,
        frozen_single_family=results.frozen_single_family,
        frozen_soft_voting_bases=results.frozen_soft_voting_bases,
        final_p20_train=results.final_p20_train,
        code_version={"available": False, "source": "unavailable", "commit": None, "dirty": None},
        dataset_fingerprint=results.dataset_fingerprint,
        final_estimator_details=results.final_estimator_details,
        soft_voting_combination_weights=results.soft_voting_combination_weights,
        warnings_log=results.warnings_log,
    )
    return producer_dir


def test_end_to_end_synthetic_artifacts_a_to_contract_to_b_to_artifacts_and_decision(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(
        tmp_path, n_days=_N_DAYS_THROUGH_2023, seed=2023
    )
    producer_dir = _write_synthetic_producer_dir(tmp_path, era5, nasa)

    stage_b_out = tmp_path / "stage_b_out"
    exit_code = main(
        [
            "--stage",
            "B",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(stage_b_out),
            "--producer-dir",
            str(producer_dir),
            "--input-mode",
            "synthetic",
            "--bootstrap-replicas",
            "20",
        ]
    )
    assert exit_code == 0

    decision = json.loads((stage_b_out / "decision.json").read_text(encoding="utf-8"))
    assert decision["verdict"] in ("CANDIDATE_VALIDATED", "CANDIDATE_NOT_VALIDATED")

    holdout_status = json.loads((stage_b_out / "holdout_status.json").read_text(encoding="utf-8"))
    assert holdout_status["stage_b_executed"] is True
    assert holdout_status["stage_c_executed"] is False
    assert holdout_status["holdout_2024_2025_open"] is False

    resolved_config = json.loads((stage_b_out / "resolved_config.json").read_text(encoding="utf-8"))
    # Nunca se presenta como habilitación científica: input_mode sintético en
    # ambos extremos (productor y consumidor).
    assert resolved_config["scientific_run"] is False

    # B nunca sobreescribe los artefactos de A: el directorio del productor
    # sigue siendo el de la Etapa A (su propio esquema), separado del de B.
    producer_schema = json.loads((producer_dir / "schema_version.json").read_text(encoding="utf-8"))
    stage_b_schema = json.loads((stage_b_out / "schema_version.json").read_text(encoding="utf-8"))
    assert producer_schema["schema_version"] != stage_b_schema["schema_version"]
    assert "stage_a" in producer_schema["schema_version"]
    assert "stage_b" in stage_b_schema["schema_version"]

    for expected in (
        "predictions_2023.csv",
        "metrics.json",
        "bootstrap.json",
        "p20_train.json",
        "training_dataset_fingerprint.json",
        "producer_reference.json",
    ):
        assert (stage_b_out / expected).exists(), expected


def test_stage_c_is_still_blocked_after_a_and_b_ran(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(
        tmp_path, n_days=_N_DAYS_THROUGH_2023, seed=2023
    )
    exit_code = main(
        [
            "--stage",
            "C",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(tmp_path / "stage_c_out"),
            "--input-mode",
            "synthetic",
        ]
    )
    assert exit_code == 2
    assert not (tmp_path / "stage_c_out").exists()


def test_cli_rejects_inadmissible_contract_before_training_with_spy(tmp_path, monkeypatch):
    """Contrato admisible ESTRUCTURALMENTE (se lee sin error) pero
    INADMISIBLE para esta ejecución concreta (`input_mode='scientific'`
    consumido por una ejecución sintética): la CLI debe rechazarlo antes de
    entrenar. Un espía sobre `stage_b_runner.run_stage_b` confirma que jamás
    se invoca."""
    import experiment_runner.controlled_daily_v4.stage_b_runner as stage_b_runner_module

    def _spy(*_a, **_k):
        raise AssertionError("run_stage_b no debía invocarse: el contrato no era admisible")

    monkeypatch.setattr(stage_b_runner_module, "run_stage_b", _spy)

    era5, nasa = write_synthetic_pergamino_csv_pair(
        tmp_path, n_days=_N_DAYS_THROUGH_2023, seed=2023
    )
    producer_dir = tmp_path / "producer_scientific_marked"
    daily_series = _daily_series_from_csv(era5, nasa)
    results = run_stage_a(daily_series, PRIMARY_DEPTH_COLUMN, FAST_CONFIG)
    assert results.selection.selected_family is not None

    artifacts.write_stage_a_artifacts(
        producer_dir,
        depth_column=PRIMARY_DEPTH_COLUMN,
        # Declarado científico -- pero la ejecución de B de este test es
        # sintética (`--input-mode synthetic`): admissibility.py debe
        # rechazar la incompatibilidad de modos antes de entrenar.
        input_mode="scientific",
        scientific_run=True,
        resolved_config={"stage": "A"},
        provenance_report=ProvenanceReport(era5_path=str(era5), nasa_power_path=str(nasa)),
        environment_info={},
        input_hashes={},
        outer_fold_boundaries=[],
        inner_fold_boundaries_by_outer=results.inner_folds_by_outer,
        per_family_outer_results=results.per_family_outer_results,
        oof_by_family=results.oof_by_family,
        selection_result=results.selection,
        frozen_single_family=results.frozen_single_family,
        frozen_soft_voting_bases=results.frozen_soft_voting_bases,
        final_p20_train=results.final_p20_train,
        code_version={"available": True, "source": "git", "commit": "a" * 40, "dirty": False},
        dataset_fingerprint=results.dataset_fingerprint,
        final_estimator_details=results.final_estimator_details,
        soft_voting_combination_weights=results.soft_voting_combination_weights,
        warnings_log=results.warnings_log,
    )

    stage_b_out = tmp_path / "stage_b_out_rejected"
    exit_code = main(
        [
            "--stage",
            "B",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(stage_b_out),
            "--producer-dir",
            str(producer_dir),
            "--input-mode",
            "synthetic",
            "--bootstrap-replicas",
            "20",
        ]
    )
    assert exit_code == 7
    assert not stage_b_out.exists()
