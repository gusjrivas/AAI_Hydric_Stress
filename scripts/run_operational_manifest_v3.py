"""Reproducible training/evaluation entry point for the frozen +1/+2/+3
operational manifest (`config/producer-calibration-plan.frozen.v3.json`,
spec `predictive-modeling`, HU4/HU6, capacidad `architecture-integration`).

Verifies the manifest's content identity, confirms the dataset's sha256
matches `dataset.sha256` exactly (never silently continues on a mismatch),
then trains/calibrates a Random Forest per horizon and training seed,
evaluates it with `predictive_modeling.calibration_assessment`, and writes
every artifact to a NEW, isolated `--output-dir` (never overwrites a
previous run). It never opens a holdout, never reads
`controlled_daily_v3`/`v4` fixtures, and never registers anything in
MLflow (out of this delivery's scope).

Reproducing the one development run this task authorized (never rerun
against real data without a new, separate authorization):

    python scripts/run_operational_manifest_v3.py \
        --manifest config/producer-calibration-plan.frozen.v3.json \
        --dataset melchor_romero_2024_consolidado \
        --output-dir data/operational_runs/<run_id> \
        --run-id <run_id>

Exercising the wiring against a synthetic fixture instead (any dataset with
`dataset.source_kind == "synthetic"` in its manifest; real, non-synthetic
data is refused unless `--allow-real-data` is passed explicitly):

    python scripts/run_operational_manifest_v3.py \
        --manifest /path/to/a/synthetic/manifest.json \
        --dataset synthetic-fixture-name --data-dir /path/to/a/tmp/dir \
        --output-dir /tmp/out --run-id smoke-test
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset_snapshot
from predictive_modeling.calibration_manifest import verify_frozen_calibration_manifest
from predictive_modeling.operational_run import run_operational_manifest
from predictive_modeling.operational_run_artifacts import persist_operational_run

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--manifest-identity",
        type=Path,
        default=None,
        help="Defaults to <manifest>.identity.json.",
    )
    parser.add_argument(
        "--dataset", required=True, help="Dataset name, as stored by data_ingestion."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--allow-real-data",
        action="store_true",
        help="Required to run against a manifest whose dataset.source_kind != 'synthetic'.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = verify_frozen_calibration_manifest(args.manifest, args.manifest_identity)

    if manifest["dataset"]["source_kind"] != "synthetic" and not args.allow_real_data:
        raise SystemExit(
            "El manifiesto declara dataset.source_kind="
            f"{manifest['dataset']['source_kind']!r}: pasar --allow-real-data explicitamente "
            "confirma que esta corrida real esta autorizada (ver AGENTS.md/protocolo experimental)."
        )

    snapshot = load_dataset_snapshot(args.dataset, data_dir=args.data_dir)
    result = run_operational_manifest(
        manifest, snapshot.dataframe, dataset_sha256=snapshot.dataset_sha256
    )

    identity_path = args.manifest_identity or args.manifest.with_name(
        args.manifest.name + ".identity.json"
    )
    manifest_identity_sha256 = json.loads(identity_path.read_text(encoding="utf-8"))[
        "content_sha256"
    ]

    output_dir = persist_operational_run(
        result,
        output_dir=args.output_dir,
        run_id=args.run_id,
        manifest_path=args.manifest,
        manifest_identity_sha256=manifest_identity_sha256,
        dataset_id=args.dataset,
        repo_root=REPO_ROOT,
    )
    print(f"Corrida operacional persistida en {output_dir}")
    for horizon_result in result.horizons:
        final = (
            horizon_result.final_decision.final_result
            if horizon_result.final_decision is not None
            else horizon_result.status
        )
        print(f"  horizonte +{horizon_result.horizon}: {final}")


if __name__ == "__main__":
    main()
