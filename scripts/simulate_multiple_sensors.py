"""Lanza N instancias de `simulate_sensor_readings.py` en paralelo, una
por sensor, para generar tráfico concurrente real contra el backend
(ADR-0008) y poder observar cómo se comporta la arquitectura con
varios sensores en simultáneo.

Uso:
    python scripts/simulate_multiple_sensors.py \
        --sensor-ids sensor-melchor-1,sensor-melchor-2,sensor-melchor-3 \
        --backend-url http://localhost:8000 --rounds 5 --interval-seconds 2
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent / "simulate_sensor_readings.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensor-ids", required=True, help="Lista separada por comas.")
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--rounds", type=int, default=1, help="Lecturas a enviar por sensor.")
    parser.add_argument("--interval-seconds", type=float, default=0.0)
    return parser.parse_args()


def _send_one_reading(sensor_id: str, backend_url: str) -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--sensor-id", sensor_id, "--backend-url", backend_url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[{sensor_id}] ERROR: {result.stderr.strip()}")
    else:
        print(f"[{sensor_id}] {result.stdout.strip()}")


def main() -> None:
    args = parse_args()
    sensor_ids = [s.strip() for s in args.sensor_ids.split(",") if s.strip()]

    for round_number in range(1, args.rounds + 1):
        print(f"--- Ronda {round_number}/{args.rounds} ---")
        with ThreadPoolExecutor(max_workers=len(sensor_ids)) as executor:
            list(
                executor.map(
                    lambda sensor_id: _send_one_reading(sensor_id, args.backend_url), sensor_ids
                )
            )
        if round_number < args.rounds and args.interval_seconds > 0:
            time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
