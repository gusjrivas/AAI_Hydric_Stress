"""Integración del runner con los artefactos corregidos.

Cubre el diagnóstico por outer fold poblado (§8.4), la serialización de las
configuraciones y modos de balanceo del Soft Voting (§7.5), la captura real
del entorno (§15) y el marcado explícito de una corrida no normativa.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from experiment_runner.controlled_daily_v4.config import (
    BOOTSTRAP_REPLICAS_DEFAULT,
    BOOTSTRAP_SEED,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_SOFT_VOTING,
    PRIMARY_DEPTH_COLUMN,
    WEIGHTING_MODES,
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
    daily = make_synthetic_daily_frame(n_days=900, seed=17)
    return run_stage_a(daily, PRIMARY_DEPTH_COLUMN, FAST_CONFIG)


def test_per_fold_mcc_is_populated_for_every_candidate(stage_a_results):
    n_outer = len(stage_a_results.outer_folds)
    for family, oof in stage_a_results.oof_by_family.items():
        assert oof.per_fold_mcc, f"{family} quedó sin diagnóstico por fold"
        assert len(oof.per_fold_mcc) == n_outer, family


def test_per_fold_mcc_matches_the_mcc_of_each_outer_fold(stage_a_results):
    from experiment_runner.controlled_daily_v4.metrics import mcc_strict

    for family, oof in stage_a_results.oof_by_family.items():
        results = stage_a_results.per_family_outer_results[family]
        expected = [mcc_strict(r.y_true, r.y_pred) for r in results]
        np.testing.assert_allclose(oof.per_fold_mcc, expected, equal_nan=True, err_msg=family)


def test_soft_voting_outer_results_record_their_base_configurations(stage_a_results):
    for result in stage_a_results.per_family_outer_results[FAMILY_SOFT_VOTING]:
        assert result.soft_voting_base_config_ids, "faltan los config_id de las bases"
        assert set(result.soft_voting_base_config_ids) == {
            "logistic_regression",
            "random_forest",
            "hist_gradient_boosting_classifier",
        }
        modes = result.soft_voting_base_weighting_modes
        assert set(modes) == set(result.soft_voting_base_config_ids)
        for mode in modes.values():
            assert mode in WEIGHTING_MODES


def test_soft_voting_base_configs_are_the_ones_selected_inside_the_outer_train(stage_a_results):
    """El Soft Voting de cada outer se compone exactamente con las
    configuraciones ganadoras del tuning inner de ese mismo outer."""
    for index, result in enumerate(stage_a_results.per_family_outer_results[FAMILY_SOFT_VOTING]):
        for family in result.soft_voting_base_config_ids:
            expected = stage_a_results.per_family_outer_results[family][index].inner_best_config
            assert result.soft_voting_base_config_ids[family] == expected.config_id
            assert result.soft_voting_base_weighting_modes[family] == expected.params["weighting"]


def test_final_estimator_details_record_effective_l2_regularization(stage_a_results):
    details = stage_a_results.final_estimator_details
    if stage_a_results.selection.selected_family is None:
        assert details is None or details == {}
        return
    assert details, "el congelamiento debe registrar detalles del estimador final"
    for family, block in details.items():
        assert block["estimator_class"], family
        if family == FAMILY_LOGISTIC_REGRESSION:
            assert block["effective_regularization"] == "l2"
            assert block["matches_protocol_l2"] is True
            assert block["l1_ratio"] == pytest.approx(0.0)
        else:
            # Constancia de que el balanceo nunca usa `class_weight`
            # (protocolo, sección 7.1).
            assert block["effective_params"].get("class_weight") is None, family


# --------------------------------------------------------------------------
# CLI
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
    def reject(constant):
        raise AssertionError(f"constante JSON no estándar: {constant}")

    return json.loads((output_dir / name).read_text(encoding="utf-8"), parse_constant=reject)


@pytest.fixture(scope="module")
def cli_output(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("cli_normative")
    exit_code, output_dir = _run_cli(tmp_path, extra_args=("--bootstrap-replicas", "10"))
    assert exit_code == 0
    return output_dir


def test_cli_writes_a_metrics_artifact(cli_output):
    payload = _load(cli_output, "metrics.json")
    assert payload["by_family"], "metrics.json debe reportar los candidatos"
    for family, block in payload["by_family"].items():
        assert block["global"]["mcc"]["status"] in ("defined", "undefined"), family
        assert block["per_outer_fold"], family
        assert block["fold_mcc_summary"]["per_fold"], family


def test_cli_captures_the_real_environment_not_a_placeholder(cli_output):
    import sklearn

    env = _load(cli_output, "environment.json")
    assert env["packages"]["scikit-learn"] == sklearn.__version__
    assert env["python_version"].startswith("3.")
    assert "completar" not in json.dumps(env)


def test_cli_marks_a_run_with_reduced_replicas_as_non_normative(cli_output):
    resolved = _load(cli_output, "resolved_config.json")
    assert resolved["bootstrap_replicas"] == 10
    assert resolved["normative_run"] is False
    assert "bootstrap_replicas" in resolved["normative_deviations"]


def test_protocol_defaults_record_no_normative_deviation():
    """Con la semilla y las réplicas normativas no se registra desviación.

    Se prueba la regla directamente en lugar de correr el CLI con las 5.000
    réplicas normativas, que no aporta nada a esta aserción y cuesta minutos.
    """
    from experiment_runner.controlled_daily_v4.cli import normative_deviations
    from experiment_runner.controlled_daily_v4.config import INPUT_MODE_SCIENTIFIC

    kwargs = {"input_mode": INPUT_MODE_SCIENTIFIC, "environment_ok": True}
    assert normative_deviations(BOOTSTRAP_SEED, BOOTSTRAP_REPLICAS_DEFAULT, **kwargs) == []
    assert normative_deviations(BOOTSTRAP_SEED, 10, **kwargs) == ["bootstrap_replicas"]
    assert normative_deviations(1234, BOOTSTRAP_REPLICAS_DEFAULT, **kwargs) == ["seed"]
    assert normative_deviations(1234, 10, **kwargs) == ["seed", "bootstrap_replicas"]

    assert normative_deviations(
        BOOTSTRAP_SEED, BOOTSTRAP_REPLICAS_DEFAULT, input_mode="synthetic", environment_ok=True
    ) == ["input_mode"]
    assert normative_deviations(
        BOOTSTRAP_SEED,
        BOOTSTRAP_REPLICAS_DEFAULT,
        input_mode=INPUT_MODE_SCIENTIFIC,
        environment_ok=False,
    ) == ["environment"]


def test_cli_records_the_schema_version_of_the_current_artifacts(cli_output):
    from experiment_runner.controlled_daily_v4.artifacts import ARTIFACT_SCHEMA_VERSION

    assert _load(cli_output, "schema_version.json")["schema_version"] == ARTIFACT_SCHEMA_VERSION


def test_cli_serializes_soft_voting_base_configurations(cli_output):
    payload = _load(cli_output, "hyperparameters_inner_selected.json")
    soft = payload[FAMILY_SOFT_VOTING]
    assert soft, "el Soft Voting debe aparecer en el artefacto de hiperparámetros"
    for entry in soft:
        assert entry["soft_voting_base_config_ids"]
        assert entry["soft_voting_base_weighting_modes"]


def test_cli_selection_decision_records_bootstrap_provenance(cli_output):
    decision = _load(cli_output, "selection_decision.json")
    if decision["outcome"] == "NO_VALID_SELECTION":
        pytest.skip("sin comparación pareada cuando el OOF es monoclase")
    assert decision["bootstrap_diagnostics"], "faltan las diagnósticas del bootstrap"
    for diagnostics in decision["bootstrap_diagnostics"].values():
        assert diagnostics["block_length"] == 30
        assert diagnostics["replicas_requested"] == 10
        assert diagnostics["segment_sizes"]
        assert diagnostics["normative"] is True
