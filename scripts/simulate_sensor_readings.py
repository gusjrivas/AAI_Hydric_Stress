"""Simula una lectura de sensor y la envía al backend real vía HTTP
(ADR-0007) — cliente sintético del endpoint genérico
POST /sensors/{sensor_id}/readings (ADR-0008), que no sabe que el
llamador es un mock.

Uso:
    python scripts/simulate_sensor_readings.py --sensor-id sensor-melchor-1 \
        --backend-url http://localhost:8000
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import requests

from data_ingestion.mock_sensor import generate_next_reading
from data_ingestion.schema import PROVENANCE_COLUMN
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensor-id", required=True)
    parser.add_argument("--backend-url", default="http://localhost:8000")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        existing = load_dataset(dataset_name_for(args.sensor_id))
        previous = existing.sort_values("timestamp").iloc[-1]
    except FileNotFoundError:
        previous = None

    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    reading = generate_next_reading(previous, timestamp)

    payload = {
        "timestamp": reading["timestamp"].isoformat(),
        "soil_moisture": reading.get("soil_moisture"),
        "temperature": reading.get("temperature"),
        "relative_humidity": reading.get("relative_humidity"),
        "precipitation": reading.get("precipitation"),
        "solar_radiation": reading.get("solar_radiation"),
        "wind_speed": reading.get("wind_speed"),
        "procedencia": reading[PROVENANCE_COLUMN],
    }
    response = requests.post(
        f"{args.backend_url}/sensors/{args.sensor_id}/readings", json=payload, timeout=30
    )
    response.raise_for_status()
    print(f"Lectura enviada (sensor '{args.sensor_id}'): {response.json()}")


if __name__ == "__main__":
    main()
