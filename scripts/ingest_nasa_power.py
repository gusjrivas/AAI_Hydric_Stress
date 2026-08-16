"""Ejecuta la ingestión real de NASA POWER para una ubicación y rango de
fechas dados. Por defecto, La Plata (Buenos Aires) — Cinturón Hortícola
Platense, región hortícola de referencia (ver
docs/research/hu1-antecedentes-argentina.md) — para el año calendario 2025.

Uso:
    python scripts/ingest_nasa_power.py
    python scripts/ingest_nasa_power.py --latitude -34.92 --longitude -57.95 \
        --start 2025-01-01 --end 2025-12-31 --name nasa_power_la_plata_2025
"""

from __future__ import annotations

import argparse
from datetime import date

from data_ingestion.ingest import run_ingestion
from data_ingestion.sources.nasa_power import fetch_nasa_power

LICENSE = (
    "Datos abiertos de NASA POWER (comunidad Agroclimatology), sin cuenta ni "
    "API key requerida. Ver https://power.larc.nasa.gov/docs/services/api/ "
    "(docs/research/hu2-fuentes-datos-acceso.md)."
)
LIMITATIONS = (
    "No provee humedad de suelo ni evapotranspiración de referencia (ET0) "
    "directamente; ET0 se deriva en preprocesamiento a partir de las "
    "variables climáticas descargadas."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude", type=float, default=-34.92)
    parser.add_argument("--longitude", type=float, default=-57.95)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--name", default="nasa_power_la_plata_2025")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_ingestion(
        fetch_fn=fetch_nasa_power,
        name=args.name,
        latitude=args.latitude,
        longitude=args.longitude,
        start=args.start,
        end=args.end,
        license_=LICENSE,
        limitations=LIMITATIONS,
    )
    print(f"Dataset guardado en: {result['dataset_path']}")
    print(f"Reporte de cobertura en: {result['coverage_path']}")
    print(f"Diccionario de datos en: {result['dictionary_path']}")


if __name__ == "__main__":
    main()
