"""CLI explícita de la Etapa A de controlled_daily_v4_external_pergamino.

Únicamente `--stage A`. No expone ninguna ruta oculta al dataset formal de
`controlled_daily_v3` ni a ningún servidor MLflow — no registra nada en
MLflow, no lo integra en absoluto.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    CalendarIntegrityError,
    ProtocolConfig,
    UnsupportedStageError,
    require_stage_a,
)
from experiment_runner.controlled_daily_v4.environment import (
    capture_environment,
    validate_environment,
)
from experiment_runner.controlled_daily_v4.provenance import validate_pergamino_provenance

DEPTH_CHOICES = {"primary": PRIMARY_DEPTH_COLUMN, "sensitivity": SENSITIVITY_DEPTH_COLUMN}


def normative_deviations(
    seed: int, bootstrap_replicas: int, *, input_mode: str, environment_ok: bool
) -> list[str]:
    """Parámetros/condiciones que apartan la corrida de lo normativo.

    Una corrida con semilla, réplicas, modo de entrada no científico o
    entorno no validado sigue siendo ejecutable (sirve para pruebas
    rápidas o desarrollo), pero queda marcada como no normativa en la
    evidencia para que no se confunda con la corrida real (hallazgo H-04:
    la condición normativa considera modo, validación de entradas,
    integridad temporal y entorno; la integridad temporal ya se exige de
    forma incondicional -- ver `features.validate_continuous_daily_calendar`
    -- por lo que llegar a este punto ya la satisface)."""
    deviations = []
    if seed != BOOTSTRAP_SEED:
        deviations.append("seed")
    if bootstrap_replicas != BOOTSTRAP_REPLICAS_DEFAULT:
        deviations.append("bootstrap_replicas")
    if input_mode != INPUT_MODE_SCIENTIFIC:
        deviations.append("input_mode")
    if not environment_ok:
        deviations.append("environment")
    return deviations


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="controlled-daily-v4-stage-a",
        description="Runner de la Etapa A de controlled_daily_v4_external_pergamino. "
        "No implementa ni acepta las etapas B o C.",
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["A", "B", "C"],
        help="Únicamente 'A' está implementada. 'B' y 'C' se rechazan explícitamente.",
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
        require_stage_a(args.stage)
    except UnsupportedStageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
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
    if args.input_mode == INPUT_MODE_SCIENTIFIC and not environment_report.ok:
        print(
            "ERROR: validación de entorno falló (antes de ajustar ningún modelo):",
            file=sys.stderr,
        )
        for issue in environment_report.issues:
            print(f"  - {issue}", file=sys.stderr)
        return 4

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
    )

    written = artifacts.write_stage_a_artifacts(
        args.output_dir,
        depth_column=depth_column,
        resolved_config={
            "stage": STAGE_A,
            "seed": args.seed,
            "bootstrap_replicas": args.bootstrap_replicas,
            "input_mode": args.input_mode,
            "normative_seed": BOOTSTRAP_SEED,
            "normative_bootstrap_replicas": BOOTSTRAP_REPLICAS_DEFAULT,
            "normative_run": not deviations,
            "normative_deviations": deviations,
            "scientific_run": report.scientific and not deviations,
        },
        provenance_report=report,
        environment_info={
            **environment_info,
            "validation_issues": environment_report.issues,
            "validated_before_training": True,
        },
        input_hashes={
            "era5_sha256": report.era5_sha256,
            "nasa_power_sha256": report.nasa_power_sha256,
        },
        outer_fold_boundaries=outer_fold_boundaries,
        per_family_outer_results=results.per_family_outer_results,
        oof_by_family=results.oof_by_family,
        selection_result=results.selection,
        frozen_single_family=results.frozen_single_family,
        frozen_soft_voting_bases=results.frozen_soft_voting_bases,
        final_p20_train=results.final_p20_train,
        final_estimator_details=results.final_estimator_details,
        overwrite=args.overwrite,
    )

    print(f"Etapa A completada. Artefactos escritos en: {args.output_dir}")
    print(f"Selección: {results.selection.outcome} -> {results.selection.selected_family}")
    for name, path in written.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
