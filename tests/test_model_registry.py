import json
from dataclasses import replace
from pathlib import Path

import mlflow
import pandas as pd
import pytest
from mlflow.exceptions import MlflowException
from sklearn.linear_model import LogisticRegression

from data_ingestion.sensor_naming import registered_model_name_for
from human_feedback.lineage import (
    LINEAGE_VERSION_1,
    LINEAGE_VERSION_2,
    FeedbackReference,
    LineageValidationError,
    RecalibrationLineage,
)
from human_feedback.model_registry import (
    ModelContractMismatch,
    list_recalibration_lineage,
    load_latest_recalibrated_model,
    load_recalibration_lineage,
    register_recalibrated_model,
)
from predictive_modeling.contract import FittedPredictor, make_contract


def _tracking(tmp_path):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment("contracts")


def _bundle():
    contract = make_contract(["soil_moisture"], lags=[1], rolling_windows=[])
    X = pd.DataFrame({"soil_moisture_lag1": [0.1, 0.2, 0.3, 0.4]})
    model = LogisticRegression().fit(X, [1, 1, 0, 0])
    return FittedPredictor(model, contract, 0.25, "2024-01-10"), X


def test_register_load_roundtrip_and_sensor_isolation(tmp_path):
    _tracking(tmp_path)
    bundle, X = _bundle()
    assert load_latest_recalibrated_model("a", bundle.contract) is None
    assert register_recalibrated_model("a", bundle, {}, {}) == "1"
    loaded = load_latest_recalibrated_model("a", bundle.contract)
    assert loaded.contract == bundle.contract
    assert loaded.threshold == bundle.threshold
    assert loaded.model_id == bundle.model_id
    assert list(loaded.model.predict(X)) == list(bundle.model.predict(X))
    assert load_latest_recalibrated_model("b", bundle.contract) is None
    assert register_recalibrated_model("a", bundle, {}, {}) == "2"


@pytest.mark.parametrize(
    "change",
    [
        {"lags": [2]},
        {"rolling_windows": [3]},
        {"horizon_days": 7},
        {"include_current": True},
        {"include_anomaly_detection": True},
    ],
)
def test_incompatible_contract_rejected_before_download(tmp_path, monkeypatch, change):
    _tracking(tmp_path)
    bundle, _ = _bundle()
    register_recalibrated_model("a", bundle, {}, {})
    expected = make_contract(["soil_moisture"], **({"lags": [1], "rolling_windows": []} | change))

    def fail(*args, **kwargs):
        raise AssertionError("No debe descargar el modelo incompatible")

    monkeypatch.setattr(mlflow.sklearn, "load_model", fail)
    with pytest.raises(ModelContractMismatch):
        load_latest_recalibrated_model("a", expected)


def test_registration_rejects_metadata_that_disagrees_with_estimator(tmp_path):
    _tracking(tmp_path)
    bundle, _ = _bundle()
    bad = replace(bundle, contract={**bundle.contract, "model_features": ["wrong"]})
    with pytest.raises(ModelContractMismatch):
        register_recalibrated_model("a", bad, {}, {})


def _lineage(
    sensor_id,
    source_model_id,
    model,
    recalibration_id="r1",
    lineage_version=LINEAGE_VERSION_1,
    dataset_sha256=None,
):
    """Linaje consistente con `model` (el predictor que efectivamente se
    va a registrar), como lo exige `_validate_lineage_matches_model`. Por
    defecto construye un evento `LINEAGE_VERSION_1` (histórico, sin
    `dataset_sha256`), igual que antes de esta capacidad.
    """
    return RecalibrationLineage(
        recalibration_id=recalibration_id,
        sensor_id=sensor_id,
        source_model_id=source_model_id,
        successor_model_id=model.model_id,
        feedback_references=[
            FeedbackReference(
                sensor_id=sensor_id,
                fecha="2024-01-01 00:00:00",
                model_version=source_model_id,
                target_timestamp="2024-01-04 00:00:00",
            )
        ],
        recalibrated_at="2026-09-06 00:00:00",
        source_trained_through="2024-01-01",
        successor_trained_through=model.trained_through,
        dataset_fingerprint="abc123",
        contract_version=model.contract["contract_version"],
        pipeline_version=model.contract["pipeline_version"],
        lineage_version=lineage_version,
        dataset_sha256=dataset_sha256,
    )


def _register_raw_version(
    sensor_id, model, params: dict, lineage: RecalibrationLineage | None = None
):
    """Registra una versión directamente vía MLflow (sin pasar por
    `register_recalibrated_model`, que siempre escribe los 4 parámetros
    requeridos juntos), con exactamente los `params` dados — simula
    persistencias parciales, corruptas o ajenas a esta capacidad.
    """
    name = registered_model_name_for(sensor_id)
    with mlflow.start_run(run_name="raw"):
        for key, value in params.items():
            mlflow.log_param(key, value)
        if lineage is not None:
            mlflow.log_dict(lineage.to_dict(), "recalibration_lineage.json")
        mlflow.sklearn.log_model(model.model, artifact_path="model", registered_model_name=name)


def test_register_persists_lineage_as_artifact_of_the_same_run(tmp_path):
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage = _lineage("a", "model-a", bundle)

    version = register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    resolved = load_recalibration_lineage("a", bundle.model_id)
    assert resolved is not None
    assert resolved.recalibration_id == lineage.recalibration_id
    assert resolved.source_model_id == "model-a"
    assert resolved.successor_model_id == bundle.model_id
    assert resolved.mlflow_model_version == version
    assert resolved.feedback_references == lineage.feedback_references


def test_list_recalibration_lineage_reconstructs_chronological_chain(tmp_path):
    _tracking(tmp_path)
    bundle, _ = _bundle()
    successor = replace(bundle, model_id="model-c")

    lineage_a_b = _lineage("a", "model-a", bundle)
    lineage_b_c = _lineage("a", bundle.model_id, successor, recalibration_id="r2")
    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage_a_b)
    register_recalibrated_model("a", successor, {}, {}, lineage=lineage_b_c)

    chain = list_recalibration_lineage("a")

    assert [event.recalibration_id for event in chain] == ["r1", "r2"]
    assert chain[0].source_model_id == "model-a"
    assert chain[0].successor_model_id == bundle.model_id
    assert chain[1].source_model_id == bundle.model_id
    assert chain[1].successor_model_id == "model-c"


def test_register_without_lineage_does_not_create_a_lineage_event(tmp_path):
    _tracking(tmp_path)
    bundle, _ = _bundle()

    register_recalibrated_model("a", bundle, {}, {})

    assert load_recalibration_lineage("a", bundle.model_id) is None
    assert list_recalibration_lineage("a") == []


@pytest.mark.parametrize(
    "override",
    [
        {"sensor_id": "b"},
        {"successor_model_id": "not-the-model-being-registered"},
        {"successor_trained_through": "2099-01-01"},
        {"contract_version": 999},
        {"pipeline_version": "otro_pipeline"},
    ],
)
def test_register_rejects_lineage_inconsistent_with_the_model_and_registers_nothing(
    tmp_path, override
):
    """Requirement H-01 (microajustes): la validación cruzada entre el
    linaje y el predictor debe ejecutarse antes de escribir nada en
    MLflow — una versión registrada nunca debe quedar sin su linaje, y
    un linaje inconsistente tampoco debe dejar una versión huérfana.
    """
    _tracking(tmp_path)
    bundle, _ = _bundle()

    with pytest.raises(LineageValidationError):
        lineage = replace(_lineage("a", "model-a", bundle), **override)
        register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    assert load_latest_recalibrated_model("a", bundle.contract) is None
    name = registered_model_name_for("a")
    assert mlflow.MlflowClient().search_model_versions(f"name='{name}'") == []


def _registered_version(sensor_id):
    name = registered_model_name_for(sensor_id)
    versions = sorted(
        mlflow.MlflowClient().search_model_versions(f"name='{name}'"), key=lambda v: int(v.version)
    )
    return versions


def _corrupt_lineage_artifact(run_id, mutate) -> None:
    """Descarga el artefacto de linaje ya persistido, le aplica `mutate`
    sobre su contenido parseado, y lo reescribe en el mismo archivo local
    (posible porque el store de artefactos en estos tests es local).
    """
    client = mlflow.MlflowClient()
    artifact_path = client.download_artifacts(run_id, "recalibration_lineage.json")
    payload = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    mutate(payload)
    Path(artifact_path).write_text(json.dumps(payload), encoding="utf-8")


def test_load_recalibration_lineage_accepts_historical_event_without_sha256(tmp_path):
    """Requirement T-01 (1): un evento histórico `LINEAGE_VERSION_1` sin
    `dataset_sha256` sigue cargando correctamente.
    """
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage = _lineage("a", "model-a", bundle)  # LINEAGE_VERSION_1 por defecto

    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    resolved = load_recalibration_lineage("a", bundle.model_id)
    assert resolved is not None
    assert resolved.lineage_version == LINEAGE_VERSION_1
    assert resolved.dataset_sha256 is None


def test_load_recalibration_lineage_accepts_new_event_with_sha256(tmp_path):
    """Requirement T-01 (2): un evento nuevo `LINEAGE_VERSION_2` con
    `dataset_sha256` válido carga correctamente y lo preserva.
    """
    _tracking(tmp_path)
    bundle, _ = _bundle()
    sha = "a" * 64
    lineage = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256=sha
    )

    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    resolved = load_recalibration_lineage("a", bundle.model_id)
    assert resolved is not None
    assert resolved.lineage_version == LINEAGE_VERSION_2
    assert resolved.dataset_sha256 == sha


def test_register_rejects_new_event_missing_sha256(tmp_path):
    """Requirement T-01 (3): un evento `LINEAGE_VERSION_2` sin
    `dataset_sha256` no puede ni construirse; por lo tanto tampoco
    registrarse."""
    _tracking(tmp_path)
    bundle, _ = _bundle()

    with pytest.raises(LineageValidationError):
        _lineage("a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2)

    assert _registered_version("a") == []


@pytest.mark.parametrize(
    "bad_sha",
    ["", "a" * 63, "a" * 65, "g" * 64, "A" * 64, "not-a-sha256-hash-value-at-all"],
)
def test_lineage_rejects_malformed_dataset_sha256(bad_sha):
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(
            recalibration_id="r1",
            sensor_id="sensor-a",
            source_model_id="model-a",
            successor_model_id="model-b",
            feedback_references=[
                FeedbackReference(
                    sensor_id="sensor-a",
                    fecha="2024-01-01 00:00:00",
                    model_version="model-a",
                    target_timestamp="2024-01-04 00:00:00",
                )
            ],
            recalibrated_at="2026-09-06 00:00:00",
            source_trained_through="2024-01-01",
            successor_trained_through="2024-01-05",
            dataset_fingerprint="abc123",
            contract_version=1,
            pipeline_version="controlled_daily_v3",
            lineage_version=LINEAGE_VERSION_2,
            dataset_sha256=bad_sha,
        )


def test_lineage_rejects_unsupported_lineage_version():
    with pytest.raises(LineageValidationError):
        RecalibrationLineage(
            recalibration_id="r1",
            sensor_id="sensor-a",
            source_model_id="model-a",
            successor_model_id="model-b",
            feedback_references=[
                FeedbackReference(
                    sensor_id="sensor-a",
                    fecha="2024-01-01 00:00:00",
                    model_version="model-a",
                    target_timestamp="2024-01-04 00:00:00",
                )
            ],
            recalibrated_at="2026-09-06 00:00:00",
            source_trained_through="2024-01-01",
            successor_trained_through="2024-01-05",
            dataset_fingerprint="abc123",
            contract_version=1,
            pipeline_version="controlled_daily_v3",
            lineage_version=99,
        )


def test_load_recalibration_lineage_returns_none_for_a_version_that_never_declared_lineage(
    tmp_path,
):
    """Requirement T-01 (6): comportamiento retrocompatible — una versión
    histórica sin los parámetros canónicos de linaje no es tratada como
    corrupta, sino como ausencia legítima.
    """
    _tracking(tmp_path)
    bundle, _ = _bundle()

    register_recalibrated_model("a", bundle, {}, {})  # sin lineage=

    assert load_recalibration_lineage("a", bundle.model_id) is None
    assert list_recalibration_lineage("a") == []


def test_declares_lineage_returns_none_without_any_declaration_marker(tmp_path):
    """Microajuste (1): ningún marcador específico de linaje presente →
    `None`, igual que una recalibración anterior a esta capacidad."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    _register_raw_version("a", bundle, {"threshold": 0.5})

    assert load_recalibration_lineage("a", "anything") is None
    assert list_recalibration_lineage("a") == []


def test_declares_lineage_returns_none_with_only_dataset_fingerprint(tmp_path):
    """Microajuste (2): `dataset_fingerprint` por sí solo no es un marcador
    suficiente de declaración de linaje (no es específico de una
    recalibración HITL) → `None`, no `LineageValidationError`."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    _register_raw_version("a", bundle, {"dataset_fingerprint": "abc123"})

    assert load_recalibration_lineage("a", "anything") is None
    assert list_recalibration_lineage("a") == []


def test_declares_lineage_raises_with_only_recalibration_id(tmp_path):
    """Microajuste (3): `recalibration_id` solo, sin el resto de los
    parámetros obligatorios, es una declaración parcial → falla
    explícitamente en vez de degradar a `None`."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    _register_raw_version("a", bundle, {"recalibration_id": "r1"})

    with pytest.raises(LineageValidationError, match="source_model_id.*successor_model_id"):
        load_recalibration_lineage("a", "anything")


@pytest.mark.parametrize("param", ["source_model_id", "successor_model_id"])
def test_declares_lineage_raises_with_only_one_model_id_param(tmp_path, param):
    """Microajuste (4): `source_model_id` o `successor_model_id` solos son
    declaración parcial → falla explícitamente."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    _register_raw_version("a", bundle, {param: "model-x"})

    with pytest.raises(LineageValidationError):
        load_recalibration_lineage("a", "anything")


def test_declares_lineage_raises_with_partial_marker_combination(tmp_path):
    """Microajuste (5): una combinación parcial de marcadores (ni completa
    ni vacía) también es declaración parcial → falla explícitamente."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    _register_raw_version("a", bundle, {"recalibration_id": "r1", "source_model_id": "model-a"})

    with pytest.raises(LineageValidationError, match="successor_model_id.*dataset_fingerprint"):
        load_recalibration_lineage("a", "anything")


def test_declares_lineage_accepts_legacy_v1_event_without_lineage_version_param(tmp_path):
    """Microajuste (6): un evento V1 válido, persistido sin el parámetro
    `lineage_version` (como lo haría la implementación anterior a este
    microajuste), sigue reconstruyéndose correctamente: la detección de
    declaración no depende de `lineage_version` en solitario."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage = _lineage("a", "model-a", bundle)  # LINEAGE_VERSION_1, sin dataset_sha256
    _register_raw_version(
        "a",
        bundle,
        {
            "recalibration_id": lineage.recalibration_id,
            "source_model_id": lineage.source_model_id,
            "successor_model_id": lineage.successor_model_id,
            "dataset_fingerprint": lineage.dataset_fingerprint,
        },
        lineage=lineage,
    )

    resolved = load_recalibration_lineage("a", bundle.model_id)
    assert resolved is not None
    assert resolved.lineage_version == LINEAGE_VERSION_1
    assert resolved.dataset_sha256 is None


def test_list_recalibration_lineage_propagates_error_on_partial_declaration(tmp_path):
    """Microajuste (8): `list_recalibration_lineage` no debe ocultar una
    declaración parcial detrás de un listado vacío o incompleto."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    _register_raw_version("a", bundle, {"recalibration_id": "r1"})

    with pytest.raises(LineageValidationError):
        list_recalibration_lineage("a")


def test_load_recalibration_lineage_fails_closed_when_artifact_download_raises_mlflow_error(
    tmp_path, monkeypatch
):
    """Requirement T-01 (7/8): una versión que declara linaje (tiene los
    parámetros canónicos) pero cuyo artefacto no puede descargarse debe
    fallar explícitamente, no degradar a `None`.
    """
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256="a" * 64
    )
    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    def fail(*args, **kwargs):
        raise MlflowException("Artifact recalibration_lineage.json not found")

    monkeypatch.setattr(mlflow.MlflowClient, "download_artifacts", fail)

    with pytest.raises(LineageValidationError):
        load_recalibration_lineage("a", bundle.model_id)


def test_load_recalibration_lineage_fails_closed_on_download_os_error(tmp_path, monkeypatch):
    """Requirement T-01 (8): un error de descarga (p. ej. de I/O) también
    debe fallar explícitamente."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256="a" * 64
    )
    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    def fail(*args, **kwargs):
        raise OSError("network unreachable")

    monkeypatch.setattr(mlflow.MlflowClient, "download_artifacts", fail)

    with pytest.raises(LineageValidationError):
        load_recalibration_lineage("a", bundle.model_id)


def test_load_recalibration_lineage_fails_closed_on_corrupted_json(tmp_path):
    """Requirement T-01 (9): JSON corrupto en un artefacto que sí se
    declaró debe fallar explícitamente."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256="a" * 64
    )
    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    version = _registered_version("a")[0]
    artifact_path = mlflow.MlflowClient().download_artifacts(
        version.run_id, "recalibration_lineage.json"
    )
    Path(artifact_path).write_text("{not valid json", encoding="utf-8")

    with pytest.raises(LineageValidationError):
        load_recalibration_lineage("a", bundle.model_id)


def test_load_recalibration_lineage_fails_closed_on_semantically_invalid_artifact(tmp_path):
    """Requirement T-01 (10): un artefacto sintácticamente válido pero que
    incumple la semántica del contrato (aquí, `source_model_id ==
    successor_model_id`) debe fallar explícitamente."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256="a" * 64
    )
    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage)

    version = _registered_version("a")[0]
    _corrupt_lineage_artifact(
        version.run_id,
        lambda payload: payload.__setitem__("source_model_id", payload["successor_model_id"]),
    )

    with pytest.raises(LineageValidationError):
        load_recalibration_lineage("a", bundle.model_id)


def test_list_recalibration_lineage_propagates_error_instead_of_partial_chain(tmp_path):
    """Requirement T-01 (11): si una versión posterior de la cadena
    declaró linaje pero está corrupta, `list_recalibration_lineage` no
    debe devolver silenciosamente solo las versiones previas válidas.
    """
    _tracking(tmp_path)
    bundle, _ = _bundle()
    successor = replace(bundle, model_id="model-c")

    lineage_a_b = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256="a" * 64
    )
    register_recalibrated_model("a", bundle, {}, {}, lineage=lineage_a_b)
    lineage_b_c = _lineage(
        "a",
        bundle.model_id,
        successor,
        recalibration_id="r2",
        lineage_version=LINEAGE_VERSION_2,
        dataset_sha256="b" * 64,
    )
    register_recalibrated_model("a", successor, {}, {}, lineage=lineage_b_c)

    versions = _registered_version("a")
    assert len(versions) == 2
    _corrupt_lineage_artifact(
        versions[1].run_id,
        lambda payload: payload.__setitem__("source_model_id", payload["successor_model_id"]),
    )

    with pytest.raises(LineageValidationError):
        list_recalibration_lineage("a")


def _raw_params_from_lineage(lineage: RecalibrationLineage, **overrides) -> dict:
    params = {
        "recalibration_id": lineage.recalibration_id,
        "source_model_id": lineage.source_model_id,
        "successor_model_id": lineage.successor_model_id,
        "dataset_fingerprint": lineage.dataset_fingerprint,
        "lineage_version": lineage.lineage_version,
    }
    params.update(overrides)
    for key, value in list(overrides.items()):
        if value is None:
            del params[key]
    return params


def test_load_recalibration_lineage_rejects_param_v2_with_artifact_v1(tmp_path):
    """R1 (parámetro V2 + artefacto V1): el parámetro `lineage_version`
    declara 2 pero el artefacto persistido es efectivamente V1 (sin
    `dataset_sha256`) — inconsistencia entre parámetro y artefacto."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v1 = _lineage("a", "model-a", bundle, lineage_version=LINEAGE_VERSION_1)
    _register_raw_version(
        "a",
        bundle,
        _raw_params_from_lineage(lineage_v1, lineage_version=LINEAGE_VERSION_2),
        lineage=lineage_v1,
    )

    with pytest.raises(LineageValidationError, match="lineage_version"):
        load_recalibration_lineage("a", bundle.model_id)


def test_load_recalibration_lineage_rejects_param_v1_with_artifact_v2(tmp_path):
    """R1 (parámetro V1 + artefacto V2): el parámetro declara 1 pero el
    artefacto persistido es efectivamente V2 (con `dataset_sha256`)."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v2 = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256="a" * 64
    )
    _register_raw_version(
        "a",
        bundle,
        _raw_params_from_lineage(lineage_v2, lineage_version=LINEAGE_VERSION_1),
        lineage=lineage_v2,
    )

    with pytest.raises(LineageValidationError, match="lineage_version"):
        load_recalibration_lineage("a", bundle.model_id)


def test_load_recalibration_lineage_rejects_missing_param_with_artifact_v2(tmp_path):
    """R1 (parámetro ausente + artefacto V2): la ausencia del parámetro
    `lineage_version` solo es válida para un artefacto V1 histórico
    genuino — nunca se interpreta como V1 cuando el artefacto es V2."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v2 = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256="a" * 64
    )
    _register_raw_version(
        "a",
        bundle,
        _raw_params_from_lineage(lineage_v2, lineage_version=None),
        lineage=lineage_v2,
    )

    with pytest.raises(LineageValidationError, match="lineage_version"):
        load_recalibration_lineage("a", bundle.model_id)


def test_load_recalibration_lineage_accepts_v1_historical_event_without_param(tmp_path):
    """R1: un evento histórico V1 genuino (sin el parámetro
    `lineage_version` y sin `dataset_sha256`) sigue siendo válido."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v1 = _lineage("a", "model-a", bundle)
    _register_raw_version(
        "a",
        bundle,
        _raw_params_from_lineage(lineage_v1, lineage_version=None),
        lineage=lineage_v1,
    )

    resolved = load_recalibration_lineage("a", bundle.model_id)

    assert resolved is not None
    assert resolved.lineage_version == LINEAGE_VERSION_1
    assert resolved.dataset_sha256 is None


def test_load_recalibration_lineage_accepts_v2_event_with_matching_param(tmp_path):
    """R1: un evento V2 válido con el parámetro `lineage_version=2`
    coincidente con el artefacto se recupera correctamente."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v2 = _lineage(
        "a", "model-a", bundle, lineage_version=LINEAGE_VERSION_2, dataset_sha256="a" * 64
    )
    _register_raw_version("a", bundle, _raw_params_from_lineage(lineage_v2), lineage=lineage_v2)

    resolved = load_recalibration_lineage("a", bundle.model_id)

    assert resolved is not None
    assert resolved.lineage_version == LINEAGE_VERSION_2
    assert resolved.dataset_sha256 == "a" * 64


def test_load_recalibration_lineage_rejects_invalid_lineage_version_param(tmp_path):
    """R1: un parámetro `lineage_version` no soportado (ni siquiera un
    entero válido) falla explícitamente."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v1 = _lineage("a", "model-a", bundle)
    _register_raw_version(
        "a",
        bundle,
        _raw_params_from_lineage(lineage_v1, lineage_version="no-es-un-entero"),
        lineage=lineage_v1,
    )

    with pytest.raises(LineageValidationError, match="lineage_version"):
        load_recalibration_lineage("a", bundle.model_id)


def test_load_recalibration_lineage_error_includes_model_version_and_run_id(tmp_path):
    """R1: el error expuesto incluye la versión del modelo y el `run_id`
    afectados, para poder identificar el evento corrupto."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v1 = _lineage("a", "model-a", bundle)
    _register_raw_version(
        "a",
        bundle,
        _raw_params_from_lineage(lineage_v1, lineage_version=LINEAGE_VERSION_2),
        lineage=lineage_v1,
    )
    version = _registered_version("a")[0]

    with pytest.raises(LineageValidationError) as excinfo:
        load_recalibration_lineage("a", bundle.model_id)

    message = str(excinfo.value)
    assert f"version={version.version}" in message
    assert f"run_id={version.run_id}" in message


def test_list_recalibration_lineage_propagates_version_mismatch_error(tmp_path):
    """R1: `list_recalibration_lineage` no debe ocultar una inconsistencia
    de `lineage_version` detrás de un listado vacío o parcial."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v1 = _lineage("a", "model-a", bundle)
    _register_raw_version(
        "a",
        bundle,
        _raw_params_from_lineage(lineage_v1, lineage_version=LINEAGE_VERSION_2),
        lineage=lineage_v1,
    )

    with pytest.raises(LineageValidationError):
        list_recalibration_lineage("a")


def test_from_dict_structural_errors_surface_as_lineage_validation_error_via_registry(tmp_path):
    """R1 (4): un artefacto con estructura inválida (aquí, una referencia
    de feedback mal formada) persistido junto a parámetros que sí
    declaran linaje debe fallar como `LineageValidationError` con
    contexto, no como una excepción estructural sin normalizar."""
    _tracking(tmp_path)
    bundle, _ = _bundle()
    lineage_v1 = _lineage("a", "model-a", bundle)
    broken_payload = lineage_v1.to_dict()
    broken_payload["feedback_references"] = [{"sensor_id": "sensor-a"}]  # incompleta

    name = registered_model_name_for("a")
    with mlflow.start_run(run_name="raw"):
        for key, value in _raw_params_from_lineage(lineage_v1).items():
            mlflow.log_param(key, value)
        mlflow.log_dict(broken_payload, "recalibration_lineage.json")
        mlflow.sklearn.log_model(bundle.model, artifact_path="model", registered_model_name=name)

    with pytest.raises(LineageValidationError):
        load_recalibration_lineage("a", bundle.model_id)


def test_loading_requires_expected_contract():
    with pytest.raises(TypeError):
        load_latest_recalibrated_model("a")


def test_load_propagates_unavailable_mlflow(monkeypatch):
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    mlflow.set_tracking_uri("http://localhost:59999")
    bundle, _ = _bundle()
    with pytest.raises(MlflowException):
        load_latest_recalibrated_model("a", bundle.contract)
