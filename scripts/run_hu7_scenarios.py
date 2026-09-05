"""Re-ejecuta los escenarios de escasez y ruido de HU8 (sección 8 y 9 de
`docs/research/hu8-analisis-resultados.md`) sobre el pipeline corregido
(auditoría de fuga temporal), y los registra en MLflow bajo el mismo
experimento nuevo que `scripts/run_hu7_experiments.py`
(`hu7-epica4-leakage-fix`), separado de las corridas históricas.

Uso:
    python scripts/run_hu7_scenarios.py
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone

import mlflow

from data_ingestion.storage import load_dataset
from experiment_runner.mlflow_logging import log_configuration_results
from experiment_runner.runner import run_configuration

DATASET_NAME = "melchor_romero_2024_consolidado"
FEATURE_COLUMNS = ["soil_moisture", "solar_radiation", "relative_humidity"]
LABEL_COLUMN = "soil_moisture"
SEEDS = [0, 1, 2, 3, 4]
EXPERIMENT_NAME = "hu7-epica4-leakage-fix"

SCENARIOS = {
    "escasez_train_fraction_0.5": {"train_fraction": 0.5, "noise_std_ratio": 0.0},
    "ruido_noise_std_ratio_0.3": {"train_fraction": 1.0, "noise_std_ratio": 0.3},
}


def _commit_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main() -> None:
    df = load_dataset(DATASET_NAME)
    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    mlflow.set_experiment(EXPERIMENT_NAME)
    commit_sha = _commit_sha()
    run_date = datetime.now(timezone.utc).isoformat()

    for scenario_name, scenario_kwargs in SCENARIOS.items():
        results = run_configuration(
            df,
            label_column=LABEL_COLUMN,
            feature_columns=FEATURE_COLUMNS,
            split_date=split_date,
            model_name="random_forest",
            include_anomaly_detection=False,
            include_synthetic=False,
            seeds=SEEDS,
            **scenario_kwargs,
        )

        config_params = {
            **scenario_kwargs,
            "model_name": "random_forest",
            "seeds": str(SEEDS),
            "pipeline_version": "leakage_fix",
            "commit_sha": commit_sha,
            "run_date": run_date,
        }

        run_id = log_configuration_results(scenario_name, config_params, results)
        print(
            f"[{scenario_name}] run_id={run_id} "
            f"f1_mean={results['f1'].mean():.4f} f1_std={results['f1'].std():.4f}"
        )


if __name__ == "__main__":
    main()
