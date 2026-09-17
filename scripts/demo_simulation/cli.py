"""CLI de la demostración acelerada (diseño, sección 2):

    python -m scripts.demo_simulation prepare --start YYYY-MM-DD --days 10 \
        --history-days 120 --seed 42
    python -m scripts.demo_simulation run --id demo-xxxxxxxxxx
    python -m scripts.demo_simulation status --id demo-xxxxxxxxxx

Esta entrega no expone el adaptador HTTP local de control (`serve`,
entrega 2): `run` ejecuta la sesión sincrónicamente en el propio
proceso de la CLI, de punta a punta o hasta el primer fallo.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from data_ingestion.storage import DEFAULT_DATA_DIR

from .config import DEFAULT_INTERVAL_SECONDS, DemoConfigError, DemoSessionConfig
from .manifest import load_manifest
from .prepare import DEFAULT_SESSIONS_DIR, prepare_session
from .worker import DemoStepError, run_session

DEFAULT_BACKEND_URL = "http://localhost:8000"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.demo_simulation", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Prepara una sesión nueva.")
    prepare_parser.add_argument("--start", type=date.fromisoformat, required=True)
    prepare_parser.add_argument("--days", type=int, required=True)
    prepare_parser.add_argument("--history-days", type=int, required=True)
    prepare_parser.add_argument("--seed", type=int, required=True)
    prepare_parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    prepare_parser.add_argument("--interval-seconds", type=int, default=DEFAULT_INTERVAL_SECONDS)
    prepare_parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR)
    prepare_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    prepare_parser.add_argument(
        "--id", dest="session_id", default=None, help="Solo para pruebas: fija el identificador."
    )

    run_parser = subparsers.add_parser("run", help="Ejecuta pasos pendientes de una sesión.")
    run_parser.add_argument("--id", dest="session_id", required=True)
    run_parser.add_argument("--steps", type=int, default=None)
    run_parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR)

    status_parser = subparsers.add_parser("status", help="Muestra el manifiesto de una sesión.")
    status_parser.add_argument("--id", dest="session_id", required=True)
    status_parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR)

    return parser


def _cmd_prepare(args: argparse.Namespace) -> int:
    config = DemoSessionConfig(
        start_date=args.start,
        days=args.days,
        history_days=args.history_days,
        seed=args.seed,
        backend_url=args.backend_url,
        interval_seconds=args.interval_seconds,
    )
    today = datetime.now(timezone.utc).date()
    try:
        result = prepare_session(
            config,
            today=today,
            sessions_root=args.sessions_dir,
            data_dir=args.data_dir,
            session_id=args.session_id,
        )
    except DemoConfigError as error:
        print(f"No se preparó la sesión: {error}", file=sys.stderr)
        return 1

    print(
        f"Sesión '{result.manifest.session_id}' preparada: {result.history_rows} filas de "
        f"historia sintética, sensor exclusivo '{result.manifest.sensor_id}'.\n"
        f"Manifiesto: {result.manifest_path}\n"
        f"Siguiente paso: python -m scripts.demo_simulation run --id {result.manifest.session_id}"
    )
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        manifest = run_session(args.session_id, args.sessions_dir, steps=args.steps)
    except (DemoStepError, FileNotFoundError) as error:
        print(f"La sesión se detuvo: {error}", file=sys.stderr)
        return 1

    print(
        f"Sesión '{manifest.session_id}': estado={manifest.status}, "
        f"días completados={manifest.cursor}/{manifest.days}."
    )
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    try:
        manifest = load_manifest(args.sessions_dir, args.session_id)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handlers = {"prepare": _cmd_prepare, "run": _cmd_run, "status": _cmd_status}
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
