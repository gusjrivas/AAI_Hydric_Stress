"""MLflow registry with mandatory pre-download semantic compatibility checks."""

from __future__ import annotations

import json
from dataclasses import asdict

import mlflow
import mlflow.sklearn

from data_ingestion.sensor_naming import registered_model_name_for
from human_feedback.lineage import RecalibrationLineage
from predictive_modeling.contract import FittedPredictor, ModelContractMismatch


def register_recalibrated_model(
    sensor_id,
    model: FittedPredictor,
    params: dict,
    metrics: dict,
    lineage: RecalibrationLineage | None = None,
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
        if lineage is not None:
            resolved_version = _resolve_version_for_run(name, run_id)
            payload = lineage.to_dict()
            payload["mlflow_model_version"] = resolved_version
            mlflow.log_dict(payload, "recalibration_lineage.json")
            mlflow.log_param("recalibration_id", lineage.recalibration_id)
            mlflow.log_param("source_model_id", lineage.source_model_id)
            mlflow.log_param("successor_model_id", lineage.successor_model_id)
            mlflow.log_param("dataset_fingerprint", lineage.dataset_fingerprint)
    versions = mlflow.MlflowClient().search_model_versions(f"name='{name}'")
    return str(next(v.version for v in versions if v.run_id == run_id))


def _resolve_version_for_run(name: str, run_id: str) -> str | None:
    versions = mlflow.MlflowClient().search_model_versions(f"name='{name}'")
    match = next((v for v in versions if v.run_id == run_id), None)
    return str(match.version) if match is not None else None


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


def load_recalibration_lineage(sensor_id, successor_model_id: str) -> RecalibrationLineage | None:
    """Recupera el evento de linaje cuyo `successor_model_id` coincide,
    validando que el artefacto persistido tenga la forma esperada.
    """
    name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    for version in client.search_model_versions(f"name='{name}'"):
        data = _download_lineage_payload(client, version.run_id)
        if data is not None and data.get("successor_model_id") == successor_model_id:
            return RecalibrationLineage.from_dict(data)
    return None


def list_recalibration_lineage(sensor_id) -> list[RecalibrationLineage]:
    """Recupera, en orden cronológico, todos los eventos de linaje
    registrados para un sensor — permite reconstruir la cadena completa
    (p. ej. feedback A → A → B, feedback B → B → C).
    """
    name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    versions = sorted(client.search_model_versions(f"name='{name}'"), key=lambda v: int(v.version))
    lineage = []
    for version in versions:
        data = _download_lineage_payload(client, version.run_id)
        if data is not None:
            lineage.append(RecalibrationLineage.from_dict(data))
    return lineage


def _download_lineage_payload(client, run_id: str) -> dict | None:
    try:
        path = client.download_artifacts(run_id, "recalibration_lineage.json")
        with open(path, encoding="utf-8") as lineage_file:
            return json.load(lineage_file)
    except (OSError, ValueError, mlflow.exceptions.MlflowException):
        return None


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
