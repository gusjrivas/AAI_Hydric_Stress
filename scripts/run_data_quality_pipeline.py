"""Ejecuta el flujo integrado de calidad de datos (data_quality.pipeline)
sobre un dataset ya consolidado, para una de las 4 configuraciones
experimentales de la Épica 4 (base, +sintéticos, +anomalías, completa).

Uso:
    python scripts/run_data_quality_pipeline.py \
        --dataset melchor_romero_2024_consolidado \
        --columns temperature relative_humidity precipitation \
            solar_radiation wind_speed soil_moisture \
        --split-date 2024-10-01 --anomaly-detection --synthetic --n-synthetic 100
"""

from __future__ import annotations

import argparse
from datetime import date

from data_ingestion.storage import load_dataset
from data_quality.pipeline import run_quality_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--columns", nargs="+", required=True)
    parser.add_argument("--split-date", type=date.fromisoformat, required=True)
    parser.add_argument("--anomaly-detection", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--n-synthetic", type=int, default=0)
    parser.add_argument("--contamination", type=float, default=0.05)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_dataset(args.dataset)

    result = run_quality_pipeline(
        df,
        numeric_columns=args.columns,
        split_date=args.split_date,
        include_anomaly_detection=args.anomaly_detection,
        include_synthetic=args.synthetic,
        n_synthetic_samples=args.n_synthetic,
        contamination=args.contamination,
        random_state=args.random_state,
    )

    print(f"Filas de entrenamiento: {len(result['train'])}")
    print(f"Filas de evaluación: {len(result['test'])}")
    print(f"Parámetros de escalado: {result['scaling_params']}")
    print(
        f"Faltantes (reporte de calidad, dataset crudo): {result['quality_report']['missing_pct']}"
    )


if __name__ == "__main__":
    main()
