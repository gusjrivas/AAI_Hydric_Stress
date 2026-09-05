"""Re-ejecuta los escenarios de escasez y ruido de HU8 (sección 8 y 9 de
`docs/research/hu8-analisis-resultados.md`) sobre el pipeline corregido
(auditoría de fuga temporal + auditoría de validación cruzada purgada y
consistencia de detección de anomalías), y los registra en MLflow bajo
el mismo experimento nuevo que `scripts/run_hu7_experiments.py`
(`hu7-epica4-purged-cv`), separado de las corridas históricas y de la
ronda anterior (`hu7-epica4-leakage-fix`).

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
from predictive_modeling.models import build_candidate_models

DATASET_NAME = "melchor_romero_2024_consolidado"
FEATURE_COLUMNS = ["soil_moisture", "solar_radiation", "relative_humidity"]
LABEL_COLUMN = "soil_moisture"
HORIZON_DAYS = 3
PERCENTILE = 20.0
LAGS = [1, 2, 3]
ROLLING_WINDOWS = [3, 7]
ALERT_THRESHOLD = 0.5
CONTAMINATION = 0.05
MODEL_NAME = "random_forest"
SEEDS = [0, 1, 2, 3, 4]
PIPELINE_VERSION = "purged_cv_v2"
EXPERIMENT_NAME = "hu7-epica4-purged-cv"

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
    model_hyperparameters = build_candidate_models(random_state=SEEDS[0])[MODEL_NAME].get_params()

    for scenario_name, scenario_kwargs in SCENARIOS.items():
        results = run_configuration(
            df,
            label_column=LABEL_COLUMN,
            feature_columns=FEATURE_COLUMNS,
            split_date=split_date,
            model_name=MODEL_NAME,
            include_anomaly_detection=False,
            include_synthetic=False,
            seeds=SEEDS,
            alert_threshold=ALERT_THRESHOLD,
            horizon_days=HORIZON_DAYS,
            percentile=PERCENTILE,
            lags=LAGS,
            rolling_windows=ROLLING_WINDOWS,
            contamination=CONTAMINATION,
            **scenario_kwargs,
        )

        config_params = {
            **scenario_kwargs,
            "dataset": DATASET_NAME,
            "split_date": str(split_date),
            "feature_columns": ",".join(FEATURE_COLUMNS),
            "label_column": LABEL_COLUMN,
            "horizon_days": HORIZON_DAYS,
            "percentile": PERCENTILE,
            "lags": str(LAGS),
            "rolling_windows": str(ROLLING_WINDOWS),
            "alert_threshold": ALERT_THRESHOLD,
            "contamination": CONTAMINATION,
            "model_name": MODEL_NAME,
            "model_hyperparameters": str(model_hyperparameters),
            "seeds": str(SEEDS),
            "pipeline_version": PIPELINE_VERSION,
            "commit_sha": commit_sha,
            "run_date": run_date,
        }

        run_id = log_configuration_results(scenario_name, config_params, results)
        print(
            f"[{scenario_name}] run_id={run_id} "
            f"f1_mean={results['f1'].mean():.4f} f1_std={results['f1'].std():.4f} "
            f"mcc_mean={results['mcc'].mean():.4f}"
        )


if __name__ == "__main__":
    main()
