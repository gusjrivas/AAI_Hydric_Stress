"""Genera un backfill inicial de lecturas sintéticas de sensor,
encadenadas por random walk acotado, y las guarda como el dataset
propio de `--sensor-id` (ADR-0007, ADR-0008).

Uso:
    python scripts/seed_mock_sensor_dataset.py --sensor-id sensor-melchor-1 \
        --start 2026-05-01 --end 2026-07-29
"""

from __future__ import annotations

import argparse
from datetime import date

from data_ingestion.mock_sensor import seed_mock_dataset
from data_ingestion.sensor_naming import dataset_name_for


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensor-id", required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_name = dataset_name_for(args.sensor_id)
    generated = seed_mock_dataset(
        dataset_name, start_date=args.start, end_date=args.end, random_state=args.random_state
    )
    print(f"Backfill generado: {len(generated)} filas, sensor '{args.sensor_id}' ({dataset_name}).")


if __name__ == "__main__":
    main()
