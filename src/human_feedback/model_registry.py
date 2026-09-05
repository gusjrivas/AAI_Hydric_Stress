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


def register_predictor(sensor_id, model: FittedPredictor, *, kind: str = "initial") -> str:
    """Persist an issued predictor so feedback can resolve it after restart."""
    if not isinstance(model, FittedPredictor):
        raise ModelContractMismatch("El registro requiere un predictor con contrato completo.")
    model.validate(model.contract)
    name = registered_model_name_for(sensor_id) + "__issued"
    mlflow.set_experiment("alerting-ui")
    with mlflow.start_run(run_name=f"predictor-{kind}") as run:
        mlflow.log_param("model_contract", json.dumps(model.contract, sort_keys=True))
        mlflow.log_param("threshold", model.threshold)
        mlflow.log_param("trained_through", model.trained_through)
        mlflow.log_param("calibration_end", model.calibration_end)
        mlflow.log_param("predictor_kind", kind)
        mlflow.log_dict(
            {k: v for k, v in asdict(model).items() if k not in {"model", "detector"}},
            "predictor_metadata.json",
        )
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
    return _load_registered_version(latest, expected_contract)


def load_predictor_by_id(
    sensor_id, model_id: str, expected_contract: dict
) -> FittedPredictor | None:
    """Load the exact predictor that issued a feedback row."""
    name = registered_model_name_for(sensor_id) + "__issued"
    client = mlflow.MlflowClient()
    for version in client.search_model_versions(f"name='{name}'"):
        try:
            metadata_path = client.download_artifacts(version.run_id, "predictor_metadata.json")
            with open(metadata_path, encoding="utf-8") as metadata_file:
                metadata = json.load(metadata_file)
        except (OSError, ValueError, mlflow.exceptions.MlflowException):
            continue
        if metadata.get("model_id") == model_id:
            return _load_registered_version(version, expected_contract)
    return None


def _load_registered_version(latest, expected_contract: dict) -> FittedPredictor:
    client = mlflow.MlflowClient()
    raw = client.get_run(latest.run_id).data.params.get("model_contract")
    try:
        registered = json.loads(raw) if raw else None
    except (TypeError, ValueError) as error:
        raise ModelContractMismatch("Contrato registrado inválido.") from error
    if registered != expected_contract:
        raise ModelContractMismatch(
            "Modelo registrado: contrato incompatible o histórico incompleto."
        )
    name = latest.name
    predictor = mlflow.sklearn.load_model(f"models:/{name}/{latest.version}")
    if not isinstance(predictor, FittedPredictor):
        raise ModelContractMismatch("El artefacto no contiene un predictor versionado.")
    predictor.validate(expected_contract)
    return predictor
