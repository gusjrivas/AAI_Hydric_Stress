"""Integración sintética de punta a punta: A -> contrato -> B -> ledger -> C,
mediante la CLI real y el ledger real (SQLite en disco, nunca mockeado).

Nunca lee datos reales de Pergamino/Balcarce/holdout. Usa exclusivamente
fixtures sintéticas. El productor A y la corrida B de estos tests se
construyen con `--input-mode synthetic` (`scientific_run=False`), consumidos
por una Etapa C también sintética, con su propio ledger sintético aislado:
ninguna ejecución de este archivo se presenta ni puede presentarse como
apertura científica real del holdout."""

from __future__ import annotations

import json

from experiment_runner.controlled_daily_v4 import artifacts, holdout_ledger
from experiment_runner.controlled_daily_v4.cli import main
from experiment_runner.controlled_daily_v4.config import (
    HOLDOUT_SITE,
    INPUT_MODE_SYNTHETIC,
    PRIMARY_DEPTH_COLUMN,
    PROTOCOL_ID,
    STAGE_C_BOUNDS,
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
from tests.controlled_daily_v4_fixtures import (
    make_synthetic_daily_frame,
    write_synthetic_era5_csv,
    write_synthetic_nasa_power_csv,
    write_synthetic_pergamino_csv_pair,
)

_N_DAYS_THROUGH_2025 = 4018
"""2015-01-01 .. 2025-12-31: el mínimo necesario para que A, B y el holdout de
C (2024-2025) queden todos cubiertos."""

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


def _write_synthetic_producer_dir(tmp_path, era5_path, nasa_path, name="producer_a"):
    daily_series = _daily_series_from_csv(era5_path, nasa_path)
    results = run_stage_a(daily_series, PRIMARY_DEPTH_COLUMN, FAST_CONFIG)
    assert (
        results.selection.selected_family is not None
    ), "fixture determinista esperaba un candidato congelado; ajustar semilla/tamaño si falla"
    producer_dir = tmp_path / name
    artifacts.write_stage_a_artifacts(
        producer_dir,
        depth_column=PRIMARY_DEPTH_COLUMN,
        input_mode=INPUT_MODE_SYNTHETIC,
        scientific_run=False,
        resolved_config={"stage": "A", "note": "fixture de integración C, sintético"},
        provenance_report=ProvenanceReport(
            era5_path=str(era5_path), nasa_power_path=str(nasa_path), mode=INPUT_MODE_SYNTHETIC
        ),
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
        code_version={"available": False, "source": "unavailable", "commit": None, "dirty": None},
        dataset_fingerprint=results.dataset_fingerprint,
        final_estimator_details=results.final_estimator_details,
        soft_voting_combination_weights=results.soft_voting_combination_weights,
        warnings_log=results.warnings_log,
    )
    return producer_dir


def _run_stage_b_cli(era5, nasa, producer_dir, output_dir):
    exit_code = main(
        [
            "--stage",
            "B",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(output_dir),
            "--producer-dir",
            str(producer_dir),
            "--input-mode",
            "synthetic",
            "--bootstrap-replicas",
            "20",
        ]
    )
    return exit_code


def _init_ledger(tmp_path, name="holdout_ledger.sqlite3"):
    ledger_path = tmp_path / name
    from experiment_runner.controlled_daily_v4.holdout_ledger import compute_holdout_identity_key

    holdout_key = compute_holdout_identity_key(
        protocol_id=PROTOCOL_ID,
        site=HOLDOUT_SITE,
        depth_column=PRIMARY_DEPTH_COLUMN,
        period_start=str(STAGE_C_BOUNDS.target_start),
        period_end=str(STAGE_C_BOUNDS.target_end),
    )
    holdout_ledger.init_ledger(
        ledger_path, mode=holdout_ledger.LEDGER_MODE_SYNTHETIC, holdout_key=holdout_key
    )
    return ledger_path, holdout_key


def _run_stage_c_cli(
    *, era5, nasa, producer_dir, stage_b_dir, ledger_path, output_dir, authorized_by="tester"
):
    return main(
        [
            "--stage",
            "C",
            "--era5-csv",
            str(era5),
            "--nasa-power-csv",
            str(nasa),
            "--output-dir",
            str(output_dir),
            "--producer-dir",
            str(producer_dir),
            "--stage-b-dir",
            str(stage_b_dir),
            "--holdout-ledger-path",
            str(ledger_path),
            "--authorized-by",
            authorized_by,
            "--input-mode",
            "synthetic",
            "--bootstrap-replicas",
            "20",
        ]
    )


def test_end_to_end_synthetic_a_to_b_to_c_full_flow(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(
        tmp_path, n_days=_N_DAYS_THROUGH_2025, seed=2025
    )
    producer_dir = _write_synthetic_producer_dir(tmp_path, era5, nasa)

    stage_b_out = tmp_path / "stage_b_out"
    assert _run_stage_b_cli(era5, nasa, producer_dir, stage_b_out) == 0
    decision = json.loads((stage_b_out / "decision.json").read_text(encoding="utf-8"))

    ledger_path, holdout_key = _init_ledger(tmp_path)
    stage_c_out = tmp_path / "stage_c_out"

    exit_code = _run_stage_c_cli(
        era5=era5,
        nasa=nasa,
        producer_dir=producer_dir,
        stage_b_dir=stage_b_out,
        ledger_path=ledger_path,
        output_dir=stage_c_out,
    )

    if decision["verdict"] != "CANDIDATE_VALIDATED":
        # Fixture determinista puede o no validar en B; si no valida, C debe
        # rechazarse sin tocar el holdout -- se ejercita en un test dedicado.
        assert exit_code == 7
        return

    assert exit_code == 0, "esperaba éxito de la Etapa C tras CANDIDATE_VALIDATED"
    assert (stage_c_out / "predictions_2024_2025.csv").exists()
    assert (stage_c_out / "outcome.json").exists()
    outcome = json.loads((stage_c_out / "outcome.json").read_text(encoding="utf-8"))
    assert "verdict" not in outcome

    state = holdout_ledger.read_holdout_state(
        ledger_path, holdout_key, expected_mode=holdout_ledger.LEDGER_MODE_SYNTHETIC
    )
    assert state.state == holdout_ledger.STATE_CONFIRMED
    assert state.finalized
    assert state.finalized_result_reference == str(stage_c_out)


def test_stage_c_rejects_when_b_not_validated_without_touching_holdout(tmp_path, monkeypatch):
    """Fuerza CANDIDATE_NOT_VALIDATED con humedad de 2023 fijada (mismo
    mecanismo que el hallazgo 2 de la Etapa B), y verifica con un espía que
    la Etapa C nunca llega a leer los CSV (ni siquiera para provenance)."""
    daily_frame = make_synthetic_daily_frame(n_days=_N_DAYS_THROUGH_2025, seed=2025)
    mask_2023 = (daily_frame.index >= "2023-01-01") & (daily_frame.index <= "2023-12-31")
    daily_frame.loc[mask_2023, "soil_moisture_0_to_7cm"] = 0.9

    era5 = tmp_path / "pergamino_era5land_soil_hourly_2015_2025.csv"
    nasa = tmp_path / "pergamino_nasa_power_daily_2015_2025.csv"
    write_synthetic_era5_csv(era5, daily_frame)
    write_synthetic_nasa_power_csv(nasa, daily_frame)

    producer_dir = _write_synthetic_producer_dir(tmp_path, era5, nasa)
    stage_b_out = tmp_path / "stage_b_out"
    assert _run_stage_b_cli(era5, nasa, producer_dir, stage_b_out) == 0
    decision = json.loads((stage_b_out / "decision.json").read_text(encoding="utf-8"))
    assert decision["verdict"] == "CANDIDATE_NOT_VALIDATED"

    ledger_path, holdout_key = _init_ledger(tmp_path)
    stage_c_out = tmp_path / "stage_c_out"

    import experiment_runner.controlled_daily_v4.ingestion as ingestion_module

    def _spy(*_a, **_k):
        raise AssertionError("La Etapa C no debía leer ningún CSV: B no validó")

    monkeypatch.setattr(ingestion_module, "load_era5_hourly_raw", _spy)

    exit_code = _run_stage_c_cli(
        era5=era5,
        nasa=nasa,
        producer_dir=producer_dir,
        stage_b_dir=stage_b_out,
        ledger_path=ledger_path,
        output_dir=stage_c_out,
    )
    assert exit_code == 7
    assert not stage_c_out.exists()

    state = holdout_ledger.read_holdout_state(
        ledger_path, holdout_key, expected_mode=holdout_ledger.LEDGER_MODE_SYNTHETIC
    )
    assert state.state == holdout_ledger.STATE_ABSENT


def _write_forced_validated_stage_b_dir(stage_b_out, producer_dir):
    """Escribe directamente un `stage_b_dir` con `CANDIDATE_VALIDATED`
    persistido, en vez de depender de que la fixture aleatoria de B valide
    con una semilla dada (evita tests intermitentes). El linaje hasta A es
    REAL: `producer_frozen_config` es el `frozen_config.json` de A leído en
    disco -- la admisibilidad de C revalida ese linaje igual que en
    producción, solo el resultado experimental de B queda fijado a mano,
    exactamente como en `test_controlled_daily_v4_stage_c_admissibility.py`."""
    from experiment_runner.controlled_daily_v4.artifacts import STAGE_B_ARTIFACT_SCHEMA_VERSION

    stage_b_out.mkdir(parents=True, exist_ok=True)
    frozen_config_raw = json.loads(
        (producer_dir / "frozen_config.json").read_text(encoding="utf-8")
    )
    (stage_b_out / "schema_version.json").write_text(
        json.dumps({"schema_version": STAGE_B_ARTIFACT_SCHEMA_VERSION}), encoding="utf-8"
    )
    (stage_b_out / "resolved_config.json").write_text(
        json.dumps({"scientific_run": False}), encoding="utf-8"
    )
    (stage_b_out / "decision.json").write_text(
        json.dumps({"verdict": "CANDIDATE_VALIDATED", "predictions_available": True}),
        encoding="utf-8",
    )
    (stage_b_out / "metrics.json").write_text(
        json.dumps({"mcc_candidate": {"value": 0.4, "status": "defined"}}), encoding="utf-8"
    )
    (stage_b_out / "bootstrap.json").write_text(
        json.dumps({"bootstrap_executed": True, "interval_lower": 0.0}), encoding="utf-8"
    )
    (stage_b_out / "producer_reference.json").write_text(
        json.dumps(
            {"producer_dir": str(producer_dir), "producer_frozen_config": frozen_config_raw}
        ),
        encoding="utf-8",
    )


def _run_validated_stage_c_once(tmp_path, seed=4242):
    """Flujo A->C completo, con un `stage_b_dir` de B forzado a
    `CANDIDATE_VALIDATED` (ver `_write_forced_validated_stage_b_dir`) para no
    depender de la aleatoriedad de la fixture sintética."""
    era5, nasa = write_synthetic_pergamino_csv_pair(
        tmp_path, n_days=_N_DAYS_THROUGH_2025, seed=seed
    )
    producer_dir = _write_synthetic_producer_dir(tmp_path, era5, nasa)
    stage_b_out = tmp_path / "stage_b_out"
    _write_forced_validated_stage_b_dir(stage_b_out, producer_dir)

    ledger_path, holdout_key = _init_ledger(tmp_path)
    stage_c_out = tmp_path / "stage_c_out"
    exit_code = _run_stage_c_cli(
        era5=era5,
        nasa=nasa,
        producer_dir=producer_dir,
        stage_b_dir=stage_b_out,
        ledger_path=ledger_path,
        output_dir=stage_c_out,
    )
    assert exit_code == 0
    return {
        "era5": era5,
        "nasa": nasa,
        "producer_dir": producer_dir,
        "stage_b_out": stage_b_out,
        "ledger_path": ledger_path,
        "holdout_key": holdout_key,
        "stage_c_out": stage_c_out,
    }


def test_second_evaluation_with_different_output_dir_is_blocked(tmp_path, monkeypatch):
    ctx = _run_validated_stage_c_once(tmp_path)

    import experiment_runner.controlled_daily_v4.stage_c_runner as stage_c_runner_module

    def _spy(*_a, **_k):
        raise AssertionError("run_stage_c no debía invocarse: el holdout ya está protegido")

    monkeypatch.setattr(stage_c_runner_module, "run_stage_c", _spy)

    other_output = tmp_path / "stage_c_out_retry_different_dir"
    exit_code = _run_stage_c_cli(
        era5=ctx["era5"],
        nasa=ctx["nasa"],
        producer_dir=ctx["producer_dir"],
        stage_b_dir=ctx["stage_b_out"],
        ledger_path=ctx["ledger_path"],
        output_dir=other_output,
    )
    # Recuperación de solo lectura del resultado ya finalizado (exit 0), o
    # rechazo explícito si por algún motivo no está finalizado -- en ningún
    # caso se reevalúa (el espía habría lanzado AssertionError, que pytest
    # habría propagado como fallo de la corrida CLI, no como exit_code).
    assert exit_code == 0
    assert not other_output.exists()


def test_recovery_reads_existing_finalized_result_without_retraining(tmp_path, monkeypatch):
    ctx = _run_validated_stage_c_once(tmp_path)

    import experiment_runner.controlled_daily_v4.stage_c_runner as stage_c_runner_module

    def _spy(*_a, **_k):
        raise AssertionError("La recuperación no debía reentrenar")

    monkeypatch.setattr(stage_c_runner_module, "run_stage_c", _spy)

    exit_code = _run_stage_c_cli(
        era5=ctx["era5"],
        nasa=ctx["nasa"],
        producer_dir=ctx["producer_dir"],
        stage_b_dir=ctx["stage_b_out"],
        ledger_path=ctx["ledger_path"],
        output_dir=tmp_path / "stage_c_out_recovered_pointer",
    )
    assert exit_code == 0


def test_overwrite_is_rejected_unconditionally_for_stage_c(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=_N_DAYS_THROUGH_2025, seed=7)
    producer_dir = _write_synthetic_producer_dir(tmp_path, era5, nasa)
    stage_b_out = tmp_path / "stage_b_out"
    _run_stage_b_cli(era5, nasa, producer_dir, stage_b_out)
    ledger_path, _ = _init_ledger(tmp_path)

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
            "--producer-dir",
            str(producer_dir),
            "--stage-b-dir",
            str(stage_b_out),
            "--holdout-ledger-path",
            str(ledger_path),
            "--authorized-by",
            "tester",
            "--input-mode",
            "synthetic",
            "--overwrite",
        ]
    )
    assert exit_code == 2


def test_output_dir_conflicting_with_producer_dir_is_rejected(tmp_path, monkeypatch):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=_N_DAYS_THROUGH_2025, seed=7)
    producer_dir = _write_synthetic_producer_dir(tmp_path, era5, nasa)
    stage_b_out = tmp_path / "stage_b_out"
    _run_stage_b_cli(era5, nasa, producer_dir, stage_b_out)
    ledger_path, _ = _init_ledger(tmp_path)

    import experiment_runner.controlled_daily_v4.ingestion as ingestion_module

    def _spy(*_a, **_k):
        raise AssertionError("no debía leerse ningún CSV: conflicto de directorios")

    monkeypatch.setattr(ingestion_module, "load_era5_hourly_raw", _spy)

    exit_code = _run_stage_c_cli(
        era5=era5,
        nasa=nasa,
        producer_dir=producer_dir,
        stage_b_dir=stage_b_out,
        ledger_path=ledger_path,
        output_dir=producer_dir,
    )
    assert exit_code == 9


def test_absent_ledger_and_missing_authorization_are_rejected_before_data_access(
    tmp_path, monkeypatch
):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=_N_DAYS_THROUGH_2025, seed=7)
    producer_dir = _write_synthetic_producer_dir(tmp_path, era5, nasa)
    stage_b_out = tmp_path / "stage_b_out"
    _run_stage_b_cli(era5, nasa, producer_dir, stage_b_out)

    import experiment_runner.controlled_daily_v4.ingestion as ingestion_module

    def _spy(*_a, **_k):
        raise AssertionError("no debía leerse ningún CSV sin --authorized-by")

    monkeypatch.setattr(ingestion_module, "load_era5_hourly_raw", _spy)

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
            "--producer-dir",
            str(producer_dir),
            "--stage-b-dir",
            str(stage_b_out),
            "--holdout-ledger-path",
            str(tmp_path / "never_initialized_ledger.sqlite3"),
            "--input-mode",
            "synthetic",
        ]
    )
    assert exit_code == 2


def test_ledger_never_initialized_is_indeterminate_and_rejected_before_data_access(
    tmp_path, monkeypatch
):
    """Un ledger nunca inicializado se lee como INDETERMINADA (nunca como
    AUSENTE) y bloquea el acceso, sin siquiera intentar reservar."""
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=_N_DAYS_THROUGH_2025, seed=7)
    producer_dir = _write_synthetic_producer_dir(tmp_path, era5, nasa)
    stage_b_out = tmp_path / "stage_b_out"
    _run_stage_b_cli(era5, nasa, producer_dir, stage_b_out)

    import experiment_runner.controlled_daily_v4.cli as cli_module
    import experiment_runner.controlled_daily_v4.ingestion as ingestion_module

    def _spy(*_a, **_k):
        raise AssertionError("no debía leerse ningún CSV: ledger nunca inicializado")

    monkeypatch.setattr(ingestion_module, "load_era5_hourly_raw", _spy)
    # Aísla específicamente el paso del ledger de la admisibilidad de B (que
    # esta fixture determinista puede o no validar, según la semilla): el
    # objetivo de este test es el ledger, ya cubierto por separado para la
    # admisibilidad en test_controlled_daily_v4_stage_c_admissibility.py.
    monkeypatch.setattr(cli_module, "check_stage_c_admissibility", lambda *a, **k: None)

    exit_code = _run_stage_c_cli(
        era5=era5,
        nasa=nasa,
        producer_dir=producer_dir,
        stage_b_dir=stage_b_out,
        ledger_path=tmp_path / "never_initialized_ledger.sqlite3",
        output_dir=tmp_path / "stage_c_out",
    )
    assert exit_code == 11
