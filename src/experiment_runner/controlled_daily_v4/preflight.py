"""Metadata-only preparation. Never parses inputs or initializes a ledger."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from experiment_runner.controlled_daily_v4.code_identity import capture_code_identity
from experiment_runner.controlled_daily_v4.environment import (
    capture_environment,
    validate_environment,
)
from experiment_runner.controlled_daily_v4.features import feature_contract
from experiment_runner.controlled_daily_v4.manifest_reference import (
    DEFAULT_CONSTRAINTS_PATH,
    DEFAULT_MANIFEST_PATH,
    load_manifest_identity_reference,
)
from experiment_runner.controlled_daily_v4.stage_b_custody import sha


def validate_layout(checkout, raw, evidence, ledger, backups):
    paths = [Path(p).resolve() for p in (checkout, raw, evidence, ledger, backups)]
    for i, left in enumerate(paths):
        if not left.is_dir():
            raise ValueError(f"Directory must already exist: {left}")
        for right in paths[i + 1 :]:
            if left == right or left in right.parents or right in left.parents:
                raise ValueError("Checkout, raw, evidence, ledger and backups must be disjoint")
    return paths


def prepare_manifest(checkout, raw, evidence, ledger, backups, image_id):
    paths = validate_layout(checkout, raw, evidence, ledger, backups)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("Immutable image ID required")
    identity = capture_code_identity()
    environment = capture_environment()
    validation = validate_environment(environment)
    if not identity.available or identity.dirty is not False or not validation.ok:
        raise ValueError("Clean known commit and pinned valid environment required")
    reference = load_manifest_identity_reference()
    files = {}
    for name, ref in (
        ("pergamino_era5land_soil_hourly_2015_2025.csv", reference.era5),
        ("pergamino_nasa_power_daily_2015_2025.csv", reference.nasa_power),
    ):
        path = paths[1] / name
        if not path.is_file() or path.stat().st_size != ref.size_bytes:
            raise ValueError(f"Missing input or size mismatch: {name}")
        files[name] = {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "expected_sha256": ref.sha256,
            "hash_verified_this_preflight": False,
        }
    return {
        "schema_version": "scientific_closure_preflight.v1",
        "status": "PREPARED_NOT_AUTHORIZED",
        "commit": identity.commit,
        "image_id": image_id,
        "image_id_source": "operator_docker_inspect",
        "environment": environment,
        "constraints_sha256": sha(DEFAULT_CONSTRAINTS_PATH),
        "protocol_manifest_sha256": sha(DEFAULT_MANIFEST_PATH),
        "feature_contract": feature_contract(),
        "inputs": files,
        "directories": dict(
            zip(("checkout", "raw", "evidence", "ledger", "backups"), map(str, paths))
        ),
        "scientific_stages_executed": [],
        "ledger_initialized": False,
        "values_read": False,
        "input_hash_policy": "deferred_to_authorized_runner",
        "seeds": {"model": 42, "bootstrap": 20250109},
        "bootstrap_replicas": 5000,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("checkout", "raw", "evidence", "ledger", "backups"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_manifest(**vars(args)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
