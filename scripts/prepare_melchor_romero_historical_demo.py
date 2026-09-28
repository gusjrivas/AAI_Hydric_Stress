"""Reproducible preparation of the Melchor Romero historical-demonstration
site (second real site, generalizing Pergamino's `pergamino-ensemble-demo`
walkthrough, ADR-0008's per-sensor isolation).

This script performs the two steps that, for Pergamino, were done manually
and documented after the fact (`docs/design/ensemble-real-execution-report
-2026-09-26.md`, `docs/design/ensemble-historical-walkthrough-report-2026-09
-26.md`): (1) build the real ensemble bundles, and (2) PREPARE five
historical emissions (one real `POST .../forecasts` per day, exactly the
route `HistoricalWalkthrough`'s reproduction reads later) -- committed here
as reusable code instead of an undocumented one-off, on the (stronger)
premise that Melchor Romero's dataset is real and already versioned in this
repository, unlike Pergamino's external CSVs.

Never touches `data/` (the repository's own dataset store) as a WRITE
target, never touches `replay_packages/` (a different capability,
`historical_replay`), and never emits more than the five declared demo
dates. Uses FastAPI's `TestClient` against the real, unmodified app (with
`dependency_overrides` pointed at the given `--data-dir`/`--bundle-root`),
exactly the same route logic a live server would run -- not a separate
implementation of the preparation step.

Usage:
    python scripts/prepare_melchor_romero_historical_demo.py \\
        --data-dir "<external, empty-or-existing dir>" \\
        --bundle-root "<external, must-be-empty dir>"

The resulting `--data-dir`/`--bundle-root` pair can then be passed as
`PRODUCER_DATA_DIR`/`PRODUCER_BUNDLE_ROOT` to
`scripts/run_producer_preview_backend.py` (generic, already sensor-agnostic)
to serve this site for real, or mounted into the `producer_v2` backend
container the same way Pergamino's runtime directories are.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

DEMO_DATES = ["2024-10-20", "2024-10-21", "2024-10-22", "2024-10-23", "2024-10-24"]
DEFAULT_SENSOR_ID = "melchor-romero-demo"


def _prepare_emissions(*, sensor_id: str, data_dir: Path, bundle_root: Path, frame: pd.DataFrame) -> None:
    from app.config import get_dataset_data_dir, is_producer_v2_enabled
    from app.dependencies import get_producer_bundle_root
    from app.main import app
    from fastapi.testclient import TestClient

    from data_ingestion.storage import save_dataset

    app.dependency_overrides[get_dataset_data_dir] = lambda: data_dir
    app.dependency_overrides[is_producer_v2_enabled] = lambda: True
    app.dependency_overrides[get_producer_bundle_root] = lambda: bundle_root
    try:
        with TestClient(app) as client:
            for raw_date in DEMO_DATES:
                as_of = pd.Timestamp(raw_date).date()
                truncated = frame.loc[frame["timestamp"].dt.date <= as_of].copy()
                truncated["origen"] = "real"
                save_dataset(f"sensor__{sensor_id}", truncated, data_dir=data_dir)
                response = client.post(
                    f"/api/v2/sensors/{sensor_id}/forecasts",
                    headers={"Idempotency-Key": f"prepare-melchor-romero-{raw_date}"},
                    json={},
                )
                if response.status_code != 201:
                    raise RuntimeError(
                        f"No se pudo preparar la emisión {raw_date}: "
                        f"{response.status_code} {response.text}"
                    )
                print(f"emisión preparada: {raw_date} (as_of_date={response.json()['as_of_date']})")
    finally:
        app.dependency_overrides.clear()

    # After all 5 emissions are prepared, restore the FULL real dataset so
    # revealed_through can show genuine later observations (never a value
    # from a date that was never in the raw dataset).
    full_frame = frame.copy()
    full_frame["origen"] = "real"
    save_dataset(f"sensor__{sensor_id}", full_frame, data_dir=data_dir)
    print(f"lecturas completas restauradas: {len(full_frame)} filas")


def main(argv: list[str] | None = None) -> int:
    from experiment_runner.melchor_romero_historical_demo_runner import (
        build_daily_frame_from_repo_dataset,
        run_demo,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--sensor-id", default=DEFAULT_SENSOR_ID)
    args = parser.parse_args(argv)

    args.data_dir.mkdir(parents=True, exist_ok=True)

    print(f"construyendo bundles reales en {args.bundle_root} ...")
    run_demo(args.bundle_root, sensor_id=args.sensor_id, horizons=(1, 2, 3))

    frame, dataset_sha256 = build_daily_frame_from_repo_dataset()
    print(f"dataset real cargado (sha256={dataset_sha256[:16]}...), preparando emisiones ...")
    _prepare_emissions(
        sensor_id=args.sensor_id, data_dir=args.data_dir, bundle_root=args.bundle_root, frame=frame
    )
    print("listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
