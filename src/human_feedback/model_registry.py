"""Registro y recuperación de versiones del modelo recalibrado en el
Model Registry de MLflow (spec alerting-ui, requirement "Disparo
manual de recalibración desde la interfaz" y "Uso del modelo
recalibrado en el próximo pronóstico").
"""

from __future__ import annotations

import mlflow
import mlflow.sklearn
from mlflow.exceptions import MlflowException

REGISTERED_MODEL_NAME = "alerting_ui_recalibrated_model"


def register_recalibrated_model(model: object, params: dict, metrics: dict) -> str:
    """Registra `model` como una nueva versión en el Model Registry de
    MLflow bajo `REGISTERED_MODEL_NAME`, junto con `params` y `metrics`
    en un run propio. Devuelve el número de versión registrada.
    """
    with mlflow.start_run(run_name="recalibracion") as run:
        for key, value in params.items():
            mlflow.log_param(key, value)
        for key, value in metrics.items():
            mlflow.log_metric(key, value)
        mlflow.sklearn.log_model(
            model, artifact_path="model", registered_model_name=REGISTERED_MODEL_NAME
        )
        run_id = run.info.run_id

    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
    matching = [v for v in versions if v.run_id == run_id]
    return str(matching[0].version)


def load_latest_recalibrated_model() -> object | None:
    """Recupera la versión más reciente registrada en
    `REGISTERED_MODEL_NAME`, o `None` si todavía no se registró
    ninguna (primera corrida, sin recalibración previa).
    """
    client = mlflow.MlflowClient()
    try:
        versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
    except MlflowException:
        return None
    if not versions:
        return None
    latest = max(versions, key=lambda v: int(v.version))
    return mlflow.sklearn.load_model(f"models:/{REGISTERED_MODEL_NAME}/{latest.version}")
