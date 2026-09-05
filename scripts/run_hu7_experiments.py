"""Re-ejecuta las 4 configuraciones experimentales de la Épica 4 (HU7)
sobre el pipeline corregido (auditoría de fuga temporal en imputación y
umbral de estrés, más la auditoría posterior de validación cruzada
purgada y consistencia de detección de anomalías), y las registra en
MLflow bajo un experimento nuevo, separado de las corridas históricas
(`hu7-epica4`) y de la ronda anterior (`hu7-epica4-leakage-fix`), para
poder comparar sin sobrescribir evidencia previa.

Toda la configuración de una corrida (dataset, partición, columnas,
horizonte, percentil, retardos/ventanas, umbral de alerta,
contaminación, modelo e hiperparámetros, semillas, cantidad de datos
sintéticos, commit y versión del pipeline) se declara explícitamente
acá y se registra como parámetro de MLflow — auditoría de
reproducibilidad, ver `docs/research/hu8-analisis-resultados.md`,
sección 11. Nada de esto depende de un valor por defecto implícito de
`run_end_to_end_pipeline`.

Uso:
    python scripts/run_hu7_experiments.py
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone

import mlflow

from data_ingestion.storage import DEFAULT_DATA_DIR, load_dataset
from experiment_runner.mlflow_logging import log_configuration_results
from experiment_runner.provenance import experiment_provenance
from experiment_runner.runner import run_configuration
from predictive_modeling.models import build_candidate_models

# --- Configuración reproducible de esta corrida ---------------------------
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
N_SYNTHETIC_SAMPLES = 100
PIPELINE_VERSION = "controlled_daily_v3"
EXPERIMENT_NAME = "hu7-controlled-daily-v3"
# ---------------------------------------------------------------------------

CONFIGURATIONS = {
    "base": {"include_anomaly_detection": False, "include_synthetic": False},
    "sinteticos": {"include_anomaly_detection": False, "include_synthetic": True},
    "anomalias": {"include_anomaly_detection": True, "include_synthetic": False},
    "completa": {"include_anomaly_detection": True, "include_synthetic": True},
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

    for config_name, flags in CONFIGURATIONS.items():
        n_synthetic_samples = N_SYNTHETIC_SAMPLES if flags["include_synthetic"] else 0

        results = run_configuration(
            df,
            label_column=LABEL_COLUMN,
            feature_columns=FEATURE_COLUMNS,
            split_date=split_date,
            model_name=MODEL_NAME,
            seeds=SEEDS,
            n_synthetic_samples=n_synthetic_samples,
            alert_threshold=ALERT_THRESHOLD,
            horizon_days=HORIZON_DAYS,
            percentile=PERCENTILE,
            lags=LAGS,
            rolling_windows=ROLLING_WINDOWS,
            contamination=CONTAMINATION,
            **flags,
        )

        config_params = {
            **flags,
            "dataset": DATASET_NAME,
            "split_date": str(split_date),
            "raw_input_features": ",".join(FEATURE_COLUMNS),
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
            "n_synthetic_samples": n_synthetic_samples,
            "pipeline_version": PIPELINE_VERSION,
            "commit_sha": commit_sha,
            "run_date": run_date,
            **experiment_provenance(DEFAULT_DATA_DIR / f"{DATASET_NAME}.parquet"),
        }

        run_id = log_configuration_results(config_name, config_params, results)
        print(
            f"[{config_name}] run_id={run_id} "
            f"f1_mean={results['f1'].mean():.4f} f1_std={results['f1'].std():.4f} "
            f"roc_auc_mean={results['roc_auc'].mean():.4f} "
            f"mcc_mean={results['mcc'].mean():.4f} "
            f"always_stress_f1_mean={results['always_stress_f1'].mean():.4f}"
        )


if __name__ == "__main__":
    main()
