"""MLflow registry with mandatory pre-download semantic compatibility checks."""

from __future__ import annotations

import json
from dataclasses import asdict

import mlflow
import mlflow.sklearn

from data_ingestion.sensor_naming import registered_model_name_for
from predictive_modeling.contract import FittedPredictor, ModelContractMismatch


def register_recalibrated_model(
    sensor_id, model: FittedPredictor, params: dict, metrics: dict
) -> str:
    if not isinstance(model, FittedPredictor):
        raise ModelContractMismatch("El registro requiere un predictor con contrato completo.")
    model.validate(model.contract)
    name = registered_model_name_for(sensor_id)
    with mlflow.start_run(run_name="recalibracion") as run:
        mlflow.log_param("model_contract", json.dumps(model.contract, sort_keys=True))
        mlflow.log_param("threshold", model.threshold)
        mlflow.log_param("trained_through", model.trained_through)
        mlflow.log_param("calibration_end", model.calibration_end)
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.log_dict(
            {k: v for k, v in asdict(model).items() if k not in {"model", "detector"}},
            "predictor_metadata.json",
        )
        # The sklearn flavor uses cloudpickle and preserves the fitted bundle.
        mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name=name)
        run_id = run.info.run_id
    versions = mlflow.MlflowClient().search_model_versions(f"name='{name}'")
    return str(next(v.version for v in versions if v.run_id == run_id))


def load_latest_recalibrated_model(sensor_id, expected_contract: dict) -> FittedPredictor | None:
    name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{name}'")
    if not versions:
        return None
    latest = max(versions, key=lambda v: int(v.version))
    raw = client.get_run(latest.run_id).data.params.get("model_contract")
    try:
        registered = json.loads(raw) if raw else None
    except (TypeError, ValueError) as error:
        raise ModelContractMismatch("Contrato registrado inválido.") from error
    if registered != expected_contract:
        raise ModelContractMismatch(
            f"Modelo de {sensor_id}, versión {latest.version}: "
            "contrato incompatible o histórico incompleto."
        )
    predictor = mlflow.sklearn.load_model(f"models:/{name}/{latest.version}")
    if not isinstance(predictor, FittedPredictor):
        raise ModelContractMismatch("El artefacto no contiene un predictor versionado.")
    predictor.validate(expected_contract)
    return predictor
