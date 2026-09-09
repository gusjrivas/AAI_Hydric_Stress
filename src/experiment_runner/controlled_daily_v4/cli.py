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
    PRIMARY_DEPTH_COLUMN,
    SENSITIVITY_DEPTH_COLUMN,
    STAGE_A,
    ProtocolConfig,
    UnsupportedStageError,
    require_stage_a,
)
from experiment_runner.controlled_daily_v4.provenance import validate_pergamino_provenance

DEPTH_CHOICES = {"primary": PRIMARY_DEPTH_COLUMN, "sensitivity": SENSITIVITY_DEPTH_COLUMN}


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        require_stage_a(args.stage)
    except UnsupportedStageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = validate_pergamino_provenance(args.era5_csv, args.nasa_power_csv)
    if not report.ok:
        print("ERROR: validación de provenance falló:", file=sys.stderr)
        for issue in report.issues:
            print(f"  - {issue}", file=sys.stderr)
        return 3

    if args.validate_inputs_only:
        print("Provenance OK. --validate-inputs-only: no se entrena nada.")
        return 0

    from experiment_runner.controlled_daily_v4 import artifacts
    from experiment_runner.controlled_daily_v4.ingestion import (
        aggregate_era5_daily,
        build_daily_joined_series,
        load_era5_hourly_raw,
        load_nasa_power_daily_raw,
        replace_missing_sentinel,
    )
    from experiment_runner.controlled_daily_v4.stage_a_runner import run_stage_a

    _era5_meta, era5_df = load_era5_hourly_raw(args.era5_csv)
    era5_daily = aggregate_era5_daily(era5_df)
    _nasa_meta, nasa_df = load_nasa_power_daily_raw(args.nasa_power_csv)
    nasa_df = replace_missing_sentinel(nasa_df)
    daily_series = build_daily_joined_series(era5_daily, nasa_df)

    protocol_config = ProtocolConfig(
        bootstrap_seed=args.seed, bootstrap_replicas=args.bootstrap_replicas
    )
    depth_column = DEPTH_CHOICES[args.depth]
    results = run_stage_a(daily_series, depth_column, protocol_config)

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

    written = artifacts.write_stage_a_artifacts(
        args.output_dir,
        depth_column=depth_column,
        resolved_config={
            "stage": STAGE_A,
            "seed": args.seed,
            "bootstrap_replicas": args.bootstrap_replicas,
        },
        provenance_report=report,
        environment_info={"note": "completar con versiones exactas del entorno de ejecución real"},
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
        overwrite=args.overwrite,
    )

    print(f"Etapa A completada. Artefactos escritos en: {args.output_dir}")
    print(f"Selección: {results.selection.outcome} -> {results.selection.selected_family}")
    for name, path in written.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
