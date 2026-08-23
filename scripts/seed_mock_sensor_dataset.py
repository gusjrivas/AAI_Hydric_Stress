"""Genera un backfill inicial de lecturas sintéticas de sensor,
encadenadas por random walk acotado, y las guarda como un dataset
nuevo (ADR-0007).

Uso:
    python scripts/seed_mock_sensor_dataset.py --name sensores_en_vivo \
        --start 2026-05-01 --end 2026-07-29
"""

from __future__ import annotations

import argparse
from datetime import date

from data_ingestion.mock_sensor import seed_mock_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generated = seed_mock_dataset(
        args.name, start_date=args.start, end_date=args.end, random_state=args.random_state
    )
    print(f"Backfill generado: {len(generated)} filas, dataset '{args.name}'.")


if __name__ == "__main__":
    main()
