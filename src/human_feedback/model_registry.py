"""MLflow registry with mandatory pre-download semantic compatibility checks."""

from __future__ import annotations

import json
from dataclasses import asdict, replace

import mlflow
import mlflow.sklearn

from data_ingestion.sensor_naming import registered_model_name_for
from human_feedback.lineage import LineageValidationError, RecalibrationLineage
from predictive_modeling.contract import FittedPredictor, ModelContractMismatch


def _validate_lineage_matches_model(
    sensor_id, model: FittedPredictor, lineage: RecalibrationLineage
) -> None:
    """Verifica que el linaje provisto describa efectivamente al predictor
    que se está registrando, antes de escribir nada en MLflow.
    """
    mismatches = []
    if lineage.sensor_id != sensor_id:
        mismatches.append("sensor_id")
    if lineage.successor_model_id != model.model_id:
        mismatches.append("successor_model_id")
    if lineage.successor_trained_through != model.trained_through:
        mismatches.append("successor_trained_through")
    if lineage.contract_version != model.contract.get("contract_version"):
        mismatches.append("contract_version")
    if lineage.pipeline_version != model.contract.get("pipeline_version"):
        mismatches.append("pipeline_version")
    if mismatches:
        raise LineageValidationError(
            "El linaje no corresponde al predictor que se registra: " f"{', '.join(mismatches)}."
        )


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
    if lineage is not None:
        _validate_lineage_matches_model(sensor_id, model, lineage)
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
        if lineage is not None:
            # El linaje se valida y persiste ANTES de registrar el predictor
            # (`log_model(..., registered_model_name=...)` más abajo): así
            # una versión registrada nunca queda sin su artefacto de linaje.
            # `mlflow_model_version` todavía no existe en este punto (la
            # versión se asigna recién al registrar) y se resuelve
            # dinámicamente al leer el linaje (`load_recalibration_lineage`/
            # `list_recalibration_lineage`), sin reescribir este artefacto
            # después.
            mlflow.log_dict(lineage.to_dict(), "recalibration_lineage.json")
            mlflow.log_param("recalibration_id", lineage.recalibration_id)
            mlflow.log_param("source_model_id", lineage.source_model_id)
            mlflow.log_param("successor_model_id", lineage.successor_model_id)
            mlflow.log_param("dataset_fingerprint", lineage.dataset_fingerprint)
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


def _load_lineage_for_version(client, version) -> RecalibrationLineage | None:
    """Descarga y valida el linaje de una versión ya registrada,
    resolviendo `mlflow_model_version` desde la versión efectivamente
    asociada a ese `run_id` (nunca desde lo que quedó grabado en el
    artefacto, que se escribió antes de que la versión existiera).
    """
    data = _download_lineage_payload(client, version.run_id)
    if data is None:
        return None
    lineage = RecalibrationLineage.from_dict(data)
    return replace(lineage, mlflow_model_version=str(version.version))


def load_recalibration_lineage(sensor_id, successor_model_id: str) -> RecalibrationLineage | None:
    """Recupera el evento de linaje cuyo `successor_model_id` coincide,
    validando que el artefacto persistido tenga la forma esperada. Solo
    considera versiones efectivamente registradas: un run con artefacto
    de linaje pero sin versión registrada (huérfano, p. ej. porque el
    registro se interrumpió después de persistir el linaje) queda fuera
    de esta búsqueda.
    """
    name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    for version in client.search_model_versions(f"name='{name}'"):
        lineage = _load_lineage_for_version(client, version)
        if lineage is not None and lineage.successor_model_id == successor_model_id:
            return lineage
    return None


def list_recalibration_lineage(sensor_id) -> list[RecalibrationLineage]:
    """Recupera, en orden cronológico, todos los eventos de linaje
    registrados para un sensor — permite reconstruir la cadena completa
    (p. ej. feedback A → A → B, feedback B → B → C). Igual que
    `load_recalibration_lineage`, solo considera versiones efectivamente
    registradas.
    """
    name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    versions = sorted(client.search_model_versions(f"name='{name}'"), key=lambda v: int(v.version))
    lineage = [_load_lineage_for_version(client, version) for version in versions]
    return [entry for entry in lineage if entry is not None]


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
