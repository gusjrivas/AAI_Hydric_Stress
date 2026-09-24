"""Load a historical-replay package and show the projection of one archived
prediction before and after its target date — no model is executed, no
metric is recalculated; this only demonstrates `historical_replay.projection.project`
over an already-loaded, already-validated package (spec `historical-replay`).

Usage:
    python scripts/replay_projection_demo.py --package-dir /path/to/package
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from historical_replay.package_loader import load_package
from historical_replay.projection import project


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    args = parser.parse_args()

    package = load_package(args.package_dir)
    record = package.records[0]
    origin = _as_date(record.identity.timestamp_origen)
    target = _as_date(record.target_timestamp)

    before = project(record, target - timedelta(days=1))
    after = project(record, target)

    print(f"package_id={package.manifest['package_id']}")
    print(f"prediction identity: {record.identity}")
    print()
    print(f"--- proyeccion en {(target - timedelta(days=1)).isoformat()} (antes del objetivo) ---")
    print(json.dumps(before, indent=2, ensure_ascii=False))
    print()
    print(f"--- proyeccion en {target.isoformat()} (fecha objetivo) ---")
    print(json.dumps(after, indent=2, ensure_ascii=False))
    print()
    print(
        f"origen={origin.isoformat()} objetivo={target.isoformat()} "
        f"campos revelados solo en la segunda proyeccion: "
        f"{sorted(set(after) - set(before))}"
    )


if __name__ == "__main__":
    main()
