"""CLI explícita de las Etapas A, B y C de controlled_daily_v4_external_pergamino.

`--stage A`, `--stage B` (reutiliza el candidato congelado por una corrida
previa de A vía `--producer-dir`) y `--stage C` (holdout final 2024-2025,
condicionado a un veredicto `CANDIDATE_VALIDATED` persistido de B, protegido
por el ledger transaccional de `holdout_ledger.py` -- Decisiones 2 y 3,
adoptadas como decisiones operativas de este encargo, ver
`docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md`).
`--init-holdout-ledger` inicializa explícitamente el ledger, como operación
separada de cualquier ejecución. No expone ninguna ruta oculta al dataset
formal de `controlled_daily_v3` ni a ningún servidor MLflow — no registra
nada en MLflow, no lo integra en absoluto.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path
from typing import Any

from experiment_runner.controlled_daily_v4 import holdout_ledger
from experiment_runner.controlled_daily_v4.admissibility import (
    StageBAdmissibilityError,
    StageCAdmissibilityError,
    check_stage_b_admissibility,
    check_stage_c_admissibility,
)
from experiment_runner.controlled_daily_v4.code_identity import capture_code_identity
from experiment_runner.controlled_daily_v4.config import (
    BOOTSTRAP_REPLICAS_DEFAULT,
    BOOTSTRAP_SEED,
    HOLDOUT_SITE,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
    INPUT_MODES,
    PRIMARY_DEPTH_COLUMN,
    PROTOCOL_ID,
    SENSITIVITY_DEPTH_COLUMN,
    STAGE_A,
    STAGE_A_BOUNDS,
    STAGE_B,
    STAGE_B_BOUNDS,
    STAGE_C,
    STAGE_C_BOUNDS,
    STAGE_C_TRAINING_BOUNDS,
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
        description="Runner de las Etapas A, B y C de controlled_daily_v4_external_pergamino.",
    )
    parser.add_argument(
        "--stage",
        required=False,
        default=None,
        choices=["A", "B", "C"],
        help="'A', 'B' y 'C' están implementadas. No requerido con --init-holdout-ledger.",
    )
    parser.add_argument(
        "--producer-dir",
        type=Path,
        default=None,
        help=(
            "Requerido con --stage B y --stage C: directorio de salida de una corrida previa "
            "de la Etapa A (debe contener 'frozen_config.json' y su evidencia asociada)."
        ),
    )
    parser.add_argument(
        "--stage-b-dir",
        type=Path,
        default=None,
        help=(
            "Requerido con --stage C: directorio de salida de una corrida previa de la "
            "Etapa B con veredicto CANDIDATE_VALIDATED persistido."
        ),
    )
    parser.add_argument(
        "--holdout-ledger-path",
        type=Path,
        default=None,
        help=(
            "Requerido con --stage C y con --init-holdout-ledger: ruta explícita y persistente "
            "del ledger SQLite de protección del holdout (fuera de cualquier --output-dir). "
            "En Docker debe apuntar a un volumen persistente compartido por todas las "
            "ejecuciones que protegen el mismo holdout."
        ),
    )
    parser.add_argument(
        "--init-holdout-ledger",
        action="store_true",
        help=(
            "Inicializa explícitamente el ledger en --holdout-ledger-path (con --input-mode "
            "determinando su modo synthetic/scientific) y termina, sin entrenar nada. Rechaza "
            "reemplazar un ledger ya existente. Operación separada de --stage C."
        ),
    )
    parser.add_argument(
        "--authorized-by",
        default=None,
        help=(
            "Requerido con --stage C: nombre/rol de quien autoriza la apertura del holdout "
            "(protocolo, sección 11). Sin valor por defecto."
        ),
    )
    parser.add_argument(
        "--era5-csv", type=Path, default=None, help="Ruta al CSV horario ERA5-Land de Pergamino."
    )
    parser.add_argument(
        "--nasa-power-csv",
        type=Path,
        default=None,
        help="Ruta al CSV diario NASA POWER de Pergamino.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
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
        help=(
            "Permite sobreescribir un directorio de salida no vacío en A/B. Prohibido "
            "incondicionalmente con --stage C (Decisión 3, adoptada para este encargo: "
            "defensa en profundidad sobre el ledger, sin excepción)."
        ),
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

    if args.init_holdout_ledger:
        # Inicialización EXPLÍCITA y SEPARADA de cualquier ejecución
        # (documento de decisiones, Decisión 2): no requiere CSV ni
        # --output-dir. Nunca reemplaza un ledger existente.
        if args.holdout_ledger_path is None:
            print(
                "ERROR: --init-holdout-ledger requiere --holdout-ledger-path explícito.",
                file=sys.stderr,
            )
            return 2
        ledger_mode = (
            holdout_ledger.LEDGER_MODE_SCIENTIFIC
            if args.input_mode == INPUT_MODE_SCIENTIFIC
            else holdout_ledger.LEDGER_MODE_SYNTHETIC
        )
        depth_column = DEPTH_CHOICES[args.depth]
        holdout_key = holdout_ledger.compute_holdout_identity_key(
            protocol_id=PROTOCOL_ID,
            site=HOLDOUT_SITE,
            depth_column=depth_column,
            period_start=str(STAGE_C_BOUNDS.target_start),
            period_end=str(STAGE_C_BOUNDS.target_end),
        )
        try:
            holdout_ledger.init_ledger(
                args.holdout_ledger_path, mode=ledger_mode, holdout_key=holdout_key
            )
        except holdout_ledger.HoldoutLedgerAlreadyInitializedError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 10
        print(
            f"Ledger inicializado en {args.holdout_ledger_path} (mode={ledger_mode}, "
            f"holdout_key={holdout_key})."
        )
        return 0

    if args.stage is None:
        print("ERROR: --stage es requerido (salvo con --init-holdout-ledger).", file=sys.stderr)
        return 2

    try:
        require_enabled_stage(args.stage)
    except UnsupportedStageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.stage == STAGE_B and args.producer_dir is None:
        print("ERROR: --stage B requiere --producer-dir explícito.", file=sys.stderr)
        return 2

    if args.stage == STAGE_C:
        missing = [
            name
            for name, value in (
                ("--producer-dir", args.producer_dir),
                ("--stage-b-dir", args.stage_b_dir),
                ("--holdout-ledger-path", args.holdout_ledger_path),
                ("--authorized-by", args.authorized_by),
            )
            if value is None
        ]
        if missing:
            print(
                f"ERROR: --stage C requiere explícitamente {', '.join(missing)}.",
                file=sys.stderr,
            )
            return 2
        if args.overwrite:
            print(
                "ERROR: --overwrite está prohibido incondicionalmente con --stage C "
                "(Decisión 3, defensa en profundidad sobre el ledger).",
                file=sys.stderr,
            )
            return 2
        if args.validate_inputs_only:
            print(
                "ERROR: --validate-inputs-only no está soportado con --stage C: validar "
                "provenance implica hashear el CSV completo, que ya incluye el holdout "
                "2024-2025 -- esa operación solo puede ocurrir después de confirmar la "
                "apertura durable del holdout, nunca como una validación aislada previa.",
                file=sys.stderr,
            )
            return 2

    if args.era5_csv is None or args.nasa_power_csv is None or args.output_dir is None:
        print(
            "ERROR: --era5-csv, --nasa-power-csv y --output-dir son requeridos (salvo con "
            "--init-holdout-ledger).",
            file=sys.stderr,
        )
        return 2

    # La Etapa C NUNCA valida provenance (lo que implica calcular el SHA-256
    # completo de los CSV, que incluyen 2024-2025) en este punto: hacerlo
    # antes de reservar/confirmar la apertura del holdout ya sería acceder al
    # archivo del holdout, aunque después se filtren esas filas (documento de
    # decisiones, Decisión 2, y "Orden de acceso al holdout" de este
    # encargo). Se difiere hasta después de la confirmación durable, dentro
    # de `_run_stage_c`.
    report = None
    if args.stage != STAGE_C:
        report = validate_pergamino_provenance(
            args.era5_csv, args.nasa_power_csv, mode=args.input_mode
        )
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
            constraints_identity=constraints_identity,
        )

    if args.stage == STAGE_C:
        return _run_stage_c(
            args,
            environment_info=environment_info,
            environment_report=environment_report,
            code_identity=code_identity,
            constraints_identity=constraints_identity,
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
    constraints_identity: dict,
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

    # Protección de los artefactos de A (hallazgo H-05, revisión externa
    # 2026-09-14): verificada en la CLI ANTES de entrenar nada -- ni siquiera
    # antes de leer el contrato -- y de nuevo, incondicionalmente, en el
    # escritor antes de cualquier escritura (`write_stage_b_artifacts`, que
    # no confía en que la CLI ya la haya aplicado). `--overwrite` nunca
    # autoriza escribir en, ni dentro de, el directorio productor de A.
    try:
        artifacts.validate_stage_b_output_directory(args.output_dir, args.producer_dir)
    except artifacts.StageBOutputDirectoryConflictsWithProducerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 9

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
        # Identidad real de 'constraints.txt' (hallazgo H-05, revisión
        # externa 2026-09-14): capturada antes de entrenar (igual que en A),
        # incorporada aquí al entorno persistido de B -- antes se capturaba
        # pero nunca llegaba a `environment.json` de B.
        consumer_environment_info={
            **environment_info,
            "constraints_identity": constraints_identity,
        },
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


def _run_stage_c(
    args: argparse.Namespace,
    *,
    environment_info: dict,
    environment_report: Any,
    code_identity: Any,
    constraints_identity: dict,
) -> int:
    """Etapa C: secuencia completa de apertura del holdout final (protocolo,
    sección 11) -- verificación de antecedentes SIN tocar ningún dato de
    2024-2025, reserva atómica del ledger, confirmación durable con
    `fsync` ANTES de acceder al holdout, evaluación única, y finalización
    separada del ledger. Nunca acepta `--overwrite` (rechazado en `main`
    antes de llegar aquí)."""
    import json
    import uuid

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
    from experiment_runner.controlled_daily_v4.stage_c_runner import (
        StageCTechnicalError,
        run_stage_c,
    )

    ledger_mode = (
        holdout_ledger.LEDGER_MODE_SCIENTIFIC
        if args.input_mode == INPUT_MODE_SCIENTIFIC
        else holdout_ledger.LEDGER_MODE_SYNTHETIC
    )

    # --- Paso 1: verificación previa, SIN tocar el holdout -----------------
    # Protección de directorios (A, B, ledger) ANTES de cualquier otra
    # verificación o escritura -- ningún archivo protegido se toca ante un
    # rechazo, ni siquiera antes de leer el contrato.
    try:
        artifacts.validate_stage_c_output_directory(
            args.output_dir,
            producer_dir=args.producer_dir,
            stage_b_dir=args.stage_b_dir,
            ledger_path=args.holdout_ledger_path,
        )
    except artifacts.StageCOutputDirectoryConflictError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 9

    try:
        contract = load_frozen_config_contract(args.producer_dir)
    except (TransferContractSchemaError, TransferContractValidationError) as exc:
        print(f"ERROR: contrato de transferencia A→B inválido: {exc}", file=sys.stderr)
        return 6

    consumer_code_identity = dataclasses.asdict(code_identity)
    try:
        check_stage_c_admissibility(
            contract,
            stage_b_dir=args.stage_b_dir,
            producer_dir=args.producer_dir,
            consumer_input_mode=args.input_mode,
            consumer_code_identity=consumer_code_identity,
            consumer_environment_issues=environment_report.issues,
        )
    except StageCAdmissibilityError as exc:
        print("ERROR: la Etapa B no habilita esta ejecución de la Etapa C:", file=sys.stderr)
        for reason in exc.reasons:
            print(f"  - {reason}", file=sys.stderr)
        return 7

    holdout_key = holdout_ledger.compute_holdout_identity_key(
        protocol_id=PROTOCOL_ID,
        site=HOLDOUT_SITE,
        depth_column=contract.depth_column,
        period_start=str(STAGE_C_BOUNDS.target_start),
        period_end=str(STAGE_C_BOUNDS.target_end),
    )

    ledger_state = holdout_ledger.read_holdout_state(
        args.holdout_ledger_path, holdout_key, expected_mode=ledger_mode
    )

    if ledger_state.state == holdout_ledger.STATE_CONFIRMED and ledger_state.finalized:
        # Recuperación de solo lectura (documento de decisiones, Decisión 2):
        # nunca se reentrena ni se accede al holdout crudo de nuevo.
        result_dir = Path(ledger_state.finalized_result_reference)
        print(
            "El holdout de esta identidad ya fue evaluado y finalizado. Recuperando el "
            f"resultado existente (solo lectura, sin reentrenar): {result_dir}"
        )
        for name in ("schema_version.json", "outcome.json", "metrics.json"):
            candidate = result_dir / name
            if candidate.exists():
                print(f"  {name}: {candidate}")
        return 0

    if ledger_state.state in (holdout_ledger.STATE_CONFIRMED, holdout_ledger.STATE_INDETERMINATE):
        print(
            f"ERROR: el holdout de esta identidad ya está protegido (estado="
            f"{ledger_state.state}): {ledger_state.detail}. No se accede a ningún dato de "
            "2024-2025. Sin marca de finalización, no hay resultado recuperable; requiere "
            "revisión humana explícita fuera de esta CLI.",
            file=sys.stderr,
        )
        return 11

    # --- Paso 2: reserva atómica, todavía sin tocar el holdout -------------
    attempt_id = uuid.uuid4().hex
    try:
        holdout_ledger.reserve_holdout(
            args.holdout_ledger_path, holdout_key, mode=ledger_mode, attempt_id=attempt_id
        )
    except holdout_ledger.HoldoutAlreadyProtectedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 11
    except holdout_ledger.HoldoutLedgerNotInitializedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 12

    # --- Paso 3: confirmación durable, todavía antes del acceso ------------
    try:
        holdout_ledger.confirm_holdout_open(
            args.holdout_ledger_path,
            holdout_key,
            mode=ledger_mode,
            attempt_id=attempt_id,
            authorized_by=args.authorized_by,
        )
    except holdout_ledger.HoldoutReservationLostError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 13

    # --- Paso 4: recién ahora, acceso autorizado y evaluación --------------
    # A partir de este punto el holdout está abierto de forma PERMANENTE: un
    # fallo posterior a esta línea deja el ledger en CONFIRMADA para siempre,
    # sin reintento automático (documento de decisiones, Decisión 2).
    report = validate_pergamino_provenance(args.era5_csv, args.nasa_power_csv, mode=args.input_mode)
    if not report.ok:
        print(
            "ERROR: validación de provenance/identidad falló DESPUÉS de confirmar la apertura "
            "del holdout -- el holdout queda marcado como abierto de forma permanente, sin "
            "reintento automático:",
            file=sys.stderr,
        )
        for issue in report.issues:
            print(f"  - {issue}", file=sys.stderr)
        return 14

    if args.input_mode == INPUT_MODE_SCIENTIFIC:
        try:
            a_provenance = json.loads(
                (Path(args.producer_dir) / "provenance.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"ERROR: no se pudo leer 'provenance.json' de A para verificar identidad de "
                f"fuente ({exc}). El holdout queda abierto de forma permanente.",
                file=sys.stderr,
            )
            return 14
        source_mismatches = [
            field
            for field in ("era5_sha256", "nasa_power_sha256")
            if a_provenance.get(field) and a_provenance.get(field) != getattr(report, field)
        ]
        if source_mismatches:
            print(
                "ERROR: los CSV provistos a la Etapa C no son la misma fuente identificada por "
                f"la Etapa A en {source_mismatches}. El holdout queda abierto de forma "
                "permanente, sin reintento automático.",
                file=sys.stderr,
            )
            return 14

    window_start, _ = compute_stage_window_bounds(STAGE_C_TRAINING_BOUNDS)
    _, window_end = compute_stage_window_bounds(STAGE_C_BOUNDS)

    _era5_meta, era5_df = load_era5_hourly_raw(args.era5_csv)
    era5_df = restrict_era5_hourly_to_window(era5_df, window_start, window_end)
    era5_daily = aggregate_era5_daily(era5_df)

    _nasa_meta, nasa_df = load_nasa_power_daily_raw(args.nasa_power_csv)
    nasa_df = restrict_nasa_power_daily_to_window(nasa_df, window_start, window_end)
    nasa_df = replace_missing_sentinel(nasa_df)

    daily_series = build_daily_joined_series(era5_daily, nasa_df)

    try:
        result = run_stage_c(
            contract,
            daily_series,
            bootstrap_replicas=args.bootstrap_replicas,
            bootstrap_seed=args.seed,
        )
    except StageCTechnicalError as exc:
        print(
            f"ERROR: fallo técnico de la Etapa C DESPUÉS de la apertura confirmada del "
            f"holdout (el holdout queda abierto de forma permanente, sin reintento "
            f"automático): {exc}",
            file=sys.stderr,
        )
        return 15

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

    written = artifacts.write_stage_c_artifacts(
        args.output_dir,
        input_mode=args.input_mode,
        scientific_run=scientific_run,
        resolved_config={
            "stage": STAGE_C,
            "producer_dir": str(args.producer_dir),
            "stage_b_dir": str(args.stage_b_dir),
            "seed": args.seed,
            "bootstrap_replicas": args.bootstrap_replicas,
            "normative_seed": BOOTSTRAP_SEED,
            "normative_bootstrap_replicas": BOOTSTRAP_REPLICAS_DEFAULT,
            "normative_run": not deviations,
            "normative_deviations": deviations,
        },
        producer_dir=args.producer_dir,
        producer_contract_raw=contract.raw,
        stage_b_dir=args.stage_b_dir,
        stage_b_decision_raw=json.loads(
            (Path(args.stage_b_dir) / "decision.json").read_text(encoding="utf-8")
        ),
        ledger_path=args.holdout_ledger_path,
        holdout_identity_key=holdout_key,
        attempt_id=attempt_id,
        authorized_by=args.authorized_by,
        consumer_code_identity=consumer_code_identity,
        consumer_environment_info={
            **environment_info,
            "constraints_identity": constraints_identity,
        },
        consumer_environment_issues=environment_report.issues,
        result=result,
    )

    # --- Paso 5: marca de finalización, separada de la apertura ------------
    holdout_ledger.finalize_holdout(
        args.holdout_ledger_path,
        holdout_key,
        mode=ledger_mode,
        result_reference=str(args.output_dir),
    )

    print(f"Etapa C completada. Artefactos escritos en: {args.output_dir}")
    print(
        f"Predicciones disponibles: {result.predictions_available} "
        f"(motivos: {result.outcome_reasons or 'ninguno'})"
    )
    if not scientific_run:
        print("[NO CIENTÍFICO] Esta corrida de Etapa C no es evidencia científica formal.")
    for name, path in written.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
