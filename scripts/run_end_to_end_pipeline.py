"""Ejecuta el orquestador de punta a punta (architecture_integration.pipeline)
sobre un dataset ya consolidado: calidad, modelado predictivo, alertas y
retroalimentación humana en un único flujo.

Uso:
    python scripts/run_end_to_end_pipeline.py \
        --dataset melchor_romero_2024_consolidado \
        --label-column soil_moisture \
        --feature-columns soil_moisture solar_radiation relative_humidity \
        --split-date 2024-10-19 --model random_forest --anomaly-detection
"""

from __future__ import annotations

import argparse
from datetime import date

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.storage import load_dataset
from predictive_modeling.models import build_candidate_models


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--label-column", required=True)
    parser.add_argument("--feature-columns", nargs="+", required=True)
    parser.add_argument("--split-date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--model", choices=["logistic_regression", "random_forest"], default="random_forest"
    )
    parser.add_argument("--horizon-days", type=int, default=3)
    parser.add_argument("--percentile", type=float, default=20.0)
    parser.add_argument("--alert-threshold", type=float, default=0.5)
    parser.add_argument("--anomaly-detection", action="store_true")
    parser.add_argument("--contamination", type=float, default=0.05)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_dataset(args.dataset)
    model = build_candidate_models(random_state=args.random_state)[args.model]

    result = run_end_to_end_pipeline(
        df,
        label_column=args.label_column,
        feature_columns=args.feature_columns,
        split_date=args.split_date,
        model=model,
        horizon_days=args.horizon_days,
        percentile=args.percentile,
        alert_threshold=args.alert_threshold,
        include_anomaly_detection=args.anomaly_detection,
        contamination=args.contamination,
        random_state=args.random_state,
    )

    print(f"Filas de entrenamiento: {len(result['train'])}")
    print(f"Filas de evaluación: {len(result['test'])}")
    print(f"Alertas generadas: {int(result['alerts'].sum())} de {len(result['alerts'])}")
    print(
        "Estados del registro de retroalimentación: "
        f"{result['feedback_log']['estado_validacion'].value_counts().to_dict()}"
    )
    if "is_anomaly" in result["train"].columns:
        print(f"Filas anómalas en entrenamiento: {int(result['train']['is_anomaly'].sum())}")


if __name__ == "__main__":
    main()
