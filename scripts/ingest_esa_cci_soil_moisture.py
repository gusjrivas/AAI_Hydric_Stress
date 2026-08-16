"""Ejecuta la ingestión real de ESA CCI Soil Moisture (CEDA Archive) para
una ubicación y rango de fechas dados. Por defecto, La Plata (Buenos
Aires) para el año calendario 2024 (año más reciente disponible en la
versión v09.2 del producto COMBINED al momento de escribir este script).

Uso:
    python scripts/ingest_esa_cci_soil_moisture.py
    python scripts/ingest_esa_cci_soil_moisture.py --latitude -34.92 \
        --longitude -57.95 --start 2024-01-01 --end 2024-12-31 \
        --name esa_cci_soil_moisture_la_plata_2024
"""

from __future__ import annotations

import argparse
from datetime import date

import requests

from data_ingestion.ingest import run_ingestion
from data_ingestion.sources.esa_cci_soil_moisture import fetch_esa_cci_soil_moisture

LICENSE = (
    "ESA CCI Soil Moisture, datos públicos vía CEDA Archive, descarga sin "
    "cuenta ni login (ver https://catalogue.ceda.ac.uk/uuid/"
    "6f99cdb86a9e4d3da2d47c79612c00a2/ y docs/research/hu2-fuentes-datos-acceso.md). "
    "Requiere cita del dataset según sus términos y condiciones."
)
LIMITATIONS = (
    "Solo provee humedad de suelo (variable 'sm', m3/m3) en grilla global de "
    "0.25° (~25 km); no provee variables climáticas. La versión v09.2 del "
    "producto COMBINED solo llega hasta 2024, no hay datos de 2025 todavía "
    "por el rezago de reprocesamiento satelital. Días sin archivo disponible "
    "quedan como NaN, no interrumpen la serie."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude", type=float, default=-34.92)
    parser.add_argument("--longitude", type=float, default=-57.95)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2024, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2024, 12, 31))
    parser.add_argument("--name", default="esa_cci_soil_moisture_la_plata_2024")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with requests.Session() as session:
        result = run_ingestion(
            fetch_fn=lambda lat, lon, start, end: fetch_esa_cci_soil_moisture(
                lat, lon, start, end, session=session
            ),
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
