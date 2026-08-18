"""Registro de parámetros, versiones y resultados en MLflow (spec
experiment-runner, requirement "Registro de parámetros, versiones y
resultados en MLflow").

Convención de nested runs: un run padre por configuración experimental
con los parámetros de la configuración y las métricas agregadas
(media de cada métrica entre semillas), y un run hijo anidado por cada
semilla con su propio parámetro `seed` y sus métricas individuales.
"""

from __future__ import annotations

import mlflow
import pandas as pd

METRIC_COLUMNS = ["precision", "recall", "f1", "roc_auc"]


def log_configuration_results(config_name: str, config_params: dict, results: pd.DataFrame) -> str:
    """Registra `results` (una fila por semilla, con columnas `seed` y
    las métricas de `METRIC_COLUMNS`) en MLflow: un run padre con
    `config_params` y las métricas agregadas, y un run hijo anidado por
    cada semilla. Devuelve el `run_id` del run padre.
    """
    with mlflow.start_run(run_name=config_name) as parent_run:
        mlflow.log_param("config_name", config_name)
        for key, value in config_params.items():
            mlflow.log_param(key, value)

        for metric in METRIC_COLUMNS:
            mlflow.log_metric(f"{metric}_mean", float(results[metric].mean()))
            mlflow.log_metric(f"{metric}_std", float(results[metric].std()))

        for _, row in results.iterrows():
            with mlflow.start_run(run_name=f"{config_name}-seed{int(row['seed'])}", nested=True):
                mlflow.log_param("config_name", config_name)
                mlflow.log_param("seed", int(row["seed"]))
                for metric in METRIC_COLUMNS:
                    mlflow.log_metric(metric, float(row[metric]))

        return parent_run.info.run_id
