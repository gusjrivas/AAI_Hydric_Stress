"""Consolida varios datasets ya ingeridos (mismo esquema, ver
data_ingestion.consolidate) en un único conjunto experimental, guarda el
resultado y regenera el reporte de cobertura sobre el dataset consolidado.

Uso:
    python scripts/consolidate_datasets.py --sources nasa_power_la_plata_2024 \
        esa_cci_soil_moisture_la_plata_2024 --name la_plata_2024_consolidado
"""

from __future__ import annotations

import argparse

from data_ingestion.consolidate import consolidate_sources
from data_ingestion.coverage import coverage_report
from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset, save_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", required=True)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frames = [load_dataset(source) for source in args.sources]

    consolidated = consolidate_sources(frames)
    dataset_path = save_dataset(args.name, consolidated)

    coverage = coverage_report(consolidated)
    coverage_path = DEFAULT_DATA_DIR / f"{args.name}_coverage.csv"
    coverage.to_csv(coverage_path, index=False)

    print(f"Dataset consolidado guardado en: {dataset_path}")
    print(f"Reporte de cobertura en: {coverage_path}")


if __name__ == "__main__":
    main()
