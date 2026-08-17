"""Ejecuta la ingestión real de NASA POWER para una ubicación y rango de
fechas dados. Por defecto, Melchor Romero (Partido de La Plata, Buenos
Aires) — localidad real dentro del Cinturón Hortícola Platense (ver
docs/research/hu1-antecedentes-argentina.md) — para el año calendario 2025.

Nota: el punto original (-34.92, -57.95, centro de la ciudad de La Plata)
cae sobre el estuario del Río de la Plata en la grilla de 0.25° de ESA CCI
Soil Moisture, que enmascara esa celda por contaminación de agua (ver
docs/research/hu2-fuentes-datos-acceso.md). Melchor Romero es un punto
tierra adentro del mismo cinturón hortícola, sin ese problema, elegido
para poder consolidar NASA POWER con ESA CCI en el mismo punto.

Uso:
    python scripts/ingest_nasa_power.py
    python scripts/ingest_nasa_power.py --latitude -34.95 --longitude -58.05 \
        --start 2025-01-01 --end 2025-12-31 --name nasa_power_melchor_romero_2025
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
    parser.add_argument("--latitude", type=float, default=-34.95)
    parser.add_argument("--longitude", type=float, default=-58.05)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--name", default="nasa_power_melchor_romero_2025")
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
