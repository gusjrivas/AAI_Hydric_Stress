"""MLflow registry with mandatory pre-download semantic compatibility checks."""

from __future__ import annotations

import json
from dataclasses import asdict, replace

import mlflow
import mlflow.sklearn

from data_ingestion.sensor_naming import registered_model_name_for
from human_feedback.lineage import (
    LINEAGE_VERSION_1,
    SUPPORTED_LINEAGE_VERSIONS,
    LineageValidationError,
    RecalibrationLineage,
)
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
            #
            # Estas líneas escriben varios parámetros por separado: MLflow no
            # garantiza que un fallo a mitad de este bloque (proceso
            # interrumpido, error de red) sea todo-o-nada. La detección de
            # declaraciones parciales (`_run_declares_lineage` /
            # `_load_lineage_for_version`) existe justamente para ese caso —
            # no depende de que este bloque sea atómico.
            mlflow.log_dict(lineage.to_dict(), "recalibration_lineage.json")
            mlflow.log_param("recalibration_id", lineage.recalibration_id)
            mlflow.log_param("source_model_id", lineage.source_model_id)
            mlflow.log_param("successor_model_id", lineage.successor_model_id)
            mlflow.log_param("dataset_fingerprint", lineage.dataset_fingerprint)
            mlflow.log_param("lineage_version", lineage.lineage_version)
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


# Parámetros que una recalibración con linaje completo debe tener TODOS.
# `dataset_fingerprint` está incluido aquí (se exige una vez que se decidió
# que el run declara linaje) pero deliberadamente NO en
# `_LINEAGE_DECLARATION_MARKERS` más abajo: por sí solo no es específico de
# una recalibración HITL (nada impide que otro tipo de run futuro también lo
# loguee), así que no alcanza para decidir si un run "declara linaje".
_LINEAGE_REQUIRED_PARAMS = (
    "recalibration_id",
    "source_model_id",
    "successor_model_id",
    "dataset_fingerprint",
)

# Parámetros específicos de una recalibración HITL: la presencia de
# CUALQUIERA de ellos ya indica que el run intenta declarar linaje (aunque
# el registro se haya interrumpido a mitad de camino y falten otros). No se
# usa `all(...)` para esta detección — un run con una persistencia parcial
# (algunos de estos parámetros, pero no todos los de
# `_LINEAGE_REQUIRED_PARAMS`) igual debe detectarse como "declara linaje" y
# fallar explícitamente, no clasificarse como histórico sin linaje.
_LINEAGE_DECLARATION_MARKERS = (
    "recalibration_id",
    "source_model_id",
    "successor_model_id",
    "lineage_version",
)


def _run_declares_lineage(run_params: dict) -> bool:
    """Un run se considera que declara (o intentó declarar) linaje si tiene
    presente CUALQUIERA de los marcadores específicos de una recalibración
    HITL (`_LINEAGE_DECLARATION_MARKERS`). Que un run tenga TODOS los
    parámetros de `_LINEAGE_REQUIRED_PARAMS` no se verifica acá — eso lo
    hace `_require_complete_lineage_declaration`, una vez que ya se decidió
    que el run declara linaje.

    MLflow no garantiza que loguear varios parámetros desde el mismo bloque
    de código sea atómico (un fallo a mitad de camino, un proceso
    interrumpido, pueden dejar un subconjunto persistido); esta detección
    existe justamente para ese caso, no asume atomicidad transaccional.
    """
    return any(param in run_params for param in _LINEAGE_DECLARATION_MARKERS)


def _require_complete_lineage_declaration(run_params: dict, context: str) -> None:
    """Un run que declara linaje (`_run_declares_lineage` dio `True`) debe
    tener TODOS los parámetros de `_LINEAGE_REQUIRED_PARAMS`. Si falta
    alguno, es una persistencia parcial/corrupta — nunca se degrada a
    `None` ni se completa con valores por defecto.
    """
    missing = [param for param in _LINEAGE_REQUIRED_PARAMS if param not in run_params]
    if missing:
        raise LineageValidationError(
            f"El run declara linaje pero le faltan parámetros obligatorios "
            f"({context}): {', '.join(missing)}."
        )


def _validate_lineage_version_consistency(
    run_params: dict, lineage: RecalibrationLineage, context: str
) -> None:
    """Cruza el parámetro MLflow `lineage_version` (si está presente)
    contra el `lineage_version` efectivamente contenido en el artefacto.

    - Ausencia del parámetro solo es válida cuando el artefacto es
      genuinamente `LINEAGE_VERSION_1` (la única versión que existió antes
      de que este parámetro se empezara a loguear); un artefacto de una
      versión posterior sin el parámetro nunca se interpreta como V1
      histórico.
    - Un parámetro presente debe ser un entero soportado y coincidir
      exactamente con el del artefacto; cualquier diferencia (parámetro
      V2 + artefacto V1, parámetro V1 + artefacto V2, parámetro
      inválido/no soportado) falla explícitamente.
    """
    raw_param_version = run_params.get("lineage_version")
    if raw_param_version is None:
        if lineage.lineage_version != LINEAGE_VERSION_1:
            raise LineageValidationError(
                f"El artefacto declara lineage_version={lineage.lineage_version!r} pero el "
                f"run no tiene el parámetro `lineage_version` ({context}); la ausencia del "
                f"parámetro solo es válida para un evento histórico lineage_version="
                f"{LINEAGE_VERSION_1}."
            )
        return
    try:
        param_version = int(raw_param_version)
    except (TypeError, ValueError) as error:
        raise LineageValidationError(
            f"El parámetro `lineage_version` no es un entero válido ({context}): "
            f"{raw_param_version!r}."
        ) from error
    if param_version not in SUPPORTED_LINEAGE_VERSIONS:
        raise LineageValidationError(
            f"El parámetro `lineage_version` no es una versión soportada ({context}): "
            f"{param_version!r}. Soportadas: {SUPPORTED_LINEAGE_VERSIONS}."
        )
    if param_version != lineage.lineage_version:
        raise LineageValidationError(
            f"El parámetro `lineage_version`={param_version} es inconsistente con el "
            f"lineage_version del artefacto ({lineage.lineage_version!r}) ({context})."
        )


def _load_lineage_for_version(client, version) -> RecalibrationLineage | None:
    """Recuperación *fail-closed* del linaje de una versión ya registrada.

    - Si la versión nunca declaró linaje (no tiene ninguno de los
      marcadores específicos, `_LINEAGE_DECLARATION_MARKERS`), devuelve
      `None` — comportamiento retrocompatible con versiones históricas
      anteriores a esta capacidad. `dataset_fingerprint` por sí solo, sin
      ningún otro marcador, tampoco cuenta como declaración: no es
      específico de una recalibración HITL.
    - Si la versión declara linaje (aunque sea de forma parcial), debe
      poder reconstruirse por completo: faltan parámetros obligatorios,
      artefacto ausente, fallo de descarga, contenido ilegible, JSON
      inválido, semántica inválida, o inconsistencia entre el artefacto y
      los parámetros ya persistidos levantan `LineageValidationError` en
      vez de degradar silenciosamente a `None`.

    `mlflow_model_version` se resuelve aquí desde la versión efectivamente
    asociada a ese `run_id` (nunca desde lo que quedó grabado en el
    artefacto, que se escribió antes de que la versión existiera).
    """
    run_params = client.get_run(version.run_id).data.params
    if not _run_declares_lineage(run_params):
        return None

    context = f"sensor version={version.version} run_id={version.run_id}"
    _require_complete_lineage_declaration(run_params, context)
    try:
        artifact_path = client.download_artifacts(version.run_id, "recalibration_lineage.json")
    except (OSError, mlflow.exceptions.MlflowException) as error:
        raise LineageValidationError(
            f"La versión declara linaje pero su artefacto no pudo descargarse ({context})."
        ) from error
    try:
        with open(artifact_path, encoding="utf-8") as lineage_file:
            data = json.load(lineage_file)
    except (OSError, ValueError) as error:
        raise LineageValidationError(
            f"El artefacto de linaje es ilegible o no es JSON válido ({context})."
        ) from error
    try:
        lineage = RecalibrationLineage.from_dict(data)
    except LineageValidationError as error:
        raise LineageValidationError(
            f"El artefacto de linaje incumple la semántica del contrato ({context}): {error}"
        ) from error
    except (TypeError, KeyError, AttributeError) as error:
        # Red de seguridad: `RecalibrationLineage.from_dict` ya normaliza toda
        # estructura inválida a `LineageValidationError`, pero esta capa nunca
        # debe dejar escapar una excepción estructural sin envolver.
        raise LineageValidationError(
            f"El artefacto de linaje tiene una estructura inválida ({context}): {error}"
        ) from error

    _validate_lineage_version_consistency(run_params, lineage, context)

    mismatches = [
        param
        for param in _LINEAGE_REQUIRED_PARAMS
        if run_params.get(param) != getattr(lineage, param)
    ]
    if mismatches:
        raise LineageValidationError(
            f"El artefacto de linaje es inconsistente con los parámetros registrados "
            f"({context}): {', '.join(mismatches)}."
        )

    return replace(lineage, mlflow_model_version=str(version.version))


def load_recalibration_lineage(sensor_id, successor_model_id: str) -> RecalibrationLineage | None:
    """Recupera el evento de linaje cuyo `successor_model_id` coincide.
    Ver `_load_lineage_for_version` para la semántica *fail-closed*: solo
    devuelve `None` para versiones que nunca declararon linaje; un
    linaje declarado pero corrupto levanta `LineageValidationError`.
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
    (p. ej. feedback A → A → B, feedback B → B → C). Las versiones
    históricas que nunca declararon linaje se omiten silenciosamente; si
    alguna versión declaró linaje y está corrupta, la función propaga
    `LineageValidationError` en vez de devolver una cadena parcial que
    aparente estar completa.
    """
    name = registered_model_name_for(sensor_id)
    client = mlflow.MlflowClient()
    versions = sorted(client.search_model_versions(f"name='{name}'"), key=lambda v: int(v.version))
    lineage = [_load_lineage_for_version(client, version) for version in versions]
    return [entry for entry in lineage if entry is not None]


def get_latest_recalibrated_version(sensor_id) -> str | None:
    """Número de versión MLflow más reciente registrada para `sensor_id`
    en el Model Registry de recalibraciones, o `None` si nunca se
    recalibró. Solo lectura de metadata de versión — no descarga ni
    valida el estimador (a diferencia de `load_latest_recalibrated_model`).
    """
    name = registered_model_name_for(sensor_id)
    versions = mlflow.MlflowClient().search_model_versions(f"name='{name}'")
    if not versions:
        return None
    return str(max(int(v.version) for v in versions))


def load_latest_issued_predictor_metadata(sensor_id) -> dict | None:
    """Metadata (sin el estimador) del último predictor "issued"
    registrado para `sensor_id` (`register_predictor`, invocado por
    `POST /forecast/{sensor_id}/run`), con `issued_model_version`
    agregado (la versión MLflow de ese registro). Devuelve `None` si
    todavía no se corrió ningún pronóstico para ese sensor. Solo
    lectura: no carga el estimador ni reentrena nada.
    """
    name = registered_model_name_for(sensor_id) + "__issued"
    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{name}'")
    if not versions:
        return None
    latest = max(versions, key=lambda v: int(v.version))
    metadata_path = client.download_artifacts(latest.run_id, "predictor_metadata.json")
    with open(metadata_path, encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)
    metadata["issued_model_version"] = str(latest.version)
    return metadata


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
