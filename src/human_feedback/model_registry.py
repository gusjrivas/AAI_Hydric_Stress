"""Registro y recuperación de versiones del modelo recalibrado en el
Model Registry de MLflow (spec alerting-ui, requirement "Disparo
manual de recalibración desde la interfaz, por sensor"). El nombre de
modelo registrado se deriva por sensor (ADR-0008) — nunca es fijo.
"""

from __future__ import annotations

import mlflow
import mlflow.sklearn

from data_ingestion.sensor_naming import registered_model_name_for


def register_recalibrated_model(
    sensor_id: str, model: object, params: dict, metrics: dict
) -> str:
    """Registra `model` como una nueva versión en el Model Registry de
    MLflow bajo el nombre propio de `sensor_id`, junto con `params` y
    `metrics` en un run propio. Devuelve el número de versión
    registrada.
    """
    registered_model_name = registered_model_name_for(sensor_id)
    with mlflow.start_run(run_name="recalibracion") as run:
        for key, value in params.items():
            mlflow.log_param(key, value)
        for key, value in metrics.items():
            mlflow.log_metric(key, value)
        mlflow.sklearn.log_model(
            model, artifact_path="model", registered_model_name=registered_model_name
        )
        run_id = run.info.run_id

    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{registered_model_name}'")
    matching = [v for v in versions if v.run_id == run_id]
    return str(matching[0].version)


def load_latest_recalibrated_model(sensor_id: str) -> object | None:
    """Recupera la versión más reciente registrada para `sensor_id`, o
    `None` si todavía no se registró ninguna. Si MLflow no está
    disponible, la excepción se propaga sin capturarse (ADR-0006).
    """
    registered_model_name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{registered_model_name}'")
    if not versions:
        return None
    latest = max(versions, key=lambda v: int(v.version))
    return mlflow.sklearn.load_model(f"models:/{registered_model_name}/{latest.version}")
