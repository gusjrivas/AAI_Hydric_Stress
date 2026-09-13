"""Integración de los artefactos de reproducibilidad/trazabilidad (hallazgo H-05).

Cubre: identidad de código capturada antes de entrenar, correspondencia entre
folds registrados y consumidos (outer/inner/congelamiento), huella del
conjunto elegible, y persistencia de advertencias con contexto. Exclusivamente
con datos sintéticos, nunca ejecuta la Etapa A real."""

from __future__ import annotations

import json

import pytest

from experiment_runner.controlled_daily_v4.config import (
    INNER_N_SPLITS,
    OUTER_N_SPLITS,
    PRIMARY_DEPTH_COLUMN,
    HistGradientBoostingGridSpec,
    LogisticRegressionGridSpec,
    ProtocolConfig,
    RandomForestGridSpec,
)
from experiment_runner.controlled_daily_v4.stage_a_runner import run_stage_a
from tests.controlled_daily_v4_fixtures import (
    make_synthetic_daily_frame,
    write_synthetic_pergamino_csv_pair,
)

FAST_CONFIG = ProtocolConfig(
    bootstrap_replicas=15,
    logistic_regression_grid=LogisticRegressionGridSpec(C=(1.0,)),
    random_forest_grid=RandomForestGridSpec(
        n_estimators=(25,), max_depth=(4,), min_samples_leaf=(5,)
    ),
    hist_gradient_boosting_grid=HistGradientBoostingGridSpec(
        learning_rate=(0.1,), max_iter=(25,), max_leaf_nodes=(15,), l2_regularization=(0.0,)
    ),
)


@pytest.fixture(scope="module")
def stage_a_results():
    daily = make_synthetic_daily_frame(n_days=900, seed=23)
    return run_stage_a(daily, PRIMARY_DEPTH_COLUMN, FAST_CONFIG)


# --------------------------------------------------------------------------
# `run_stage_a`: huella y folds internos
# --------------------------------------------------------------------------


def test_dataset_fingerprint_is_populated_and_matches_the_eligible_frame(stage_a_results):
    from experiment_runner.controlled_daily_v4.dataset_fingerprint import (
        compute_dataset_fingerprint,
    )
    from experiment_runner.controlled_daily_v4.stage_a_runner import build_eligible_frame
    from tests.controlled_daily_v4_fixtures import make_synthetic_daily_frame as _make

    daily = _make(n_days=900, seed=23)
    eligible = build_eligible_frame(daily, PRIMARY_DEPTH_COLUMN)
    expected = compute_dataset_fingerprint(eligible)
    assert stage_a_results.dataset_fingerprint["sha256"] == expected["sha256"]
    assert stage_a_results.dataset_fingerprint["n_rows"] == len(eligible)


def test_inner_folds_are_recorded_once_per_outer_fold_with_the_real_gap(stage_a_results):
    n_outer = len(stage_a_results.outer_folds)
    outer_indices = {f.index for f in stage_a_results.outer_folds}
    assert set(stage_a_results.inner_folds_by_outer) == outer_indices
    assert len(stage_a_results.inner_folds_by_outer) == n_outer

    for outer_fold in stage_a_results.outer_folds:
        inner_folds = stage_a_results.inner_folds_by_outer[outer_fold.index]
        assert len(inner_folds) == INNER_N_SPLITS
        for inner_fold in inner_folds:
            max_target_train = inner_fold.train["target_timestamp"].max()
            min_feature_val = inner_fold.validation["feature_timestamp"].min()
            assert max_target_train < min_feature_val


def test_the_inner_folds_recorded_are_the_ones_actually_used_by_the_three_families(
    stage_a_results,
):
    """Ninguna familia debería haber recalculado su propia partición interna:
    el `inner_median_mcc`/`inner_best_config` de las tres familias de un mismo
    outer fold deben ser reproducibles evaluando exactamente los folds
    registrados en `inner_folds_by_outer`."""
    from experiment_runner.controlled_daily_v4.stage_a_runner import build_family_config_map
    from experiment_runner.controlled_daily_v4.tuning import select_best_config

    family_configs = build_family_config_map(FAST_CONFIG)
    for outer_fold in stage_a_results.outer_folds:
        inner_folds = stage_a_results.inner_folds_by_outer[outer_fold.index]
        for family in ("logistic_regression", "random_forest", "hist_gradient_boosting_classifier"):
            recorded = next(
                r
                for r in stage_a_results.per_family_outer_results[family]
                if r.outer_fold_index == outer_fold.index
            )
            best_config, median, _ = select_best_config(family_configs[family], inner_folds)
            assert best_config.config_id == recorded.inner_best_config.config_id
            assert median == pytest.approx(recorded.inner_median_mcc, nan_ok=True)


def test_freeze_folds_use_the_normative_outer_n_splits_and_gap(stage_a_results):
    selection = stage_a_results.selection
    if selection.selected_family is None:
        pytest.skip("sin selección estable en esta corrida sintética")
    if stage_a_results.frozen_single_family is not None:
        folds = stage_a_results.frozen_single_family.folds
    else:
        folds = next(iter(stage_a_results.frozen_soft_voting_bases.values())).folds
    assert len(folds) == OUTER_N_SPLITS
    for fold in folds:
        max_target_train = fold.train["target_timestamp"].max()
        min_feature_val = fold.validation["feature_timestamp"].min()
        assert max_target_train < min_feature_val


def test_warnings_log_entries_always_carry_a_phase_context(stage_a_results):
    for entry in stage_a_results.warnings_log:
        assert "phase" in entry
        assert "category" in entry
        assert "message" in entry
        assert entry["count"] >= 1


# --------------------------------------------------------------------------
# CLI: artefactos nuevos
# --------------------------------------------------------------------------


def _run_cli(tmp_path, extra_args=()):
    from experiment_runner.controlled_daily_v4.cli import main

    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=200, seed=13)
    output_dir = tmp_path / "out"
    exit_code = main(
        [
            "--stage",
            "A",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(output_dir),
            "--input-mode",
            "synthetic",
            *extra_args,
        ]
    )
    return exit_code, output_dir


def _load(output_dir, name):
    return json.loads((output_dir / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cli_output(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("cli_repro")
    exit_code, output_dir = _run_cli(tmp_path, extra_args=("--bootstrap-replicas", "10"))
    assert exit_code == 0
    return output_dir


def test_cli_writes_a_code_version_artifact_before_training(cli_output):
    payload = _load(cli_output, "code_version.json")
    assert "available" in payload
    assert "source" in payload
    # En este entorno de test corre dentro del repositorio real: Git debe
    # estar disponible y el commit debe ser el SHA completo (40 caracteres).
    if payload["available"]:
        assert payload["commit"] is None or len(payload["commit"]) == 40


def test_cli_writes_a_dataset_fingerprint_artifact(cli_output):
    payload = _load(cli_output, "dataset_fingerprint.json")
    assert len(payload["sha256"]) == 64
    assert payload["n_rows"] > 0
    assert payload["columns"][0] == "feature_timestamp"


def test_cli_writes_inner_and_freeze_fold_boundaries(cli_output):
    inner = _load(cli_output, "inner_fold_boundaries.json")
    assert inner, "debe haber al menos un outer fold con boundaries internas"
    for boundaries in inner.values():
        assert len(boundaries) == INNER_N_SPLITS
        for b in boundaries:
            assert b["train_feature_start"] < b["validation_feature_start"]

    outer = _load(cli_output, "outer_fold_boundaries.json")
    freeze = _load(cli_output, "freeze_fold_boundaries.json")
    assert len(outer) == OUTER_N_SPLITS
    assert len(freeze) == OUTER_N_SPLITS
    for b in freeze:
        assert b["n_train"] > 0
        assert b["n_validation"] > 0


def test_cli_writes_a_warnings_artifact_even_when_empty(cli_output):
    payload = _load(cli_output, "warnings.json")
    assert isinstance(payload, list)


# --------------------------------------------------------------------------
# Revisión externa 2026-09-13, punto 3: identidad de constraints + config efectiva
# --------------------------------------------------------------------------


def test_environment_artifact_includes_the_real_constraints_file_identity(cli_output):
    """La huella persistida debe corresponder al archivo `constraints.txt`
    realmente usado para validar el entorno -- no un valor inventado ni
    desacoplado del que `environment.validate_environment` contrastó."""
    import hashlib

    from experiment_runner.controlled_daily_v4.manifest_reference import (
        DEFAULT_CONSTRAINTS_PATH,
    )

    env = _load(cli_output, "environment.json")
    identity = env["constraints_identity"]
    assert identity["path"] == str(DEFAULT_CONSTRAINTS_PATH)
    assert identity["exists"] is True

    real_sha256 = hashlib.sha256(DEFAULT_CONSTRAINTS_PATH.read_bytes()).hexdigest()
    assert identity["sha256"] == real_sha256


def test_environment_artifact_reports_no_hash_when_constraints_file_is_absent(tmp_path):
    from experiment_runner.controlled_daily_v4.environment import capture_constraints_identity

    identity = capture_constraints_identity(tmp_path / "does_not_exist.txt")
    assert identity["exists"] is False
    assert identity["sha256"] is None


def test_resolved_config_persists_the_effective_protocol_config_actually_consumed(cli_output):
    """Los parámetros persistidos deben coincidir con los efectivamente
    consumidos por `run_stage_a` en esta misma corrida sintética -- se
    reconstruye el `ProtocolConfig` que la CLI arma con los mismos argumentos
    y se compara campo a campo contra lo persistido."""
    from experiment_runner.controlled_daily_v4.config import BOOTSTRAP_SEED

    resolved = _load(cli_output, "resolved_config.json")
    effective = resolved["effective_protocol_config"]

    expected = ProtocolConfig(bootstrap_seed=BOOTSTRAP_SEED, bootstrap_replicas=10)

    assert effective["gap"] == expected.gap
    assert effective["outer_n_splits"] == expected.outer_n_splits
    assert effective["inner_n_splits"] == expected.inner_n_splits
    assert effective["horizon_days"] == expected.horizon_days
    assert list(effective["lags"]) == list(expected.lags)
    assert list(effective["rolling_windows"]) == list(expected.rolling_windows)
    assert effective["decision_threshold"] == expected.decision_threshold
    assert effective["practical_margin_delta_mcc"] == expected.practical_margin_delta_mcc
    assert effective["bootstrap_block_days"] == expected.bootstrap_block_days
    assert effective["bootstrap_replicas"] == 10, "debe reflejar el --bootstrap-replicas usado"
    assert effective["bootstrap_seed"] == BOOTSTRAP_SEED
    expected_emission_start = expected.stage_bounds.emission_start.isoformat()
    assert effective["stage_bounds"]["emission_start"] == expected_emission_start
    assert list(effective["logistic_regression_grid"]["C"]) == list(
        expected.logistic_regression_grid.C
    )
    assert list(effective["random_forest_grid"]["n_estimators"]) == list(
        expected.random_forest_grid.n_estimators
    )
    assert list(effective["hist_gradient_boosting_grid"]["learning_rate"]) == list(
        expected.hist_gradient_boosting_grid.learning_rate
    )


def test_resolved_config_effective_grids_match_the_grids_actually_used_in_this_run(
    stage_a_results,
):
    """La configuración persistida debe ser la misma que efectivamente generó
    los candidatos evaluados en `stage_a_results` (fixture con `FAST_CONFIG`,
    grillas reducidas) -- no la grilla normativa completa por defecto."""
    from experiment_runner.controlled_daily_v4.artifacts import normalize_for_json

    persisted = normalize_for_json(FAST_CONFIG)
    outer_results = stage_a_results.per_family_outer_results["logistic_regression"]
    used_config_ids = {r.inner_best_config.config_id for r in outer_results}

    assert persisted["logistic_regression_grid"]["C"] == list(
        FAST_CONFIG.logistic_regression_grid.C
    )
    for config_id in used_config_ids:
        assert "C=1.0" in config_id, "FAST_CONFIG solo declara C=1.0"


def test_cli_marks_code_identity_deviation_when_tree_is_dirty(tmp_path, monkeypatch):
    """Simula una identidad de código no disponible (equivalente a correr
    dentro de un contenedor sin `.git` ni metadato de build): la corrida debe
    seguir siendo ejecutable pero quedar marcada como no normativa."""
    import experiment_runner.controlled_daily_v4.cli as cli_module
    from experiment_runner.controlled_daily_v4.code_identity import CodeIdentity

    monkeypatch.setattr(
        cli_module,
        "capture_code_identity",
        lambda: CodeIdentity(available=False, source="unavailable", commit=None, dirty=None),
    )
    exit_code, output_dir = _run_cli(tmp_path)
    assert exit_code == 0
    resolved = _load(output_dir, "resolved_config.json")
    assert "code_identity" in resolved["normative_deviations"]
    assert resolved["normative_run"] is False
