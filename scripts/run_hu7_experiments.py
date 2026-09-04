"""Re-ejecuta las 4 configuraciones experimentales de la Épica 4 (HU7)
sobre el pipeline corregido (auditoría de fuga temporal: imputación
causal + umbral de estrés congelado en entrenamiento), y las registra
en MLflow bajo un experimento nuevo, separado de las corridas
históricas (`hu7-epica4`), para poder comparar antes/después sin
sobrescribir la evidencia histórica.

Parámetros reconstruidos a partir de lo documentado en
`docs/research/hu8-analisis-resultados.md` y `backend/app/config.py`,
dado que la ejecución original de HU7 fue ad hoc y nunca quedó
committeada como script (`openspec/changes/add-experiment-execution/
proposal.md`, "Código afectado: ninguno nuevo") — ver el informe final
de esta auditoría para el detalle de qué está verificado literalmente
contra el historial y qué es una reconstrucción razonable.

Uso:
    python scripts/run_hu7_experiments.py
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
N_SYNTHETIC_SAMPLES = 100
EXPERIMENT_NAME = "hu7-epica4-leakage-fix"

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

    for config_name, flags in CONFIGURATIONS.items():
        results = run_configuration(
            df,
            label_column=LABEL_COLUMN,
            feature_columns=FEATURE_COLUMNS,
            split_date=split_date,
            model_name="random_forest",
            seeds=SEEDS,
            n_synthetic_samples=N_SYNTHETIC_SAMPLES if flags["include_synthetic"] else 0,
            **flags,
        )

        config_params = {
            **flags,
            "model_name": "random_forest",
            "n_synthetic_samples": N_SYNTHETIC_SAMPLES if flags["include_synthetic"] else 0,
            "seeds": str(SEEDS),
            "pipeline_version": "leakage_fix",
            "commit_sha": commit_sha,
            "run_date": run_date,
        }

        run_id = log_configuration_results(config_name, config_params, results)
        print(
            f"[{config_name}] run_id={run_id} "
            f"f1_mean={results['f1'].mean():.4f} f1_std={results['f1'].std():.4f} "
            f"roc_auc_mean={results['roc_auc'].mean():.4f}"
        )


if __name__ == "__main__":
    main()
