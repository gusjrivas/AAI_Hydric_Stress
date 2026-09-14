"""CLI explícita de las Etapas A y B de controlled_daily_v4_external_pergamino.

`--stage A` y `--stage B` (esta última reutilizando el candidato congelado por
una corrida previa de A vía `--producer-dir`). `--stage C` se rechaza
explícitamente (ledger del holdout y secuencia de apertura, Decisión 2,
pendiente -- ver `docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md`).
No expone ninguna ruta oculta al dataset formal de `controlled_daily_v3` ni a
ningún servidor MLflow — no registra nada en MLflow, no lo integra en
absoluto.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path
from typing import Any

from experiment_runner.controlled_daily_v4.admissibility import (
    StageBAdmissibilityError,
    check_stage_b_admissibility,
)
from experiment_runner.controlled_daily_v4.code_identity import capture_code_identity
from experiment_runner.controlled_daily_v4.config import (
    BOOTSTRAP_REPLICAS_DEFAULT,
    BOOTSTRAP_SEED,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
    INPUT_MODES,
    PRIMARY_DEPTH_COLUMN,
    SENSITIVITY_DEPTH_COLUMN,
    STAGE_A,
    STAGE_A_BOUNDS,
    STAGE_B,
    STAGE_B_BOUNDS,
    CalendarIntegrityError,
    ProtocolConfig,
    UnsupportedStageError,
    require_enabled_stage,
)
from experiment_runner.controlled_daily_v4.environment import (
    capture_constraints_identity,
    capture_environment,
    validate_environment,
)
from experiment_runner.controlled_daily_v4.manifest_reference import DEFAULT_CONSTRAINTS_PATH
from experiment_runner.controlled_daily_v4.provenance import validate_pergamino_provenance
from experiment_runner.controlled_daily_v4.stage_b_runner import (
    StageBTechnicalError,
    build_stage_b_training_frame,
)
from experiment_runner.controlled_daily_v4.transfer_contract import (
    TransferContractSchemaError,
    TransferContractValidationError,
    load_frozen_config_contract,
)

DEPTH_CHOICES = {"primary": PRIMARY_DEPTH_COLUMN, "sensitivity": SENSITIVITY_DEPTH_COLUMN}


def normative_deviations(
    seed: int,
    bootstrap_replicas: int,
    *,
    input_mode: str,
    environment_ok: bool,
    code_identity_ok: bool = True,
) -> list[str]:
    """Parámetros/condiciones que apartan la corrida de lo normativo.

    Una corrida con semilla, réplicas, modo de entrada no científico,
    entorno no validado, o identidad de código no verificable/modificada
    sigue siendo ejecutable (sirve para pruebas rápidas o desarrollo), pero
    queda marcada como no normativa en la evidencia para que no se confunda
    con la corrida real (hallazgo H-04: la condición normativa considera
    modo, validación de entradas, integridad temporal y entorno; la
    integridad temporal ya se exige de forma incondicional -- ver
    `features.validate_continuous_daily_calendar` -- por lo que llegar a
    este punto ya la satisface). `code_identity_ok` cubre el hallazgo H-05:
    es `False` cuando el SHA de código no pudo obtenerse de ninguna fuente,
    o cuando se obtuvo pero el árbol de trabajo está modificado."""
    deviations = []
    if seed != BOOTSTRAP_SEED:
        deviations.append("seed")
    if bootstrap_replicas != BOOTSTRAP_REPLICAS_DEFAULT:
        deviations.append("bootstrap_replicas")
    if input_mode != INPUT_MODE_SCIENTIFIC:
        deviations.append("input_mode")
    if not environment_ok:
        deviations.append("environment")
    if not code_identity_ok:
        deviations.append("code_identity")
    return deviations


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="controlled-daily-v4-stage-a",
        description="Runner de las Etapas A y B de controlled_daily_v4_external_pergamino. "
        "No implementa ni acepta la Etapa C.",
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["A", "B", "C"],
        help="'A' y 'B' están implementadas. 'C' se rechaza explícitamente.",
    )
    parser.add_argument(
        "--producer-dir",
        type=Path,
        default=None,
        help=(
            "Requerido con --stage B: directorio de salida de una corrida previa de la "
            "Etapa A (debe contener 'frozen_config.json' y su evidencia asociada)."
        ),
    )
    parser.add_argument(
        "--era5-csv", required=True, type=Path, help="Ruta al CSV horario ERA5-Land de Pergamino."
    )
    parser.add_argument(
        "--nasa-power-csv",
        required=True,
        type=Path,
        help="Ruta al CSV diario NASA POWER de Pergamino.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directorio explícito de salida de artefactos.",
    )
    parser.add_argument(
        "--depth",
        choices=list(DEPTH_CHOICES),
        default="primary",
        help="'primary' (0-7cm, principal) o 'sensitivity' (7-28cm, sin efecto en la selección).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=BOOTSTRAP_SEED,
        help="Semilla del bootstrap (default normativo).",
    )
    parser.add_argument(
        "--bootstrap-replicas",
        type=int,
        default=BOOTSTRAP_REPLICAS_DEFAULT,
        help="Réplicas del bootstrap (default normativo 5000; reducir solo para pruebas rápidas).",
    )
    parser.add_argument(
        "--validate-inputs-only",
        action="store_true",
        help="Valida provenance de los dos CSV y termina, sin entrenar nada.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite sobreescribir un directorio de salida no vacío.",
    )
    parser.add_argument(
        "--input-mode",
        choices=list(INPUT_MODES),
        default=INPUT_MODE_SCIENTIFIC,
        help=(
            "'scientific' (default): exige identidad de los CSV contra la referencia "
            "versionada del manifiesto y entorno validado contra constraints.txt antes de "
            "entrenar. 'synthetic': exclusivo de tests/desarrollo con fixtures -- nunca se "
            "activa automáticamente; toda salida producida en este modo queda marcada "
            "explícitamente como no científica."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        require_enabled_stage(args.stage)
    except UnsupportedStageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.stage == STAGE_B and args.producer_dir is None:
        print("ERROR: --stage B requiere --producer-dir explícito.", file=sys.stderr)
        return 2

    report = validate_pergamino_provenance(args.era5_csv, args.nasa_power_csv, mode=args.input_mode)
    if not report.ok:
        print("ERROR: validación de provenance/identidad falló:", file=sys.stderr)
        for issue in report.issues:
            print(f"  - {issue}", file=sys.stderr)
        return 3

    if args.validate_inputs_only:
        if args.input_mode == INPUT_MODE_SYNTHETIC:
            print("Provenance OK [NO CIENTÍFICO: --input-mode synthetic]. No se entrena nada.")
        else:
            print("Provenance OK. --validate-inputs-only: no se entrena nada.")
        return 0

    environment_info = capture_environment()
    environment_report = validate_environment(environment_info)
    # Identidad del archivo de referencia contrastado (hallazgo H-05, revisión
    # externa 2026-09-13, punto 3): persiste el SHA-256 de `constraints.txt`
    # junto con el resultado de validarlo, no solo el resultado — capturado
    # antes de entrenar, igual que el resto del entorno.
    constraints_identity = capture_constraints_identity(DEFAULT_CONSTRAINTS_PATH)
    if args.input_mode == INPUT_MODE_SCIENTIFIC and not environment_report.ok:
        print(
            "ERROR: validación de entorno falló (antes de ajustar ningún modelo):",
            file=sys.stderr,
        )
        for issue in environment_report.issues:
            print(f"  - {issue}", file=sys.stderr)
        return 4

    # Identidad de código (hallazgo H-05), capturada antes de entrenar, igual
    # que el entorno: nunca inventa un commit ni un estado limpio/modificado
    # si no puede determinarlos (ver `code_identity.capture_code_identity`).
    code_identity = capture_code_identity()
    code_identity_ok = code_identity.available and code_identity.dirty is False

    from experiment_runner.controlled_daily_v4 import artifacts
    from experiment_runner.controlled_daily_v4.features import compute_stage_window_bounds
    from experiment_runner.controlled_daily_v4.ingestion import (
        aggregate_era5_daily,
        build_daily_joined_series,
        load_era5_hourly_raw,
        load_nasa_power_daily_raw,
        replace_missing_sentinel,
        restrict_era5_hourly_to_window,
        restrict_nasa_power_daily_to_window,
    )
    from experiment_runner.controlled_daily_v4.stage_a_runner import run_stage_a

    if args.stage == STAGE_B:
        return _run_stage_b(
            args,
            report=report,
            environment_info=environment_info,
            environment_report=environment_report,
            code_identity=code_identity,
        )

    # Recorte a la ventana autorizada de la Etapa A (más la historia causal
    # mínima) ANTES de agregar humedad o convertir el centinela -- ningún
    # agregador ni procesador de valores recibe filas de fuera de esa
    # ventana (hallazgo H-03; antes se recortaba recién dentro del runner,
    # después de agregar/procesar el rango completo).
    window_start, window_end = compute_stage_window_bounds(STAGE_A_BOUNDS)

    _era5_meta, era5_df = load_era5_hourly_raw(args.era5_csv)
    era5_df = restrict_era5_hourly_to_window(era5_df, window_start, window_end)
    era5_daily = aggregate_era5_daily(era5_df)

    _nasa_meta, nasa_df = load_nasa_power_daily_raw(args.nasa_power_csv)
    nasa_df = restrict_nasa_power_daily_to_window(nasa_df, window_start, window_end)
    nasa_df = replace_missing_sentinel(nasa_df)

    daily_series = build_daily_joined_series(era5_daily, nasa_df)

    protocol_config = ProtocolConfig(
        bootstrap_seed=args.seed, bootstrap_replicas=args.bootstrap_replicas
    )
    depth_column = DEPTH_CHOICES[args.depth]
    try:
        results = run_stage_a(daily_series, depth_column, protocol_config)
    except CalendarIntegrityError as exc:
        print(
            "ERROR: integridad del calendario diario falló (no se entrenó nada):",
            file=sys.stderr,
        )
        print(f"  - {exc}", file=sys.stderr)
        return 5

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

    deviations = normative_deviations(
        args.seed,
        args.bootstrap_replicas,
        input_mode=args.input_mode,
        environment_ok=environment_report.ok,
        code_identity_ok=code_identity_ok,
    )
    # Única fuente de la bandera `scientific_run`: se calcula una vez aquí y
    # se reutiliza tanto en `resolved_config.json` como en el contrato de
    # transferencia A→B (`frozen_config.json`) -- nunca se duplica la lógica.
    scientific_run = report.scientific and not deviations

    written = artifacts.write_stage_a_artifacts(
        args.output_dir,
        depth_column=depth_column,
        input_mode=args.input_mode,
        scientific_run=scientific_run,
        resolved_config={
            "stage": STAGE_A,
            "seed": args.seed,
            "bootstrap_replicas": args.bootstrap_replicas,
            "input_mode": args.input_mode,
            "normative_seed": BOOTSTRAP_SEED,
            "normative_bootstrap_replicas": BOOTSTRAP_REPLICAS_DEFAULT,
            "normative_run": not deviations,
            "normative_deviations": deviations,
            "scientific_run": scientific_run,
            # Configuración experimental efectiva completa (hallazgo H-05,
            # revisión externa 2026-09-13, punto 3): el mismo objeto
            # `ProtocolConfig` pasado a `run_stage_a`, no una copia manual
            # mantenida aparte -- incluye fronteras temporales, horizonte,
            # gap, folds, lags, ventanas móviles, umbral, margen práctico,
            # parámetros de bootstrap y las tres grillas de hiperparámetros.
            # La CLI no expone forma de solicitar una configuración distinta
            # de esta (solo `--seed`/`--bootstrap-replicas` la parametrizan,
            # ya reflejados arriba): no existe hoy una divergencia posible
            # entre "solicitado" y "efectivamente consumido" más allá de esos
            # dos campos.
            "effective_protocol_config": protocol_config,
        },
        provenance_report=report,
        environment_info={
            **environment_info,
            "validation_issues": environment_report.issues,
            "validated_before_training": True,
            "constraints_identity": constraints_identity,
        },
        code_version=dataclasses.asdict(code_identity),
        input_hashes={
            "era5_sha256": report.era5_sha256,
            "nasa_power_sha256": report.nasa_power_sha256,
        },
        dataset_fingerprint=results.dataset_fingerprint,
        outer_fold_boundaries=outer_fold_boundaries,
        inner_fold_boundaries_by_outer=results.inner_folds_by_outer,
        per_family_outer_results=results.per_family_outer_results,
        oof_by_family=results.oof_by_family,
        selection_result=results.selection,
        frozen_single_family=results.frozen_single_family,
        frozen_soft_voting_bases=results.frozen_soft_voting_bases,
        final_p20_train=results.final_p20_train,
        final_estimator_details=results.final_estimator_details,
        soft_voting_combination_weights=results.soft_voting_combination_weights,
        warnings_log=results.warnings_log,
        overwrite=args.overwrite,
    )

    print(f"Etapa A completada. Artefactos escritos en: {args.output_dir}")
    print(f"Selección: {results.selection.outcome} -> {results.selection.selected_family}")
    for name, path in written.items():
        print(f"  {name}: {path}")
    return 0


def _run_stage_b(
    args: argparse.Namespace,
    *,
    report: Any,
    environment_info: dict,
    environment_report: Any,
    code_identity: Any,
) -> int:
    """Etapa B: reentrenamiento del candidato congelado por una corrida previa
    de A (`--producer-dir`) y compuerta temporal sobre 2023 (protocolo,
    sección 10). Nunca entrena nada antes de que la lectura estructural del
    contrato y la admisibilidad de esta ejecución concreta hayan sido
    verificadas -- ambas ocurren antes de tocar cualquier dato de humedad."""
    from experiment_runner.controlled_daily_v4 import artifacts
    from experiment_runner.controlled_daily_v4.features import compute_stage_window_bounds
    from experiment_runner.controlled_daily_v4.ingestion import (
        aggregate_era5_daily,
        build_daily_joined_series,
        load_era5_hourly_raw,
        load_nasa_power_daily_raw,
        replace_missing_sentinel,
        restrict_era5_hourly_to_window,
        restrict_nasa_power_daily_to_window,
    )
    from experiment_runner.controlled_daily_v4.stage_b_runner import run_stage_b

    try:
        contract = load_frozen_config_contract(args.producer_dir)
    except (TransferContractSchemaError, TransferContractValidationError) as exc:
        print(f"ERROR: contrato de transferencia A→B inválido: {exc}", file=sys.stderr)
        return 6

    # Ingesta recortada a la UNIÓN de la ventana de A (entrenamiento,
    # incluida su historia causal) y la ventana de B (evaluación 2023,
    # incluida su propia historia causal): ninguna fila de 2024-2025 llega
    # jamás a un agregador ni a un procesador de valores, sin importar qué
    # fechas traigan los CSV recibidos (hallazgo H-03, extendido a B).
    ingestion_window_start, _ = compute_stage_window_bounds(STAGE_A_BOUNDS)
    _, ingestion_window_end = compute_stage_window_bounds(STAGE_B_BOUNDS)

    _era5_meta, era5_df = load_era5_hourly_raw(args.era5_csv)
    era5_df = restrict_era5_hourly_to_window(era5_df, ingestion_window_start, ingestion_window_end)
    era5_daily = aggregate_era5_daily(era5_df)

    _nasa_meta, nasa_df = load_nasa_power_daily_raw(args.nasa_power_csv)
    nasa_df = restrict_nasa_power_daily_to_window(
        nasa_df, ingestion_window_start, ingestion_window_end
    )
    nasa_df = replace_missing_sentinel(nasa_df)

    daily_series = build_daily_joined_series(era5_daily, nasa_df)

    try:
        training_frame = build_stage_b_training_frame(daily_series, contract.depth_column)
    except CalendarIntegrityError as exc:
        print(
            "ERROR: integridad del calendario diario falló (no se entrenó nada):",
            file=sys.stderr,
        )
        print(f"  - {exc}", file=sys.stderr)
        return 5

    from experiment_runner.controlled_daily_v4.dataset_fingerprint import (
        compute_dataset_fingerprint,
    )

    consumer_training_dataset_fingerprint = compute_dataset_fingerprint(training_frame)
    consumer_code_identity = dataclasses.asdict(code_identity)

    try:
        check_stage_b_admissibility(
            contract,
            producer_dir=args.producer_dir,
            consumer_input_mode=args.input_mode,
            consumer_code_identity=consumer_code_identity,
            consumer_environment_issues=environment_report.issues,
            consumer_training_dataset_fingerprint=consumer_training_dataset_fingerprint,
        )
    except StageBAdmissibilityError as exc:
        print("ERROR: candidato no admisible para esta ejecución de la Etapa B:", file=sys.stderr)
        for reason in exc.reasons:
            print(f"  - {reason}", file=sys.stderr)
        return 7

    try:
        result = run_stage_b(
            contract,
            daily_series,
            bootstrap_replicas=args.bootstrap_replicas,
            bootstrap_seed=args.seed,
        )
    except StageBTechnicalError as exc:
        print(
            f"ERROR: fallo técnico de la Etapa B (no es un veredicto experimental): {exc}",
            file=sys.stderr,
        )
        return 8

    deviations = normative_deviations(
        args.seed,
        args.bootstrap_replicas,
        input_mode=args.input_mode,
        environment_ok=environment_report.ok,
        code_identity_ok=consumer_code_identity.get("available") is True
        and consumer_code_identity.get("dirty") is False,
    )
    scientific_run = (
        contract.scientific_run
        and report.scientific
        and not deviations
        and args.input_mode == INPUT_MODE_SCIENTIFIC
    )

    written = artifacts.write_stage_b_artifacts(
        args.output_dir,
        input_mode=args.input_mode,
        scientific_run=scientific_run,
        resolved_config={
            "stage": STAGE_B,
            "producer_dir": str(args.producer_dir),
            "seed": args.seed,
            "bootstrap_replicas": args.bootstrap_replicas,
            "normative_seed": BOOTSTRAP_SEED,
            "normative_bootstrap_replicas": BOOTSTRAP_REPLICAS_DEFAULT,
            "normative_run": not deviations,
            "normative_deviations": deviations,
        },
        producer_dir=args.producer_dir,
        producer_contract_raw=contract.raw,
        consumer_code_identity=consumer_code_identity,
        consumer_environment_info=environment_info,
        consumer_environment_issues=environment_report.issues,
        result=result,
        overwrite=args.overwrite,
    )

    print(f"Etapa B completada. Artefactos escritos en: {args.output_dir}")
    print(f"Veredicto: {result.verdict} (motivos: {result.verdict_reasons or 'ninguno'})")
    if not scientific_run:
        print("[NO CIENTÍFICO] Esta corrida de Etapa B no habilita la Etapa C.")
    for name, path in written.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
