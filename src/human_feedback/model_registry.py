"""Registro y recuperación de versiones del modelo recalibrado en el
Model Registry de MLflow (spec alerting-ui, requirement "Disparo
manual de recalibración desde la interfaz, por sensor, con contrato de
compatibilidad de esquema"). El nombre de modelo registrado se deriva
por sensor (ADR-0008) — nunca es fijo.

Cada versión registrada guarda, además de `params`/`metrics`, la
metadata mínima para validar compatibilidad antes de reutilizar el
modelo: `feature_columns`, `horizon_days`, `threshold` y
`pipeline_version` (auditoría metodológica de la memoria técnica — ver
docs/research/hu8-analisis-resultados.md, sección 11). Si quien llama a
`load_latest_recalibrated_model` declara qué `feature_columns` espera,
la función valida que coincidan con las registradas antes de descargar
el modelo, y levanta `ModelContractMismatch` en vez de cargarlo en
silencio si no coinciden.
"""

from __future__ import annotations

import mlflow
import mlflow.sklearn

from data_ingestion.sensor_naming import registered_model_name_for

_FEATURE_COLUMNS_PARAM = "feature_columns"
_FEATURE_COLUMNS_SEPARATOR = "|"


class ModelContractMismatch(RuntimeError):
    """El modelo recalibrado más reciente registrado para un sensor no
    es compatible con las `feature_columns` que quien llama espera usar
    (por ejemplo, porque `FEATURE_COLUMNS` cambió desde que se registró
    esa versión). Se levanta antes de descargar/deserializar el modelo.
    """


def register_recalibrated_model(
    sensor_id: str,
    model: object,
    params: dict,
    metrics: dict,
    feature_columns: list[str],
    horizon_days: int,
    threshold: float,
    pipeline_version: str,
) -> str:
    """Registra `model` como una nueva versión en el Model Registry de
    MLflow bajo el nombre propio de `sensor_id`, junto con `params` y
    `metrics` en un run propio, más la metadata de contrato
    (`feature_columns`, `horizon_days`, `threshold`, `pipeline_version`)
    necesaria para validar compatibilidad en una carga posterior.
    Devuelve el número de versión registrada.
    """
    registered_model_name = registered_model_name_for(sensor_id)
    with mlflow.start_run(run_name="recalibracion") as run:
        mlflow.log_param(_FEATURE_COLUMNS_PARAM, _FEATURE_COLUMNS_SEPARATOR.join(feature_columns))
        mlflow.log_param("horizon_days", horizon_days)
        mlflow.log_param("threshold", threshold)
        mlflow.log_param("pipeline_version", pipeline_version)
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


def load_latest_recalibrated_model(
    sensor_id: str, expected_feature_columns: list[str] | None = None
) -> object | None:
    """Recupera la versión más reciente registrada para `sensor_id`, o
    `None` si todavía no se registró ninguna. Si MLflow no está
    disponible, la excepción se propaga sin capturarse (ADR-0006).

    Si se provee `expected_feature_columns`, valida que coincida
    exactamente con las `feature_columns` con las que se registró esa
    versión, ANTES de descargar el modelo — si no coinciden, levanta
    `ModelContractMismatch` en vez de cargar un modelo entrenado con un
    esquema de variables distinto al que el llamador va a usar. Si se
    omite (`None`, valor por defecto), no valida nada — comportamiento
    preexistente, para no romper llamadores que todavía no declaran qué
    esperan.
    """
    registered_model_name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{registered_model_name}'")
    if not versions:
        return None
    latest = max(versions, key=lambda v: int(v.version))

    if expected_feature_columns is not None:
        run = client.get_run(latest.run_id)
        registered_raw = run.data.params.get(_FEATURE_COLUMNS_PARAM)
        registered_columns = (
            registered_raw.split(_FEATURE_COLUMNS_SEPARATOR) if registered_raw else None
        )
        if registered_columns != list(expected_feature_columns):
            raise ModelContractMismatch(
                f"El modelo recalibrado más reciente de '{sensor_id}' (versión "
                f"{latest.version}) se registró con feature_columns={registered_columns}, "
                f"pero se pidió cargarlo esperando {list(expected_feature_columns)}. "
                "No se carga un modelo con un esquema de variables distinto."
            )

    return mlflow.sklearn.load_model(f"models:/{registered_model_name}/{latest.version}")
