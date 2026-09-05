"""Registro de parámetros, versiones y resultados en MLflow (spec
experiment-runner, requirement "Registro de parámetros, versiones y
resultados en MLflow").

Convención de nested runs: un run padre por configuración experimental
con los parámetros de la configuración y las métricas agregadas
(media de cada métrica entre semillas), y un run hijo anidado por cada
semilla con su propio parámetro `seed` y sus métricas individuales.
"""

from __future__ import annotations

import json

import mlflow
import pandas as pd


def log_configuration_results(config_name: str, config_params: dict, results: pd.DataFrame) -> str:
    """Registra `results` (una fila por semilla, con columna `seed` y
    una columna por cada métrica presente) en MLflow: un run padre con
    `config_params` y las métricas agregadas, y un run hijo anidado por
    cada semilla. Cualquier columna de `results` distinta de `seed` se
    registra como métrica — no hay una lista fija de nombres de métrica,
    para no tener que editar este módulo cada vez que se agrega una
    métrica o un baseline nuevo (ver
    `docs/research/hu8-analisis-resultados.md`, sección 11, MCC/balanced
    accuracy/average precision/baselines agregados en la misma
    auditoría). Devuelve el `run_id` del run padre.
    """
    metric_columns = [column for column in results.columns if column != "seed"]

    with mlflow.start_run(run_name=config_name) as parent_run:
        mlflow.log_param("config_name", config_name)
        for key, value in config_params.items():
            mlflow.log_param(key, value)
        mlflow.log_dict(config_params, "configuration.json")

        for metric in metric_columns:
            mlflow.log_metric(f"{metric}_mean", float(results[metric].mean()))
            mlflow.log_metric(f"{metric}_std", float(results[metric].std()))

        for _, row in results.iterrows():
            with mlflow.start_run(run_name=f"{config_name}-seed{int(row['seed'])}", nested=True):
                mlflow.log_param("config_name", config_name)
                mlflow.log_param("seed", int(row["seed"]))
                for metric in metric_columns:
                    mlflow.log_metric(metric, float(row[metric]))
                artifact = next(
                    (
                        a
                        for a in results.attrs.get("artifacts", [])
                        if a["seed"] == int(row["seed"])
                    ),
                    None,
                )
                if artifact is not None:
                    metadata = {k: v for k, v in artifact.items() if k != "predictions"}
                    mlflow.log_dict(metadata, "effective_configuration.json")
                    records = json.loads(
                        artifact["predictions"].to_json(orient="records", date_format="iso")
                    )
                    mlflow.log_dict({"rows": records}, "predictions.json")
                    mlflow.set_tag("evaluation_status", "empty" if not records else "evaluated")

        return parent_run.info.run_id
