"""One scientific B attempt; recovery reads authenticated local artifacts only.

Custody assumes one persistent registry shared by all processes, as for C.
No reset/release/re-evaluation command is provided.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

KEY = "controlled_daily_v4_external_pergamino/pergamino/0-7cm/B/2023"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_paths(output, registry, producer, checkout):
    paths = [Path(p).resolve() for p in (output, registry, producer, checkout)]
    out, reg, prod, repo = paths
    if any(p == repo or repo in p.parents for p in (out, reg)):
        raise ValueError("Scientific evidence and registry must be outside checkout")
    if out == prod or out in prod.parents or prod in out.parents:
        raise ValueError("Output and producer must be disjoint")
    if any(reg == p or p in reg.parents or reg in p.parents for p in (out, prod)):
        raise ValueError("Registry must be outside all artifact directories")
    if not reg.parent.is_dir() or not out.parent.is_dir():
        raise ValueError("Explicit external evidence/registry parent directories required")


@contextmanager
def connect(path):
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=30)
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS attempts "
        "(key TEXT PRIMARY KEY, id TEXT, metadata TEXT, result TEXT)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS events " "(id TEXT, at TEXT, kind TEXT, reason TEXT)")
    try:
        yield conn
    finally:
        conn.close()


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def reserve(path, metadata):
    with connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        attempt = uuid4().hex
        try:
            conn.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, NULL)",
                (KEY, attempt, json.dumps(metadata, sort_keys=True)),
            )
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise ValueError(
                "B already attempted; only explicit read-only recovery allowed"
            ) from exc
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?)",
            (attempt, utcnow(), "RESERVED", "first scientific attempt"),
        )
        conn.commit()
    return attempt


def finalize(path, attempt, output):
    output = Path(output).resolve()
    files = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    required = {
        "decision.json",
        "predictions_2023.csv",
        "metrics.json",
        "stage_b_custody.json",
        "code_version.json",
        "resolved_config.json",
    }
    if not required <= files.keys():
        raise ValueError("Incomplete B artifacts; attempt remains blocked")
    result = {"directory": str(output), "files": files}
    with connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        changed = conn.execute(
            "UPDATE attempts SET result=? WHERE key=? AND id=? AND result IS NULL",
            (json.dumps(result), KEY, attempt),
        ).rowcount
        if changed != 1:
            conn.rollback()
            raise ValueError("Attempt ownership or finalization conflict")
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?)",
            (attempt, utcnow(), "FINALIZED", "complete artifact hashes"),
        )
        conn.commit()


def recover(path, reason):
    if not reason or not reason.strip() or not Path(path).is_file():
        raise ValueError("Recovery requires existing registry and technical reason")
    # Never recreates a missing registry; a missing/incomplete record fails closed.
    with connect(path) as conn:
        row = conn.execute("SELECT id,result FROM attempts WHERE key=?", (KEY,)).fetchone()
        if row is None or row[1] is None:
            raise ValueError("Incomplete attempt: manual review required, no re-evaluation")
        attempt, raw = row
        result = json.loads(raw)
        directory = Path(result["directory"])
        for name, expected in result["files"].items():
            if (
                Path(name).name != name
                or not (directory / name).is_file()
                or sha(directory / name) != expected
            ):
                raise ValueError("Recovery integrity failure")
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?)",
            (attempt, utcnow(), "RECOVERED_READ_ONLY", reason),
        )
        return result


def guarded_stage_b(args, run, **context):
    """Called before provenance parsing, aggregation or model fitting."""
    if args.input_mode != "scientific":
        from experiment_runner.controlled_daily_v4.provenance import validate_pergamino_provenance

        context["report"] = validate_pergamino_provenance(
            args.era5_csv, args.nasa_power_csv, mode=args.input_mode
        )
        if not context["report"].ok:
            return 3
        return run(args, **context)
    if args.stage_b_registry_path is None:
        raise ValueError("Scientific B requires --stage-b-registry-path")
    validate_paths(
        args.output_dir,
        args.stage_b_registry_path,
        args.producer_dir,
        Path(__file__).resolve().parents[3],
    )
    if args.recover_stage_b:
        result = recover(args.stage_b_registry_path, args.recovery_reason)
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.overwrite:
        raise ValueError("Scientific B forbids overwrite")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("Scientific B requires a new empty output directory")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image_id or ""):
        raise ValueError("Scientific B requires immutable --image-id sha256")
    identity = context["code_identity"]
    if not identity.available or identity.dirty is not False:
        raise ValueError("Scientific B requires clean known code identity")
    from experiment_runner.controlled_daily_v4.transfer_contract import load_frozen_config_contract

    contract = load_frozen_config_contract(args.producer_dir)
    if (
        not contract.scientific_run
        or not contract.candidate_produced
        or contract.depth_role != "primary_selection"
        or contract.producer_code_identity.get("commit") != identity.commit
    ):
        raise ValueError("Candidate must be scientifically frozen at this commit before B")
    from experiment_runner.controlled_daily_v4.features import feature_contract

    producer_config = json.loads((args.producer_dir / "resolved_config.json").read_text())
    if producer_config.get("image_id") != args.image_id:
        raise ValueError("A and B must use the same immutable image")
    if contract.raw.get("feature_contract") != feature_contract():
        raise ValueError("Frozen feature contract differs from executable contract")
    if args.seed != 20250109 or args.bootstrap_replicas != 5000:
        raise ValueError("Scientific B requires normative bootstrap configuration")
    metadata = {
        "key": KEY,
        "started_at": utcnow(),
        "commit": identity.commit,
        "image_id": args.image_id,
        "candidate": contract.raw,
        "configuration": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "input_hashes": {"era5": sha(args.era5_csv), "nasa": sha(args.nasa_power_csv)},
        "producer_hashes": {p.name: sha(p) for p in args.producer_dir.iterdir() if p.is_file()},
        "environment": context["environment_info"],
    }
    attempt = reserve(args.stage_b_registry_path, metadata)
    from experiment_runner.controlled_daily_v4.provenance import validate_pergamino_provenance

    report = validate_pergamino_provenance(args.era5_csv, args.nasa_power_csv, mode=args.input_mode)
    if not report.ok:
        raise ValueError("Provenance failed after reservation; B remains blocked")
    context["report"] = report
    code = run(args, **context)
    if code == 0:
        payload = {"attempt_id": attempt, **metadata}
        (args.output_dir / "stage_b_custody.json").write_text(
            json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8"
        )
        finalize(args.stage_b_registry_path, attempt, args.output_dir)
    return code
